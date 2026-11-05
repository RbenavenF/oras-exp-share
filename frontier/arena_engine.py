"""Arena B engine constants and guarded CRO bridge specifications (§31).

The logic lives in code.bin's shared cave, never in zero-filled CRO jump tables.
No retail function reads bit 31 among the measured setup-mask consumers; the
runtime regression matrix remains required before declaring this stage complete.
"""
import struct

RULE = 0x80000000
START = 0x1E33D8
START_BEFORE = 0xE1A00005                    # mov r0,r5, late in StartBattle
HP_WORKS = (16693, 16694)                    # REPARTO, reserved 2026-11-05
UDIV = 0x15EC10
SITES = {
    0x724C0: ('arena_enter', bytes.fromhex('010c85e20010a0e3bab5c0e1b815c0e1')),
    0x1D21C: ('arena_turn_end', bytes.fromhex('0600a0e1353901eb00f020e300f020e3')),
    0x7945C: ('arena_switch', bytes.fromhex('0060a0e10180a0e10cd04de202a0a0e1')),
}
CONSTANTS = {'ARENA_RULE': RULE, 'ARENA_ACTIVE': 16466, 'ARENA_ROUTE': 4,
             'ARENA_HP_OFFSET': 2 * (HP_WORKS[0] - 0x4000), 'ARENA_END_SITE': 0x1D21C}


def cro_writes(symbols):
    """guarded_writes entries; compose with Pike/Palace, then rehash once.

    After BLX, LR points at the branch, not at the inline literal. The entry
    snapshot and end-turn hooks return through that branch; a blocked switch
    restores the retail prologue's frame and returns straight to its caller.
    """
    return [dict(offset=site, before=before.hex(), after=struct.pack(
        '<4I', 0xE59FC004, 0xE12FFF3C, 0xEA000000, symbols[name]).hex())
            for site, (name, before) in SITES.items()]
