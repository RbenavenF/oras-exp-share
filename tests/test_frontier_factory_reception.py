"""Run the shared preflight with its real draft, then the zone challenge adapter."""
import pytest
import test_frontier_factory as ft
from test_frontier_factory import game
import factory
import factory_open as fo
import factory_reception as fr
import modes
import patch
from pawn_vm import VM


def preflight(game, works, choices):
    script, labels = game[3:5]
    state, results, menus = {'menu': []}, [], []
    def menu(vm, args):
        menus.append(state['menu'])
        return choices.pop(0)
    stubs = ft.natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        '_GetRealTimeToSecond': lambda vm, a: 1234567,
        'ListMenuAdd': lambda vm, a: state['menu'].append(a),
        'GlobalSetParentParam': lambda vm, a: results.append(a[1])})
    helpers = {name: labels[f'z{name}_{address:x}'] for name, address in factory.HELPERS.items()}
    calls = {helpers['msg']: lambda vm, a: 0, helpers['msg_wait']: lambda vm, a: 0,
        helpers['msg_close']: lambda vm, a: 0,
        helpers['menu_init']: lambda vm, a: state.__setitem__('menu', []), helpers['menu_run']: menu}
    VM(script, stubs, calls).run(labels['factory_prepare'])
    return results[-1], menus


def initial(iv=0, config=0x164):
    works = {modes.CONFIG[1]: config, patch.WORK_IV: iv,
             fo.WORK_PENDING_RENT: 2, fo.WORK_DRAFT_RENTS: 29,
             factory.WORK_STREAK: 20, factory.WORK_RNG: 55}
    for mode in range(4):
        s, record = modes.bank(1, mode)
        works.update({s: 10 + mode, record: 50 + mode, modes.FACTORY_RENTS[mode]: 22 + mode})
    works.update(dict(zip(patch.WORK_SETS, (66, 67, 68))))
    works.update(dict(zip(patch.WORK_RIVAL, (70, 71, 72))))
    return works


@pytest.mark.parametrize('mode', [0, 1])
def test_real_draft_new_inscription_clears_only_selected_streak_and_count(game, mode):
    works = initial()
    before = dict(works)
    result, menus = preflight(game, works, [mode, 0, 1, 2])
    assert result == 1 and [len(m) for m in menus] == [3, 6, 5, 4]
    assert works[modes.CONFIG[1]] == (0x164 if mode else 0)
    assert works[modes.bank(1, mode)[0]] == works[modes.FACTORY_RENTS[mode]] == 0
    assert works[fo.WORK_PENDING_RENT] == mode + 1
    assert works[patch.WORK_IV] == 3 and works[factory.WORK_STREAK] == 0
    for m in range(4):
        assert works[modes.bank(1, m)[1]] == before[modes.bank(1, m)[1]]
        if m != mode:
            for w in (modes.bank(1, m)[0], modes.FACTORY_RENTS[m]):
                assert works[w] == before[w]
    sets = game[0]
    offered = [ft.set_of_line(x[0]) for x in menus[1]]
    if mode:
        assert all(s in fo.pool(1) for s in offered)  # old count must not promote first draft
        assert works[fo.WORK_DRAFT_RENTS] == 0
    else:
        assert all(r == 'N' and 66 <= i <= 131 for r, i in offered)


@pytest.mark.parametrize('mode', [0, 1])
@pytest.mark.parametrize('draft', [[65535], [0, 65535], [0, 1, 65535]])
def test_draft_cancel_restores_config_counter_snapshot_and_all_previous_works(game, mode, draft):
    works = initial()
    before = dict(works)
    result, _ = preflight(game, works, [mode, *draft])
    assert result == 0 and works == before


@pytest.mark.parametrize('choice', [2, 65535, -1, 7])
def test_level_cancel_is_side_effect_free(game, choice):
    works = initial()
    before = dict(works)
    result, _ = preflight(game, works, [choice])
    assert result == 0 and works == before


@pytest.mark.parametrize('config', [0, 50, 0x164])
@pytest.mark.parametrize('choice', [0, 2, 65535, -1, 7])
def test_paused_resume_or_cancel_preserves_every_saved_value(game, config, choice):
    works = initial(iv=12, config=config)
    before = dict(works)
    result, menus = preflight(game, works, [choice])
    assert result == int(choice == 0)
    assert len(menus) == 1 and works == before


@pytest.mark.parametrize('config', [1, 100, 0x13c, 0x165, 0x232, 0x364, 65535])
def test_invalid_paused_config_is_refused_without_any_mutation(game, config):
    works = initial(iv=12, config=config)
    before = dict(works)
    result, menus = preflight(game, works, [])
    assert result == 0 and not menus and works == before


@pytest.mark.parametrize('mode,config', [(0, 0), (0, 50), (1, 0x164)])
def test_retire_clears_only_active_bank_preserving_records_and_other_modes(game, mode, config):
    works = initial(iv=12, config=config)
    before = dict(works)
    result, _ = preflight(game, works, [1])
    assert result == 0 and works[patch.WORK_IV] == 0
    assert works[modes.bank(1, mode)[0]] == works[modes.FACTORY_RENTS[mode]] == 0
    for work in (fo.WORK_PENDING_RENT, fo.WORK_DRAFT_RENTS, factory.WORK_RNG,
                 factory.WORK_STREAK, *patch.WORK_SETS, *patch.WORK_RIVAL):
        assert works[work] == 0
    for m in range(4):
        assert works[modes.bank(1, m)[1]] == before[modes.bank(1, m)[1]]
        if m != mode:
            assert works[modes.bank(1, m)[0]] == before[modes.bank(1, m)[0]]
            assert works[modes.FACTORY_RENTS[m]] == before[modes.FACTORY_RENTS[m]]


def test_declining_confirmation_when_resuming_keeps_draft_and_streak(game):
    result, works, _ = ft.reception(game, chosen=0, declined=True, iv=12, fstreak=20)
    assert result == 1 and works[patch.WORK_IV] == 12
    assert works[patch.WORK_FSTREAK] == 20 and works[patch.WORK_ROUTE] == 0


@pytest.mark.parametrize('mode,config', [(0, 0), (0, 50), (1, 0x164)])
def test_loss_cleanup_of_rental_counter_does_not_erase_other_mode_or_records(game, mode, config):
    works = initial(iv=12, config=config)
    before = dict(works)
    script, labels = game[-2:]
    stubs = ft.natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1])})
    VM(script, stubs).run(labels['factory_clear_rents'])
    assert works[modes.FACTORY_RENTS[mode]] == 0
    for w, value in before.items():
        if w != modes.FACTORY_RENTS[mode]:
            assert works[w] == value
