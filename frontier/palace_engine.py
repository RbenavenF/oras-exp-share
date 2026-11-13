"""Palace B engine constants and guarded DllBattle.cro bridges (reports/frontier.md §32, frontier/asm/palace.s).

Measured in Azahar on the v0.5 DllBattle.cro loaded at 0x6f3000 (work/frontier/palace/b2-gdb-m3b.log):
- client constructor 0x72f40: arguments (clientID, thinker...) at [sp+0x5c..]; thinker stored at +0x91
  (0x73064), AI object at +0x1c8 only for thinker 1 (0x731f0..0x73304), its AI flags from 0x73228..0x732ac;
- the single battle setup 0x164fc builds client 0 with thinker 0 (0x16660) and client 1 with thinker 1
  (0x166c8);
- command dispatch 0x49b0..0x4a08: row of 0x1c bytes in table 0xdbc68, column = client+0x91.

Same bridge shape as the Arena's (arena_engine.bridge): `nop; bl stub; b +0; nop`, the stubs (asm/palace_b_cro.s)
in DllBattle.cro since F7-CUEVA-LUMA (patch.BATTLE_CRO_AT).
The second dispatcher (0x7664, never reached in the measured battles) is left retail: if it ever carries a
decision, the player is simply asked (manual control), which is the retail behaviour.
"""
import palace_ai  # noqa: E402,F401  (stage C, also reached as pe.palace_ai)
from arena_engine import bridge

RULE = 0x40000000            # setup+0xa8 bit 30 (the Arena owns bit 31; retail masks measured up to 0x100000)
AI_FLAGS = 7                 # the Maison trainers' AI flags (trainer object +0xc, 0x1e3620)
ROUTE = 3
ACTIVE = 16462               # frontier/REPARTO.md
DECISIONS = (3, 5, 6)        # commands answered by the AI column for the Palace's client 0
SITES = {
    0x731F0: ('palace_ai_want', bytes.fromhex('9100d4e5010050e36c009d0500005003')),
    0x73258: ('palace_ai_flags', bytes.fromhex('200895e5000050e31600001a110000ea')),
    0x49EC: ('palace_dispatch', bytes.fromhex('9130d4e5800160e0795f84e2002182e0')),
}
CONSTANTS = {'PALACE_RULE': RULE, 'PALACE_AI': AI_FLAGS, 'PALACE_ROUTE': ROUTE, 'PALACE_ACTIVE': ACTIVE}


def cro_writes(symbols):
    """guarded_writes entries, composed with the Pike's and the Arena's before the single rehash. `symbols`:
    patch.battle_cro_code() (CRO file offsets).

    Stage C (palace_ai.py, asm/palace_cro.s) lives in the CRO itself: its `bl` at 0xd468 and its code and tables
    in the padding after .text; it does not use the code.bin cave."""
    return [*palace_ai.cro_writes(), *[dict(offset=site, before=before.hex(), after=bridge(site, symbols[name]).hex())
            for site, (name, before) in SITES.items()]]
