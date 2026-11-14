"""Noland: seed replay, generated Pawn, and dynamic native construction."""
import struct

import pytest

import test_frontier_factory as factory_tests
import test_frontier_brains as base
from test_frontier_factory import game
from test_frontier_brains import scripts
import brains
import factory
import factory_brain as noland
import modes
import patch
from pawn_vm import VM


@pytest.mark.parametrize('streak', [20, 41, 62, 83, 104])
@pytest.mark.parametrize('seconds', [1, 1000, 1234567, 0x7FFFFFFF])
def test_replay_all_six_and_generate_legal_rival(game, streak, seconds):
    sets, table, _, script, labels, *_ = game
    works, menus, _ = factory_tests.draft(game, [0, 1, 2], streak=streak, seconds=seconds)
    works[factory.WORK_STREAK] = streak
    expected_offers, expected_team = noland.team(sets, works[factory.WORK_RNG], streak)
    actual_offers = [i | (patch.SUPER if rank == 'S' else 0) for rank, i in factory_tests.offered(menus, table)]
    assert expected_offers == actual_offers
    stubs = factory_tests.natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                                  'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1])})
    VM(script, stubs, {}).run(labels['factory_brain'])
    actual_team = [works[w] for w in patch.WORK_RIVAL]
    assert actual_team == expected_team
    assert not set(actual_team) & set(actual_offers)
    members = [sets['S' if v & patch.SUPER else 'N'][v & 1023] for v in actual_team]
    assert len({s['species'] for s in members}) == 3
    items = [s['item'] for s in members if s['item']]
    assert len(set(items)) == len(items)
    assert all(s['species'] != 201 for s in members)
    before = dict(works)
    VM(script, stubs, {}).run(labels['factory_brain'])
    assert works == before  # paused/resumed battle gets the same team without the clock


@pytest.mark.parametrize('symbols', [0, 1, 2, 3])
def test_script_thresholds_and_repeats(scripts, symbols):
    for streak in [19, 20, 21, 40, 41, 42, 61, 62, 63, 83]:
        expected = brains.due('factory', streak + 1, 3 if symbols == 2 else symbols)
        assert base.check(scripts, 'factory', 1, streak, symbols) == (1 + 8 * expected if expected else 0)


@pytest.mark.parametrize('variant,previous,expected', [(1, 0, 1), (2, 1, 3), (1, 3, 3)])
@pytest.mark.parametrize('config', [0, 0x164])
def test_factory_symbol_and_bonus_only_once(scripts, variant, previous, expected, config):
    script, labels = scripts['factory']
    works = {patch.WORK_ROUTE: 1, modes.CONFIG[1]: config,
             brains.WORK_BRAIN: 1 + 8 * variant, brains.WORK_SYMBOLS: previous | 0x3000}
    paid = []
    stubs = base.natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                          'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                          'GlobalCall': lambda vm, a: 0})
    for _ in range(2):
        VM(script, stubs, {labels['L30']: lambda vm, a: paid.append(a[0])}).run(labels['brains_won'])
    assert works[brains.WORK_SYMBOLS] == expected | 0x3000
    assert works[brains.WORK_BRAIN] == 0 and paid == [10]


@pytest.mark.parametrize('variant,iv,ids', [(1, 15, [170, 185, 200]),
                                        (2, 31, [0x8000 | 104, 0x8000 | 558, 0x8000 | 600])])
