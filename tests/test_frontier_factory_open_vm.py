"""Execute generated draft/replay Pawn. Reception and Azahar remain separate acceptance."""
import pytest

import test_frontier_factory as ft
from test_frontier_factory import game
import data as fd
import factory
import factory_brain as noland
import factory_open as fo
import modes
import patch
from pawn_vm import VM


def decode(line):
    return (fo.LEGENDARY_POOL[line - fo.LINE_BASE] if line >= fo.LINE_BASE
            else ft.set_of_line(line))


@pytest.mark.parametrize('round_no', [1, 2, 3, 4, 5, 6, 7, 8, 9, 9363])
@pytest.mark.parametrize('rents', [0, 14, 15, 21, 22, 28, 29, 35, 36, 42, 43, 65535])
def test_open_draft_iv_promotion_snapshot_and_noland_replay(game, round_no, rents):
    sets, table, _, script, labels, *_ = game
    streak = (round_no - 1) * 7
    before = {modes.CONFIG[1]: 0x164, modes.FACTORY_RENTS[1]: rents,
              modes.FACTORY_RENTS[0]: 999, modes.bank(1, 0)[0]: 57,
              modes.bank(1, 1)[0]: streak, fo.WORK_DRAFT_RENTS: 123}
    works, menus, log = ft.draft(game, [0, 1, 2], streak=streak, extra=before)
    offers = [decode(line) for line, _, _ in menus[0]]
    assert [len(m) for m in menus] == [6, 5, 4]
    assert all(s in pool for s, pool in zip(offers, fo.draft_pools(round_no, rents)))
    members = [sets[r][i] for r, i in offers]
    assert len({s['species'] for s in members}) == len({s['item'] for s in members}) == 6
    assert works[patch.WORK_IV] == fd.fixed_iv(round_no)
    assert works[fo.WORK_DRAFT_RENTS] == rents
    assert all(works[w] == v for w, v in before.items() if w != fo.WORK_DRAFT_RENTS)
    expected_offers, rival = noland.team(sets, works[factory.WORK_RNG], streak, True, rents)
    assert expected_offers == [i | patch.SUPER for _, i in offers]
    assert [works[w] & ~ (3 << patch.ABILITY_SHIFT) for w in patch.WORK_SETS] == expected_offers[:3]
    # Several swaps can happen after the draft. The replay must use the snapshot.
    works[modes.FACTORY_RENTS[1]] = (rents + 6) & 65535
    works[factory.WORK_STREAK] = streak + 6
    stubs = ft.natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1])})
    VM(script, stubs, {}).run(labels['factory_brain'])
    assert [works[w] for w in patch.WORK_RIVAL] == rival
    assert not set(rival) & set(expected_offers)
    members = [sets['S'][v & 1023] for v in rival]
    assert len({s['species'] for s in members}) == 3
    items = [s['item'] for s in members if s['item']]
    assert len(set(items)) == len(items)
    saved = dict(works)
    VM(script, stubs, {}).run(labels['factory_brain'])
    assert works == saved


@pytest.mark.parametrize('choices', [[65535], [0, 65535], [0, 1, 65535], [0, 0]])
def test_cancel_keeps_saved_seed_snapshot_and_team(game, choices):
    initial = {modes.CONFIG[1]: 0x164, modes.FACTORY_RENTS[1]: 36,
               fo.WORK_DRAFT_RENTS: 22, **dict(zip(patch.WORK_SETS, [88, 89, 90]))}
    works, _, log = ft.draft(game, choices, rng=55, extra=initial)
    assert all(works[w] == v for w, v in initial.items())
    assert works[factory.WORK_RNG] == 55
    assert patch.WORK_IV not in works
    assert log[-1] == ('result', [0, 0])


@pytest.mark.parametrize('config', [0, 50, 0x13C, 0x165, 0x232, 0x364, 65535])
def test_only_valid_singles_open_config_changes_draft(game, config):
    # Unsupported/corrupt config is rejected by reception in the next milestone;
    # shared draft falls back to the unchanged level-50 path.
    _, normal, _ = ft.draft(game, [0, 1, 2], streak=14)
    works, actual, _ = ft.draft(game, [0, 1, 2], streak=14,
        extra={modes.CONFIG[1]: config, modes.FACTORY_RENTS[1]: 65535, fo.WORK_DRAFT_RENTS: 42})
    assert actual == normal
    assert works[fo.WORK_DRAFT_RENTS] == 42


def test_new_legendary_labels_do_not_overlap_existing_shared_text(game):
    assert len(fo.LEGENDARY_POOL) == 44
    assert [factory.line_of(r, i) for r, i in fo.LEGENDARY_POOL] == list(range(1134, 1178))
    assert min(factory.line_of(r, i) for r, i in fo.LEGENDARY_POOL) > 1133
    # Old slot metadata and every old menu line remain byte-for-byte stable.
    _, table, levels, *_ = game
    assert len(table) == 926
    assert [count for _, count in levels] == [66, 38, 38, 196, 196, 196, 196, 784]
    assert max(factory.line_of(r, i) for r, i in table) == 997


@pytest.mark.parametrize('index', [i for _, i in fo.LEGENDARY_POOL])
def test_swap_labels_resolve_every_legendary_set(game, index):
    works, menus, _ = ft.swap(game, [3], [index | patch.SUPER, 66, 67], [70, 71, 72])
    assert menus[0][0][0] == factory.line_of('S', index)
    assert works[patch.WORK_SETS[0]] == index | patch.SUPER


def test_legendary_offer_can_be_selected_and_replayed(game):
    sets, _, _, script, labels, *_ = game
    for seed in range(1000):
        offers, _ = noland.draw(sets, seed, 4, open_mode=True)
        legend_positions = [k for k, value in enumerate(offers) if ('S', value & 1023) in fo.LEGENDARY_POOL]
        if legend_positions:
            break
    else:
        pytest.fail('No legendary offered in 1000 seeds')
    k = legend_positions[0]
    choices = [k] + [i for i in range(6) if i != k][:2]
    works, menus, _ = ft.draft(game, choices, streak=28, seconds=seed,
        extra={modes.CONFIG[1]: 0x164, modes.FACTORY_RENTS[1]: 0})
    assert menus[0][k][0] == factory.line_of('S', offers[k] & 1023)
    assert works[patch.WORK_SETS[0]] & ~(3 << patch.ABILITY_SHIFT) == offers[k]
