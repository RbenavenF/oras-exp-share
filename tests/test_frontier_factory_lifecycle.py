"""Factory rental accounting and Open exchange run as generated Pawn, not Python mirrors."""
import pytest

import test_frontier_factory as ft
from test_frontier_factory import game
import factory
import factory_open as fo
import modes
import patch
from pawn_vm import VM


@pytest.mark.parametrize('config,mark', [(0, 1), (50, 1), (0x164, 2), (0x13c, 0), (65535, 0)])
def test_successful_draft_marks_one_rental_without_credit(game, config, mark):
    works, _, _ = ft.draft(game, [0, 1, 2], extra={modes.CONFIG[1]: config,
        modes.FACTORY_RENTS[0]: 14, modes.FACTORY_RENTS[1]: 43})
    assert works.get(fo.WORK_PENDING_RENT, 0) == mark
    assert works[modes.FACTORY_RENTS[0]] == 14
    assert works[modes.FACTORY_RENTS[1]] == 43


@pytest.mark.parametrize('choices', [[65535], [0, 65535], [0, 1, 65535]])
def test_cancel_draft_keeps_pending_mark(game, choices):
    works, _, _ = ft.draft(game, choices, extra={modes.CONFIG[1]: 0x164,
                                               fo.WORK_PENDING_RENT: 2})
    assert works[fo.WORK_PENDING_RENT] == 2


def win(game, works, iv=12):
    script, labels = game[-2:]
    works[patch.WORK_IV] = iv
    stubs = ft.natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'GetMyWinCount': lambda vm, a: 1, 'GlobalCall': lambda vm, a: 0})
    VM(script, stubs).run(labels['factory_after_win'])


@pytest.mark.parametrize('mode,config', [(0, 0), (0, 50), (1, 0x164)])
@pytest.mark.parametrize('count', [0, 14, 21, 28, 35, 42, 65534, 65535])
def test_victory_credits_exactly_once_and_only_its_bank(game, mode, config, count):
    works = {modes.CONFIG[1]: config, fo.WORK_PENDING_RENT: mode + 1,
             **dict.fromkeys(modes.FACTORY_RENTS, count)}
    records = {modes.bank(1, m)[1]: 333 + m for m in range(4)}
    works.update(records)
    win(game, works)
    assert works[fo.WORK_PENDING_RENT] == 0
    for m, bank in enumerate(modes.FACTORY_RENTS):
        assert works[bank] == (min(count + 1, 65535) if m == mode else count)
    saved = dict(works)
    win(game, works)
    assert works == saved
    assert all(works[w] == value for w, value in records.items())


@pytest.mark.parametrize('config,mark', [(0, 2), (0x164, 1), (0x13c, 2), (0x364, 2), (0x164, 65535)])
def test_mismatched_or_corrupt_mark_is_consumed_without_credit(game, config, mark):
    works = {modes.CONFIG[1]: config, fo.WORK_PENDING_RENT: mark,
             **dict.fromkeys(modes.FACTORY_RENTS, 22)}
    win(game, works)
    assert works[fo.WORK_PENDING_RENT] == 0
    assert all(works[w] == 22 for w in modes.FACTORY_RENTS)


def test_retail_win_does_not_touch_factory_mark_or_banks(game):
    works = {fo.WORK_PENDING_RENT: 2, modes.FACTORY_RENTS[1]: 42}
    win(game, works, iv=0)
    assert works[fo.WORK_PENDING_RENT] == 2
    assert works[modes.FACTORY_RENTS[1]] == 42


def encoded(rank, index):
    return index | (patch.SUPER if rank == 'S' else 0)


def test_open_swap_rejects_duplicate_species_in_other_archive(game):
    sets = game[0]
    # Find by measured data, not by an assumed cross-archive index mapping.
    rival = next(i for i, s in enumerate(sets['N'][:208])
                 if s['species'] in {t['species'] for t in sets['S']})
    same = next(i for i, s in enumerate(sets['S']) if s['species'] == sets['N'][rival]['species'])
    mine = [patch.SUPER | 500, patch.SUPER | same, patch.SUPER | 907]
    works, _, _ = ft.swap(game, [0, 0], mine, [rival, 140, 207],
                        extra={modes.CONFIG[1]: 0x164})
    assert [works[w] for w in patch.WORK_SETS] == mine
    assert works.get(fo.WORK_PENDING_RENT, 0) == 0


def test_open_swap_rejects_duplicate_item_with_different_species(game):
    sets = game[0]
    a, b = next((i, j) for i, s in enumerate(sets['N'][:208]) for j, t in enumerate(sets['S'])
        if s['item'] and s['item'] == t['item'] and s['species'] != t['species'])
    mine = [patch.SUPER | 500, patch.SUPER | b, patch.SUPER | 907]
    works, _, _ = ft.swap(game, [0, 0], mine, [a, 140, 207], extra={modes.CONFIG[1]: 0x164})
    assert [works[w] for w in patch.WORK_SETS] == mine
    assert works.get(fo.WORK_PENDING_RENT, 0) == 0


@pytest.mark.parametrize('give', range(3))
def test_valid_open_swap_preserves_super_archive_and_marks_pending(game, give):
    sets = game[0]
    # Three compatible strong rentals plus a legendary opponent.
    candidate = fo.LEGENDARY_POOL[0]
    selected = [candidate]
    for rank, index in fo.OPEN_POOLS[0]:
        s = sets[rank][index]
        if all(s['species'] != sets[r][i]['species'] and
               (not s['item'] or s['item'] != sets[r][i]['item']) for r, i in selected):
            selected.append((rank, index))
        if len(selected) == 4:
            break
    mine = [encoded(*s) for s in selected[1:]]
    rival = encoded(*candidate)
    works, menus, _ = ft.swap(game, [give, 0], mine, [rival, 140, 207],
        extra={modes.CONFIG[1]: 0x164, modes.FACTORY_RENTS[1]: 42})
    assert menus[1][0][0] == factory.line_of(*candidate)
    assert works[patch.WORK_SETS[give]] & (patch.SUPER | 1023) == rival
    assert all(works[w] == mine[k] for k, w in enumerate(patch.WORK_SETS) if k != give)
    assert works[fo.WORK_PENDING_RENT] == 2 and works[modes.FACTORY_RENTS[1]] == 42
    win(game, works)
    assert works[modes.FACTORY_RENTS[1]] == 43
    assert works[fo.WORK_PENDING_RENT] == 0


@pytest.mark.parametrize('choices', [[3], [65535], [0, 65535], [1, 7], [-1], [0, -1]])
def test_no_change_cancel_and_invalid_choice_do_not_mark_rental(game, choices):
    works, _, _ = ft.swap(game, choices, ft.MINE, ft.RIVALS,
        extra={modes.CONFIG[1]: 0x164, modes.FACTORY_RENTS[1]: 22})
    assert works.get(fo.WORK_PENDING_RENT, 0) == 0
    assert works[modes.FACTORY_RENTS[1]] == 22
    assert [works[w] for w in patch.WORK_SETS] == list(ft.MINE)


def test_invalid_set_index_rejected_without_table_overread(game):
    works, _, _ = ft.swap(game, [0, 0], ft.MINE, [1023, 140, 207], extra={modes.CONFIG[1]: 0x164})
    assert [works[w] for w in patch.WORK_SETS] == list(ft.MINE)
    assert works.get(fo.WORK_PENDING_RENT, 0) == 0
