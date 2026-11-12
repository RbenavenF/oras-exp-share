#!/usr/bin/env python3
"""Battle Arena, stage A (reports/diseno/arena.md §1): the zone script of its interior, a clone of the Battle Maison
hall, run as the Battle Tower (frontier/tower.py) with the Arena's own route, works and BP.

Singles, Level 50, rank Normal, with the player's own team chosen on the Maison's screens (mode selection, then the
party selection 0x457c, untouched; the order chosen is the battle order), 7 battles a round, an own streak and record
by streak route 4 (patch.STREAK_ROUTES), BP of data.FRONTIER_BP['arena'] after the 7th battle of each round, pause and
resume as the Maison, and the mutual exclusion with the other facilities (factory.busy_check, patch.ACTIVE_WORK).

Stage B: bit31 marks Arena battles, with switching forbidden and Body judgement after three turns
(frontier/arena_engine.py); Mind and Skill remain outside this implementation.

Greta (F8-CEREBRO-ARENA): battles 28/56, then every 28 after both symbols, using brains.py's private teams,
identity, texts and persistent Guts symbols. Her battles keep the Arena rules. Reception offers «Symbols».
Doubles and Open Level remain outside this implementation.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import brains  # noqa: E402
import factory  # noqa: E402
import data as fd  # noqa: E402
import patch  # noqa: E402
import tower  # noqa: E402

FACILITY = 'arena'
ZONE = 457                       # frontier/REPARTO.md; checked statically by frontier/zone_check.py (§29)
ROUTE = patch.ROUTE[FACILITY]
STREAK, ACTIVE, RECORD = (patch.STREAK_ROUTES[ROUTE][1] + k for k in range(3))
ARENA_BP = fd.FRONTIER_BP[FACILITY]


def arena_program(retail):
    """Zone 517's retail script with the Arena (module docstring)."""
    p = tower.facility_program(retail, FACILITY)
    brains.symbols_option(p, FACILITY, factory.LINE_SYMBOLS)
    return p


def zone_script(retail):
    """Built zone script bytes of the Arena's interior."""
    return arena_program(retail).build_script(f'L{retail.main:x}').build()
