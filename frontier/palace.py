#!/usr/bin/env python3
"""Battle Palace, stage A (reports/diseno/palacio.md §1): the zone script of its interior, a clone of the Battle
Maison hall, run as the Battle Tower (frontier/tower.py) with the Palace's own route, works and BP.

Singles, Level 50, rank Normal, with the player's own team chosen on the Maison's screens (mode selection, then the
party selection 0x457c, untouched: the Tower showed the party screen refuses every Pokémon without the mode
selection, reports/frontier.md §25), 7 battles a round, an own streak and record by streak route 3
(patch.STREAK_ROUTES), BP of data.FRONTIER_BP['palace'] after the 7th battle of each round, pause and resume as the
Maison, and the mutual exclusion with the other facilities (factory.busy_check, patch.ACTIVE_WORK).

Stage B (reports/frontier.md §32): in its battles the game's AI decides for the player's Pokémon (frontier/asm/
palace.s, frontier/palace_engine.py; still without the nature table, stage C). The battle video does not record
those decisions, so the Palace's «next battle» menu drops «Guardar vídeo» (VIDEO_ITEM, `hide_video`) and the
record routine offered after a loss or at the end (VIDEO_RECORD: SaveBattleRecord + wait) returns at once. Same known deviations as the Tower: the Maison's texts
(«Mansión Batalla»), its party rules, its boss on the streak; no Spenser, Doubles or Open Level.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import data as fd  # noqa: E402
import patch  # noqa: E402
import tower  # noqa: E402
from pawn import OP, Op  # noqa: E402

FACILITY = 'palace'
VIDEO_MENU = 'L3d2c'             # 0x3d08: LOAD_P_S_PRI 20; JNZ 0x3d2c skips ListMenuAdd(68 «Guardar vídeo», 1)
VIDEO_ITEM = 68
VIDEO_RECORD = 'L3fdc'           # PROC; SaveBattleRecord(arg); L4(1) (wait for the applet); called at 0x21d0 (loss
                                 # path L2210), 0x2250 and 0x25dc. Azahar 2026-11-10: after a loss it saved a video.
ZONE = 340                       # frontier/REPARTO.md; checked statically by frontier/zone_check.py (§27)
ROUTE = patch.ROUTE[FACILITY]
STREAK, ACTIVE, RECORD = (patch.STREAK_ROUTES[ROUTE][1] + k for k in range(3))
PALACE_BP = fd.FRONTIER_BP[FACILITY]


def hide_video(p):
    """The «next battle» menu (0x3ce4..0x3d20: Continuar 67, Pausar 69, Guardar vídeo 68 only if argument 20 is 0)
    never adds its video item: its conditional jump over the ListMenuAdd becomes unconditional."""
    add = p.native('ListMenuAdd')
    found = []
    for i in range(len(p.items) - 6):
        a, b, c, d, e, f = p.items[i:i + 6]
        if (all(isinstance(x, Op) for x in (a, b, c, d, e, f)) and a.op == OP['LOAD_P_S_PRI'] and a.args == [20]
                and b.op == OP['JNZ'] and b.args == [VIDEO_MENU] and [x.op for x in (c, d, e)] == [OP['PUSH_P_C']] * 3
                and [x.args for x in (c, d, e)] == [[0], [1], [VIDEO_ITEM]] and f.op == OP['SYSREQ_N']
                and f.args[0] == add):
            found.append(i)
    if len(found) != 1:
        raise ValueError(f'video menu item not found once ({len(found)})')
    p.items[found[0]:found[0] + 2] = [Op(OP['JUMP'], [VIDEO_MENU])]
    return p


def hide_record(p):
    """The battle-record routine VIDEO_RECORD becomes `PROC; ZERO_PRI; RETN`: no «save the video?» applet."""
    record = p.native('SaveBattleRecord')
    at = [i for i, x in enumerate(p.items) if not isinstance(x, Op) and x[1] == VIDEO_RECORD]
    if len(at) != 1:
        raise ValueError(f'{VIDEO_RECORD} not found once')
    i = at[0]
    body = p.items[i + 1:i + 10]
    want = [(OP['PROC'], [0]), (OP['PUSH_P_S'], [12]), (OP['SYSREQ_N'], [record, 4]), (OP['PUSH_P_C'], [1]),
            (OP['PUSH_P_C'], [4]), (OP['CALL'], ['L4']), (OP['ZERO_PRI'], [0]), (OP['RETN'], [0])]
    if [(x.op, x.args) if isinstance(x, Op) else x for x in body[:8]] != want:
        raise ValueError(f'{VIDEO_RECORD} is not the measured record routine')
    p.items[i + 2:i + 7] = []
    return p


def palace_program(retail):
    """Zone 517's retail script with the Palace (module docstring)."""
    return hide_record(hide_video(tower.facility_program(retail, FACILITY)))


def zone_script(retail):
    """Built zone script bytes of the Palace's interior."""
    return palace_program(retail).build_script(f'L{retail.main:x}').build()
