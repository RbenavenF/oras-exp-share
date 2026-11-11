#!/usr/bin/env python3
"""Battle Palace, stage A (reports/diseno/palacio.md §1): the zone script of its interior, a clone of the Battle
Maison hall, run as the Battle Tower (frontier/tower.py) with the Palace's own route, works and BP.

Singles, Level 50, rank Normal, with the player's own team chosen on the Maison's screens (mode selection, then the
party selection 0x457c, untouched: the Tower showed the party screen refuses every Pokémon without the mode
selection, reports/frontier.md §25), 7 battles a round, an own streak and record by streak route 3
(patch.STREAK_ROUTES), BP of data.FRONTIER_BP['palace'] after the 7th battle of each round, pause and resume as the
Maison, and the mutual exclusion with the other facilities (factory.busy_check, patch.ACTIVE_WORK).

Stage B (reports/frontier.md §32): in its battles the game's AI decides for the player's Pokémon (frontier/asm/
palace.s, frontier/palace_engine.py; nature table in stage C). The battle video does not record
those decisions, so the Palace's «next battle» menu drops «Guardar vídeo» (VIDEO_ITEM, `hide_video`) and the
record routine offered after a loss or at the end (VIDEO_RECORD: SaveBattleRecord + wait) returns at once. Same known deviations as the Tower: the Maison's texts
(«Mansión Batalla»), its party rules; no Doubles or Open Level.

Frontier Brain (F8-CEREBRO-PALACIO, frontier/brains.py): Spenser at battles 21/42 and every 21 after both symbols
(brains.APPEARANCES), with his fixed teams (reports/diseno/cerebros.md §7), no Maison boss on route 3, and «Symbols»
in the reception menu (value brains.MENU_SYMBOLS). His battle keeps the Palace engine (B/C: the AI decides for the
player's Pokémon by nature); the rival side is the game's usual AI.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import brains  # noqa: E402
import data as fd  # noqa: E402
import factory  # noqa: E402
import patch  # noqa: E402
import tower  # noqa: E402

# Kept as aliases for the Palace probes and earlier callers; shared by all seven facilities.
from battle_video import VIDEO_MENU, VIDEO_ITEM, VIDEO_RECORD, hide_video, hide_record  # noqa: E402

FACILITY = 'palace'
ZONE = 340                       # frontier/REPARTO.md; checked statically by frontier/zone_check.py (§27)
ROUTE = patch.ROUTE[FACILITY]
STREAK, ACTIVE, RECORD = (patch.STREAK_ROUTES[ROUTE][1] + k for k in range(3))
PALACE_BP = fd.FRONTIER_BP[FACILITY]


def palace_program(retail):
    """Zone 517's retail script with the Palace (module docstring) and «Symbols» in its reception menu (Spenser's
    symbol, brains.symbols_option; text 619 line factory.LINE_SYMBOLS, as the Factory and the Tower)."""
    p = tower.facility_program(retail, FACILITY)
    brains.symbols_option(p, FACILITY, factory.LINE_SYMBOLS)
    return p


def zone_script(retail):
    """Built zone script bytes of the Palace's interior."""
    return palace_program(retail).build_script(f'L{retail.main:x}').build()
