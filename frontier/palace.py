#!/usr/bin/env python3
"""Battle Palace, stage A (reports/diseno/palacio.md §1): the zone script of its interior, a clone of the Battle
Maison hall, run as the Battle Tower (frontier/tower.py) with the Palace's own route, works and BP.

Singles, Level 50, rank Normal, with the player's own team chosen on the Maison's screens (mode selection, then the
party selection 0x457c, untouched: the Tower showed the party screen refuses every Pokémon without the mode
selection, reports/frontier.md §25), 7 battles a round, an own streak and record by streak route 3
(patch.STREAK_ROUTES), BP of data.FRONTIER_BP['palace'] after the 7th battle of each round, pause and resume as the
Maison, and the mutual exclusion with the other facilities (factory.busy_check, patch.ACTIVE_WORK).

Stage A only: the player still gives the orders. The Palace's own rule (the Pokémon choose their moves by nature)
needs the battle engine and is stage B/C (design §1, §4). Same known deviations as the Tower: the Maison's texts
(«Mansión Batalla»), its party rules, its boss on the streak; no Spenser, Doubles or Open Level.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import data as fd  # noqa: E402
import patch  # noqa: E402
import tower  # noqa: E402

FACILITY = 'palace'
ZONE = 340                       # frontier/REPARTO.md; checked statically by frontier/zone_check.py (§27)
ROUTE = patch.ROUTE[FACILITY]
STREAK, ACTIVE, RECORD = (patch.STREAK_ROUTES[ROUTE][1] + k for k in range(3))
PALACE_BP = fd.FRONTIER_BP[FACILITY]


def palace_program(retail):
    """Zone 517's retail script with the Palace (module docstring)."""
    return tower.facility_program(retail, FACILITY)


def zone_script(retail):
    """Built zone script bytes of the Palace's interior."""
    return palace_program(retail).build_script(f'L{retail.main:x}').build()
