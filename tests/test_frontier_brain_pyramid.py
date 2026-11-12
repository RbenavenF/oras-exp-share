"""Brandon, the Pyramid's Brain (F8-CEREBRO-PIRAMIDE, reports/diseno/cerebros.md §1, §5, §7): the summit after the
floor is counted, its pending state, the symbols and the BP, in the Pawn VM. VM runs are not evidence of the game."""
import struct

import pytest

from test_frontier_pyramid import retail, floor, lobby, natives, maps  # noqa: F401
import brains
import data as fd
import patch as fp
import pyramid as py
from pawn_vm import VM

SHIFT = 2 * (py.ROUTE - 1)
SILVER_LINE = lambda key: 4 * (py.ROUTE - 1) + brains.KEYS.index(key)   # noqa: E731
LOST_LINE = brains.MORE + 4 * (py.ROUTE - 1)
TOWER_STREAK = fp.STREAK_ROUTES[fp.ROUTE['tower']][1]   # another facility's work: untouched


def run(floor, routine, works, win=1):
    script, labels = floor
    works = dict(works)
    log = []

    def gcall(vm, a):
        if a[0] == py.GLOBAL_SAY:
            log.append(('say', works[py.WORK_MSG] & 0xFF))
        elif a[0] == brains.GLOBAL_SAY:
            log.append(('brain', works[brains.WORK_MSG]))
        else:
            log.append(('global', a[0]))

    def battle(vm, a):
        log.append(('battle', works.get(brains.WORK_BRAIN, 0), works.get(fp.WORK_ROUTE)))
    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'GlobalCall': gcall,
        'BattleInstWorkCreate': lambda vm, a: log.append(('create',)),
        'BattleInstWorkDelete': lambda vm, a: log.append(('delete',)),
        'SetRank': lambda vm, a: log.append(('rank', a[0])),
        'SetTrainer': lambda vm, a: log.append(('trainer', a[0])),
        'StartBattle': battle,
        'IsWin': lambda vm, a: win,
        '_MapChangeCore': lambda vm, a: log.append(('map', *a)),
    })
    calls = {labels[n]: (lambda vm, a: 0) for n in (py.TALK_START, py.TALK_END, *(c[0] for c in py.AFTER_BATTLE))}
    calls[labels[py.ADD_BP]] = lambda vm, a: log.append(('bp', a[0]))
    VM(script, stubs, calls).run(labels[routine])
    return works, log


def top(streak_before, symbols=0, extra=None):
    """Floor 7 just cleared, `streak_before` floors counted before it."""
    return {py.ACTIVE: 7, py.STREAK: streak_before, py.RECORD: streak_before, fp.WORK_ROUTE: py.ROUTE,
            py.WORK_BEATEN: 7, brains.WORK_SYMBOLS: symbols << SHIFT, **(extra or {})}


