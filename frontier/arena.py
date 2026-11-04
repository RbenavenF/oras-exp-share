#!/usr/bin/env python3
"""Battle Arena, stage A (reports/diseno/arena.md §1): the zone script of its interior, a clone of the Battle Maison
hall, run as the Battle Tower (frontier/tower.py) with the Arena's own route, works and BP.

Singles, Level 50, rank Normal, with the player's own team chosen on the Maison's screens (mode selection, then the
party selection 0x457c, untouched; the order chosen is the battle order), 7 battles a round, an own streak and record
by streak route 4 (patch.STREAK_ROUTES), BP of data.FRONTIER_BP['arena'] after the 7th battle of each round, pause and
resume as the Maison, and the mutual exclusion with the other facilities (factory.busy_check, patch.ACTIVE_WORK).

Stage A only: no 3-turn limit, no judgement and switching is allowed. Those need the battle engine and are stage B
(design §1, §2). Same known deviations as the Tower and the Palace: the Maison's texts («Mansión Batalla»), its party
rules, its boss on the streak; no Greta, Doubles or Open Level.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
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
    return tower.facility_program(retail, FACILITY)


def zone_script(retail):
    """Built zone script bytes of the Arena's interior."""
    return arena_program(retail).build_script(f'L{retail.main:x}').build()
