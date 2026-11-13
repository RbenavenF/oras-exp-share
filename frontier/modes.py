"""F9 shared mode keys and saved-work allocation (REPARTO, 2026-11-13).

Preparation API only: no reception or native hook imports this module yet.
New banks have explicit record addresses: there was insufficient space for the
eleven unused S+1 holes proposed in modos.md. Legacy M=0 addresses are unchanged.
Runtime persistence must be measured before enabling any new mode.
"""
import patch
import data as fd

SINGLE_50, SINGLE_OPEN, DOUBLE_50, DOUBLE_OPEN = range(4)
MODE = dict(enumerate((16429, 16430, 16451, 16455, 16456, 16469, 16471), 1))
LEVEL = dict(enumerate((16546, 16573, 16594, 16603, 16635, 16637, 16638), 1))
NEW_BANKS = {
    (1, SINGLE_OPEN): (16690, 16691), (2, SINGLE_OPEN): (16695, 16719),
    (3, SINGLE_OPEN): (16734, 16735), (4, SINGLE_OPEN): (16738, 16739),
    (5, SINGLE_OPEN): (16741, 16743), (6, SINGLE_OPEN): (16745, 16746),
    (7, SINGLE_OPEN): (16747, 16749),
    (1, DOUBLE_50): (16750, 16751), (2, DOUBLE_50): (16753, 16754),
    (1, DOUBLE_OPEN): (16755, 16757), (2, DOUBLE_OPEN): (16758, 16759),
}
FACTORY_SET3, FACTORY_RIVAL3 = 16646, 16647
FACTORY_RENTS = (16673, 16677, 16678, 16398)
RESERVED = (*[w for bank in NEW_BANKS.values() for w in bank],
            *MODE.values(), *LEVEL.values(), FACTORY_SET3, FACTORY_RIVAL3, *FACTORY_RENTS)
FIELD_AT, FIELD_END = 0xF0A00, 0xF1000


def valid(route, mode):
    return route in patch.STREAK_ROUTES and mode in range(4) and (mode < 2 or route in (1, 2))


def bank(route, mode):
    """(streak, record) works, or None for retail/invalid combinations.

    Rank and active-state guards are the caller's responsibility. In particular,
    this does not reinterpret a retail Super rank as a level mode.
    """
    if not valid(route, mode):
        return None
    if mode == SINGLE_50:
        streak = patch.STREAK_ROUTES[route][1]
        return streak, streak + 2
    return NEW_BANKS[route, mode]


def battle_points(route, mode, round_no, brain=False):
    """Completed unit's PB; Libre uses its format's Level 50 column.

    Reject invalid combinations rather than award points from another bank.
    The caller handles unit completion and balance saturation exactly once.
    """
    if not valid(route, mode) or round_no < 1 or (brain and mode >= DOUBLE_50):
        raise ValueError('invalid mode, round or Doubles Brain')
    facility = patch.STREAK_ROUTES[route][0]
    columns = fd.FRONTIER_BP_DOUBLES if mode >= DOUBLE_50 else fd.FRONTIER_BP
    return columns[facility][min(round_no, 30) - 1] + (fd.BRAIN_BONUS if brain else 0)