def challenge_bp(streak):
    return fd.FRONTIER_BP['pyramid'][min(streak // 7, len(fd.FRONTIER_BP['pyramid'])) - 1]


@pytest.mark.parametrize('symbols', [0, 1, 2, 3])
def test_thresholds_after_counting_the_floor(floor, symbols):
    """Every challenge end up to floor 210: Brandon exactly when brains.due says, by the floors counted (21, 70...)."""
    seen = []
    for streak in range(7, 211, 7):
        works, log = run(floor, 'pyramid_stairs', top(streak - 1, symbols))
        battles = [x for x in log if x[0] == 'battle']
        expect = brains.due('pyramid', streak, 3 if symbols == 2 else symbols)
        assert battles == ([('battle', py.ROUTE + 8 * expect, py.ROUTE)] if expect else []), streak
        if expect:
            seen.append((streak, expect))
    assert seen == {0: [(21, 1)], 1: [(70, 2)], 2: [(21, 1), (70, 2), (105, 2), (140, 2), (175, 2), (210, 2)],
                    3: [(21, 1), (70, 2), (105, 2), (140, 2), (175, 2), (210, 2)]}[symbols]


@pytest.mark.parametrize('floor_number', range(1, 7))
def test_lower_floors_never_call_brandon(floor, floor_number):
    works, log = run(floor, 'pyramid_stairs', {py.ACTIVE: floor_number, py.STREAK: 20, py.RECORD: 20,
                                               fp.WORK_ROUTE: py.ROUTE, py.WORK_BEATEN: 7})
    assert not any(x[0] in ('battle', 'bp', 'brain') for x in log)
    assert works.get(py.WORK_SUMMIT, 0) == 0
    assert works[py.STREAK] == 21 and works[py.ACTIVE] == floor_number + 1


def test_not_due_closes_the_challenge_as_before(floor):
    works, log = run(floor, 'pyramid_stairs', top(13))
    assert not any(x[0] in ('battle', 'brain') for x in log) and works.get(py.WORK_SUMMIT, 0) == 0
    assert [x for x in log if x[0] == 'bp'] == [('bp', challenge_bp(14))]
    assert (works[py.STREAK], works[py.ACTIVE], works[fp.WORK_ROUTE], works[py.WORK_BEATEN]) == (14, 0, 0, 0)
    assert works.get(brains.WORK_BRAIN, 0) == 0 and maps(log) == [(*py.LOBBY_RETURN, 0, 0, 1, 0)]


@pytest.mark.parametrize('variant,streak,initial', [(1, 20, 0), (2, 69, 1), (1, 20, 3), (2, 69, 3), (2, 104, 3)])
def test_win_symbol_bonus_once_and_floor_counted_once(floor, variant, streak, initial):
    works, log = run(floor, 'pyramid_stairs', top(streak, initial, {TOWER_STREAK: 5}))
    counted = streak + 1
    assert [x for x in log if x[0] not in ('say', 'map')] == [
        ('brain', SILVER_LINE('intro_silver') + variant - 1), ('create',), ('rank', 0), ('trainer', 0),
        ('battle', py.ROUTE + 8 * variant, py.ROUTE), ('delete',), ('bp', fd.BRAIN_BONUS),
        ('brain', SILVER_LINE('won_silver') + variant - 1), ('bp', challenge_bp(counted))]
    expected_symbols = (initial | (1 if variant == 1 else 3)) << SHIFT
    assert works[brains.WORK_SYMBOLS] == expected_symbols and works[TOWER_STREAK] == 5
    assert (works[py.STREAK], works[py.RECORD]) == (counted, counted)          # the Brain adds no floor
    assert (works[py.ACTIVE], works[fp.WORK_ROUTE], works[py.WORK_BEATEN], works[py.WORK_SUMMIT],
            works[brains.WORK_BRAIN]) == (0, 0, 0, 0, 0)
    assert maps(log) == [(*py.LOBBY_RETURN, 0, 0, 1, 0)]


@pytest.mark.parametrize('initial', [0, 1, 3])
def test_loss_ends_the_challenge_keeping_symbols_and_record(floor, initial):
    streak = {0: 20, 1: 69, 3: 69}[initial]
    works, log = run(floor, 'pyramid_stairs', top(streak, initial, {py.RECORD: 300}), win=0)
    assert ('brain', LOST_LINE) in log and ('say', py.MSG['lost']) in log
    assert not any(x[0] == 'bp' for x in log)
    assert works[brains.WORK_SYMBOLS] == initial << SHIFT and works[py.RECORD] == 300
    assert (works[py.STREAK], works[py.ACTIVE], works[fp.WORK_ROUTE], works[py.WORK_BEATEN], works[py.WORK_SUMMIT],
            works[brains.WORK_BRAIN]) == (0, 0, 0, 0, 0, 0)
    assert maps(log) == [(*py.LOBBY_RETURN, 0, 0, 1, 0)]


def test_record_is_counted_before_brandon(floor):
    works, log = run(floor, 'pyramid_stairs', top(20, 0, {py.RECORD: 5}), win=0)
    assert works[py.RECORD] == 21 and works[py.STREAK] == 0


@pytest.mark.parametrize('variant', [1, 2])
def test_pending_summit_after_a_reload_is_not_skipped_nor_counted_again(floor, variant):
    """A save after the floor was counted holds WORK_SUMMIT: the attendant goes straight to Brandon."""
    streak = 21 if variant == 1 else 70
    state = {py.ACTIVE: 7, py.STREAK: streak, py.RECORD: streak, fp.WORK_ROUTE: 0, py.WORK_BEATEN: 7,
             py.WORK_SUMMIT: variant, brains.WORK_SYMBOLS: (0 if variant == 1 else 1) << SHIFT}
    works, log = run(floor, 'pyramid_stairs', state)
    assert ('battle', py.ROUTE + 8 * variant, py.ROUTE) in log
    assert [x for x in log if x[0] == 'bp'] == [('bp', fd.BRAIN_BONUS), ('bp', challenge_bp(streak))]
    assert works[py.STREAK] == streak and works[py.WORK_SUMMIT] == 0
    assert not ('say', py.MSG['floor']) in log


def test_pending_summit_keeps_the_floor_trainers_beaten(floor):
    state = {py.ACTIVE: 7, py.STREAK: 21, py.WORK_BEATEN: 7, py.WORK_SUMMIT: 1}
    for k in range(py.TRAINERS):
        works, log = run(floor, f'pyramid_trainer{k}', state)
        assert log == [('say', py.MSG['beaten'])] and works == {**state, py.WORK_MSG: py.MSG['beaten']}


def test_pending_is_written_before_the_battle(floor):
    """The pending state is set before StartBattle, so a reset during Brandon's battle (nothing saved since the
    counted floor was saved) comes back to the summit, never to the floor's trainers."""
    script, labels = floor
    works = top(20)
    seen = {}

    def battle(vm, a):
        seen.update(summit=works.get(py.WORK_SUMMIT), streak=works[py.STREAK], brain=works.get(brains.WORK_BRAIN))
    nothing = lambda vm, a: 0   # noqa: E731
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0), 'WorkSet': lambda vm, a: works.__setitem__(*a[:2]),
                     'StartBattle': battle, 'IsWin': lambda vm, a: 1, 'GlobalCall': nothing,
                     'BattleInstWorkCreate': nothing, 'BattleInstWorkDelete': nothing, 'SetRank': nothing,
                     'SetTrainer': nothing, '_MapChangeCore': nothing})
    calls = {labels[n]: (lambda vm, a: 0) for n in (py.TALK_START, py.TALK_END, py.ADD_BP,
                                                     *(c[0] for c in py.AFTER_BATTLE))}
    VM(script, stubs, calls).run(labels['pyramid_stairs'])
    assert seen == {'summit': 1, 'streak': 21, 'brain': py.ROUTE + 8}


