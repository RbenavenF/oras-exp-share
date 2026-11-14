"""F9 shared mode keys and saved-work allocation (REPARTO, 2026-11-13).

The native engine (frontier/asm/modes.s, linked by patch.mode_constants) and the Tower reception
(tower.config_check) use these tables; no mode menu is enabled yet (F9-LIBRE-*).
New banks have explicit record addresses: there was insufficient space for the
eleven unused S+1 holes proposed in modos.md. MODE/LEVEL share one CONFIG u16 per
route after the laboratory found three additional unsafe works. Legacy M=0
addresses are unchanged.
Runtime persistence: reports/modos-base.md (Azahar evidence, per milestone).
"""
import patch
import data as fd

SINGLE_50, SINGLE_OPEN, DOUBLE_50, DOUBLE_OPEN = range(4)
CONFIG = dict(enumerate((16546, 16573, 16594, 16603, 16635, 16637, 16638), 1))
NEW_BANKS = {
    (1, SINGLE_OPEN): (16690, 16691), (2, SINGLE_OPEN): (16695, 16719),
    (3, SINGLE_OPEN): (16734, 16735), (4, SINGLE_OPEN): (16738, 16739),
    (5, SINGLE_OPEN): (16741, 16743), (6, SINGLE_OPEN): (16745, 16746),
    (7, SINGLE_OPEN): (16747, 16749),
    (1, DOUBLE_50): (16750, 16751), (2, DOUBLE_50): (16753, 16754),
    (1, DOUBLE_OPEN): (16755, 16757), (2, DOUBLE_OPEN): (16758, 16759),
}
FACTORY_SET3, FACTORY_RIVAL3 = 16646, 16647
FACTORY_RENTS = (16451, 16455, 16456, 16469)
RESERVED = (*[w for bank in NEW_BANKS.values() for w in bank],
            *CONFIG.values(), FACTORY_SET3, FACTORY_RIVAL3, *FACTORY_RENTS)
FIELD_AT, FIELD_END = 0xF0A00, 0xF1000
SELECTION_CODE = {'CODE_PARTY_SLOT': 0x3B6150, 'CODE_GET_LEVEL': 0x14FD1C}
SELECTION_HEADS = {0x3B6150: 0xE3510006, 0x14FD1C: 0xE92D4070}


def valid(route, mode):
    return route in patch.STREAK_ROUTES and mode in range(4) and (mode < 2 or route in (1, 2))


def pack_config(route, mode, level):
    """Persistent mode and opponent level, independent of the retail rank byte."""
    if not valid(route, mode):
        raise ValueError('invalid route/mode')
    levels = (100,) if route == 1 and mode & 1 else range(60, 101) if mode & 1 else (50,)
    if level not in levels:
        raise ValueError('invalid opponent level')
    return mode << 8 | level


def unpack_config(route, word):
    """(M,L), or None for corrupt/unsupported settings; zero is legacy 50."""
    if route not in CONFIG or not 0 <= word <= 0x3FF:
        return None
    if word == 0:
        return SINGLE_50, 50
    mode, level = word >> 8, word & 0xFF
    try:
        pack_config(route, mode, level)
    except ValueError:
        return None
    return mode, level


def bank(route, mode):
    """(streak, record) works, or None for retail/invalid combinations.

    Rank guards are the caller's responsibility. Streak access remains available
    after ACTIVE is cleared by LOST; level hooks require ACTIVE separately.
    This does not reinterpret a retail Super rank as a level mode.
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


def selection_config(route, mode, levels, *, persisted=None):
    """Registration API: CONFIG after an accepted, complete inscription.

    `levels` describes the effective selection (Battle Box when selected), not
    the whole party or only the Dome's two fighters. Call before save/start.
    On resume the validated saved CONFIG is authoritative. The caller leaves
    works/PB untouched on ValueError or cancellation; this has no side effects.
    This API neither enables a reception menu nor queries the game's selection.
    """
    if not valid(route, mode):
        raise ValueError('invalid route/mode')
    if persisted is not None:
        config = unpack_config(route, persisted)
        if config is None or config[0] != mode:
            raise ValueError('invalid resumed configuration')
        return persisted
    if route == 1:
        return pack_config(route, mode, 100 if mode & 1 else 50)
    levels = tuple(levels)
    if len(levels) != (4 if mode >= DOUBLE_50 else 3) or any(
            type(level) is not int or not 1 <= level <= 100 for level in levels):
        raise ValueError('incomplete or invalid effective selection')
    return pack_config(route, mode, max(60, *levels) if mode & 1 else 50)


def assemble_selection():
    """Native registration API in the previously reserved Field cave. No callback
    or reception calls it yet: accepted/new/resume must be explicit at that caller.
    Descriptor ABI and side effects: frontier/asm/modes_selection.s.
    """
    blob, symbols = patch.link(
        [patch.ROOT / 'frontier/asm/modes_selection.s'], FIELD_AT, 'mode_register',
        {**patch.mode_constants(), 'ROUTE_OFF': 2 * (patch.WORK_ROUTE - 0x4000)},
        {**SELECTION_CODE, 'CODE_MODE_OF': patch.assemble()[1]['mode_of']})
    if FIELD_AT + len(blob) > FIELD_END:
        raise ValueError('registration API exceeds the F9 Field reservation')
    return blob, symbols


def cro_writes():
    """Unreachable API payload; no hook until callback linkage is measured.
    patch.battle_cro supplies v0.5 identity, rehash and CRR validation.
    """
    blob, _ = assemble_selection()
    return [dict(offset=FIELD_AT, before=bytes(len(blob)).hex(), after=blob.hex())]
