"""Stock bug fix: Osc 1/2/3 Fine from -100 to -73 is ignored over MIDI.

Not part of MPE: a separate byte patch on the stock image, so it can be
built and flashed on its own, or its three entries added to another
definition. Addresses and evidence are in docs/findings/summit-2.2-build2121.md,
section "Osc Fine over MIDI: -100 to -73 rejected".

Osc Fine is sent as a CC pair: CC 15/18/21 carries the coarse byte, 14-114
for -100..+100 (the Summit's own panel sends -100 as 14), and CC 47/50/53
the fine byte. param_set_from_midi 0x08010038 drops a value below its
descriptor's min (cmp at 0x08010078). The three coarse-byte descriptors in
patch_param_desc (offsets 0x33, 0x48, 0x5D) have min 28 (0x1C) and max 228
(0xE4), so every value from 14 to 27 is dropped and the parameter keeps its
previous value. The front panel is not affected.

The fix sets each min to 14. The descriptors are .data initialisers (flash
0x0804E7CC + 12 * offset, copied to RAM 0x20002A4C at boot), so the edit is
in flash. max stays 228: values 115-127 were already accepted on stock.
"""

SOURCE = "summit-firmware-2.2-build2121.syx"
NAME = "osc-fine-fix"

PATCH_PARAM_DESC = 0x0804E7CC  # flash initialiser of patch_param_desc (RAM 0x20002A4C), 12 B per patch offset

# (flash address, original bytes, new bytes, why)
PATCHES = [
    (PATCH_PARAM_DESC + 0x33 * 12, b"\x1c", b"\x0e",
     "patch_param_desc[0x033].min 28 -> 14: Osc 1 Fine coarse byte (CC 15), 0x0804EA30"),
    (PATCH_PARAM_DESC + 0x48 * 12, b"\x1c", b"\x0e",
     "patch_param_desc[0x048].min 28 -> 14: Osc 2 Fine coarse byte (CC 18), 0x0804EB2C"),
    (PATCH_PARAM_DESC + 0x5D * 12, b"\x1c", b"\x0e",
     "patch_param_desc[0x05D].min 28 -> 14: Osc 3 Fine coarse byte (CC 21), 0x0804EC28"),
]