@pytest.mark.parametrize('k', range(py.TRAINERS))
def test_ordinary_trainers_never_get_a_brain(floor, k):
    works, log = run(floor, f'pyramid_trainer{k}', {py.ACTIVE: 7, py.STREAK: 20, py.WORK_BEATEN: 0,
                                                    brains.WORK_BRAIN: py.ROUTE + 8})
    assert ('battle', 0, py.ROUTE) in log and works[py.WORK_BEATEN] == 1 << k


def test_retire_clears_a_pending_summit(lobby):
    from test_frontier_pyramid import run_lobby
    works, log = run_lobby(lobby, {py.ACTIVE: 7, py.STREAK: 21, py.RECORD: 21, py.WORK_SUMMIT: 1,
                                   brains.WORK_SYMBOLS: 1}, answers=(py.NO, py.YES))
    assert (works[py.ACTIVE], works[py.STREAK], works[py.WORK_SUMMIT], works[py.RECORD]) == (0, 0, 0, 21)
    assert works[brains.WORK_SYMBOLS] == 1


@pytest.mark.parametrize('bits,line', [(0, 1), (1, 2), (2, 3), (3, 3)])
def test_lobby_symbols_receptionist(lobby, bits, line):
    script, labels = lobby
    works = {brains.WORK_SYMBOLS: (bits << SHIFT) | 0b01, fp.ACTIVE_WORK['tower']: 1}
    said = []
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                     'GlobalCall': lambda vm, a: said.append((a[0], works[brains.WORK_MSG]))})
    calls = {labels[n]: (lambda vm, a: 0) for n in (py.TALK_START, py.TALK_END)}
    VM(script, stubs, calls).run(labels['pyramid_symbols'])
    assert said == [(brains.GLOBAL_SAY, LOST_LINE + line)]


def test_lobby_event_3_is_the_symbols_receptionist(retail):
    from pawn import Op, OP
    p = py.lobby_program(retail)
    at = py.factory._index(p, f'L{retail.main:x}')
    table = next(o for o in p.items[at:] if isinstance(o, Op) and o.op == OP['CASETBL'])
    stub = dict(zip(table.args[2::2], table.args[3::2]))[py.SYMBOLS_EVENT]
    start = py.factory._index(p, stub)
    call = next(o for o in p.items[start:] if isinstance(o, Op) and o.op == OP['CALL'])
    assert call.args == ['pyramid_symbols']


def test_brandon_exact_teams_and_identity():
    expected = {
        1: (16, [(377, 217, 3, (152, 152, 0, 0, 106, 100), (153, 276, 89, 246)),
                 (379, 234, 3, (152, 152, 0, 0, 6, 200), (89, 232, 92, 334)),
                 (378, 150, 15, (106, 0, 152, 0, 100, 152), (58, 133, 87, 156))]),
        2: (31, [(144, 232, 16, (6, 0, 252, 252, 0, 0), (59, 352, 332, 115)),
                 (145, 157, 16, (6, 0, 252, 252, 0, 0), (87, 197, 65, 113)),
                 (146, 213, 16, (6, 0, 252, 252, 0, 0), (126, 63, 332, 219))])}
    rows = brains.brain_rows()
    for v, (iv, team) in expected.items():
        trainer = brains.trainer_id('pyramid', v)
        assert trainer == 140 + v
        assert fd.parse_trainer(brains.trainers()[trainer]) == {
            'class': 96, 'sets': tuple(brains.set_index('pyramid', v, k) for k in range(3))}
        at = brains.ENTRY * (12 + v - 1)
        assert struct.unpack_from('<HBB', rows, at) == (trainer, iv, 0)
        for k, (species, item, nature, ev, moves) in enumerate(team):
            idx = brains.set_index('pyramid', v, k)
            assert 259 <= idx <= 264
            s = fd.parse_set(brains.sets()[idx])
            assert (s['species'], s['item'], s['nature'], s['moves']) == (species, item, nature, moves)
            hp, atk, df, spe, spa, spd = ev
            assert struct.unpack_from('<H6B', rows, at + 4 + 8 * k) == (idx, hp, atk, df, spa, spd, spe)
    assert brains.trainer_names()[12:14] == ['Brandon', 'Brandon']
    assert brains.APPEARANCES['pyramid'] == (21, 70, 35) and 'pyramid' in brains.ENABLED


def test_floor_and_lobby_fit(retail):
    scripts = py.zone_scripts(retail)
    assert all(len(raw) < py.ZO_LIMIT - 600 for raw in scripts.values())