@pytest.mark.parametrize('config,level', [(0, 50), (0x164, 100)])
def test_native_preserves_dynamic_team_across_retail_builder(variant, iv, ids, config, level):
    uc, ar, put = base.machine(1, 1 + 8 * variant, trainer=brains.trainer_id('factory', variant), config=config)
    works = base.SAVE + 0x13144
    for w, v in zip(patch.WORK_RIVAL, ids):
        put(works + 2 * (w - 0x4000), v, '<H')
    put(works + 2 * (patch.WORK_IV - 0x4000), 9, '<H')
    made, seen = iter(base.TEMPS), []

    def retail(m, r):
        for w in patch.WORK_RIVAL:
            put(works + 2 * (w - 0x4000), 229, '<H')
        return 0x55

    def load(m, r):
        m.mem_write(r[3], struct.pack('<5HBBHH', 1, 216, 1, 218, 216, 3, 0, 0, 0))

    def make(m, r):
        seen.append(struct.unpack('<5HBBHH', m.mem_read(r[0], 16)))
        return next(made)

    c = brains.CODE
    stubs = {c['CODE_START']: retail, c['CODE_LOAD_SET']: load, c['CODE_MAKE_PARAM']: make,
             c['CODE_EV_SET']: lambda m, r: pytest.fail('Noland must keep rental EVs'),
             c['CODE_FRIENDSHIP']: lambda m, r: None, c['CODE_GET_MAX_HP']: lambda m, r: 99,
             c['CODE_SET_HP']: lambda m, r: None, c['CODE_COPY']: lambda m, r: None}
    result, calls = base.run(uc, ar, base.START_SITE, (base.WORK, 1, 0), stubs)
    assert result == 0x55
    assert [v[1:5] for v in seen] == [(218, 1, 218, 218)] * 3
    loads = [v for v in calls if v[0] == c['CODE_LOAD_SET']]
    assert [v[2:4] for v in loads] == [(0xB8 if i & 0x8000 else 0xB6, i & 1023) for i in ids]
    assert [v[2:5] for v in calls if v[0] == c['CODE_MAKE_PARAM']] == [(level, iv, base.HEAP)] * 3
    assert [v[2] for v in calls if v[0] == c['CODE_FRIENDSHIP']] == [0, 0, 0]
    assert [struct.unpack('<H', uc.mem_read(works + 2 * (w - 0x4000), 2))[0] for w in patch.WORK_RIVAL] == ids
    assert struct.unpack('<H', uc.mem_read(works + 2 * (patch.WORK_IV - 0x4000), 2))[0] == 9


@pytest.mark.parametrize('variant,symbols', [(1, 0), (2, 1), (2, 3)])
def test_factory_loss_clears_pending_before_retail_streak_cleanup(scripts, variant, symbols):
    """Execute the real loss branch through ClearWinCount; no award can run first."""
    from pawn_vm import Stop
    script, labels = scripts['factory']
    works = {patch.WORK_ROUTE: 1, patch.WORK_IV: 9,
             patch.WORK_FSTREAK: 20 if variant == 1 else 41,
             patch.WORK_FRECORD: 50, brains.WORK_BRAIN: 1 + 8 * variant,
             brains.WORK_SYMBOLS: symbols | 0x3000}
    reached = []

    def clear(vm, args):
        assert works[patch.WORK_IV] == works[brains.WORK_BRAIN] == 0
        assert works[brains.WORK_SYMBOLS] == symbols | 0x3000
        assert works[patch.WORK_FRECORD] == 50
        reached.append('ClearWinCount')
        raise Stop

    stubs = {h: lambda vm, a: pytest.fail(f'Unexpected loss native {h}') for _, h in script.natives}
    said = []
    stubs.update(base.natives({'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                               'WorkGet': lambda vm, a: works.get(a[0], 0),
                               'GlobalCall': lambda vm, a: said.append((a[0], works[brains.WORK_MSG])),
                               'GetMyWinCount': lambda vm, a: works[patch.WORK_FSTREAK],
                               'ClearWinCount': clear}))
    with pytest.raises(Stop):
        VM(script, stubs, {labels['L533c']: lambda vm, a: 0,
                           labels['L3fdc']: lambda vm, a: 0,
                           labels['L30']: lambda vm, a: pytest.fail('No BP on a loss')}).run(labels[factory.LOST])
    assert reached == ['ClearWinCount']
    assert said == [(brains.GLOBAL_SAY, brains.MORE)]       # Noland's line, once, before the loss is saved
