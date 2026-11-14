"""patches/osc_fine_fix.py: Osc 1/2/3 Fine from -100 to -73 over MIDI.

Builds the real patched file into a temporary directory and skips without the
official firmware. Only the three descriptor minimums may differ. In the
emulator, CC 15/18/21 with a value of 14-27 is dropped on stock and stored on
the patched image; every other value behaves as on stock.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import patch  # noqa: E402
import syx  # noqa: E402

from emu.machine import Machine  # noqa: E402
from test_cc_nrpn import CC, CC_NRPN_RX, DATA, MIDI_CURRENT_PART  # noqa: E402

DEFINITION = ROOT / "patches" / "osc_fine_fix.py"

PATCHES = 0x200138A0             # Single patch buffer; part 0, multi_mode 0 after boot()
# patch_param_offset 0x0801D95C reads a pnum -> offset table at 0x200163A4 in
# .bss. It is built by 0x0801D90C from the offset -> NRPN table 0x20015E60,
# which 0x0801D8AC builds from patch_param_desc (observed). boot() stops
# before main, so both tables are empty: build them first.
BUILD_OFFSET_TO_NRPN = 0x0801D8AC
BUILD_PNUM_TO_OFFSET = 0x0801D90C

# (coarse-byte CC, patch offset, descriptor in flash)
FINE = [
    (15, 0x033, 0x0804EA30),     # Osc 1 Fine
    (18, 0x048, 0x0804EB2C),     # Osc 2 Fine
    (21, 0x05D, 0x0804EC28),     # Osc 3 Fine
]
UNSET = 0x80                     # above every value a CC can carry


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    definition = patch.load_definition(DEFINITION)
    if not (patch.FIRMWARE_DIR / definition.SOURCE).exists():
        pytest.skip(f"firmware/{definition.SOURCE} not present (run scripts/fetch-firmware.sh)")
    path, _ = patch.build(DEFINITION, out_dir=tmp_path_factory.mktemp("patched"), out=lambda s: None)
    official = (patch.FIRMWARE_DIR / definition.SOURCE).read_bytes()
    return syx.decode(official), syx.decode(path.read_bytes())


def test_only_the_three_descriptor_minimums_differ(built):
    (header0, stock), (header1, patched) = built
    assert header1 == header0
    assert len(patched) == len(stock)
    assert patch.diff(stock, patched) == [(desc, b"\x1c", b"\x0e") for _, _, desc in FINE]
    for _, _, desc in FINE:
        assert patched[desc - patch.IMAGE_BASE + 1] == 0xE4   # max stays 228


def received(image):
    """For each Fine CC, the patch byte after each CC value 0-127."""
    m = Machine(image)
    m.boot()
    m.call(BUILD_OFFSET_TO_NRPN, budget=200_000)
    m.call(BUILD_PNUM_TO_OFFSET, budget=500_000)
    m.write(CC_NRPN_RX, b"\x01")
    m.write(MIDI_CURRENT_PART, b"\x00")
    out = {}
    for cc, offset, _ in FINE:
        row = []
        for value in range(128):
            m.write(PATCHES + offset, bytes([UNSET]))
            m.write(DATA, bytes([cc, value]))
            m.call(CC, DATA, budget=20_000)
            row.append(m.u8(PATCHES + offset))
        out[cc] = row
    return out


@pytest.fixture(scope="module")
def sweeps(built):
    (_, stock), (_, patched) = built
    return received(stock), received(patched)


@pytest.mark.parametrize("cc", [cc for cc, _, _ in FINE])
def test_stock_drops_minus_100_to_minus_73(sweeps, cc):
    stock, _ = sweeps
    assert [v for v in range(128) if stock[cc][v] == UNSET] == list(range(28))
    assert all(stock[cc][v] == v for v in range(28, 128))


@pytest.mark.parametrize("cc", [cc for cc, _, _ in FINE])
def test_patched_accepts_the_full_range(sweeps, cc):
    stock, patched = sweeps
    assert [v for v in range(128) if patched[cc][v] == UNSET] == list(range(14))
    assert all(patched[cc][v] == v for v in range(14, 128))
    assert patched[cc][28:] == stock[cc][28:]
