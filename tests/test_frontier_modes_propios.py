"""F9 reception contract in Pawn VM; no claim of emulator coverage here."""
import pytest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]

import factory
import modes
import overlay
import patch
import tower
from pawn import gf_hash, s32
from pawn_vm import VM


@pytest.fixture(scope='module', params=tower.MODE_FACILITIES)
def facility(request):
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    name = request.param
    _, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    p = tower.facility_program(retail, name)
    return name, p.build_script(f'L{retail.main:x}'), p.layout()


def reception(facility, config=0, active=0, choice=0, accepted=1, kind=0, declined=False):
    name, script, labels = facility
    route = patch.ROUTE[name]
    old, old_record = modes.bank(route, 0)
    new, new_record = modes.bank(route, 1)
    works = {modes.CONFIG[route]: config, patch.ACTIVE_WORK[name]: active,
             old: 12, old_record: 20, new: 6, new_record: 9}
    before = dict(works)
    log = []
    def app(vm, args):
        log.append(('app', args))
        works.update({0x800C: accepted, 0x800D: kind, 0x800E: 7})
    def challenge(vm, args):
        log.append(('challenge', args, dict(works)))
        return int(declined)
    def wins(vm, args):
        mode = modes.unpack_config(route, works[modes.CONFIG[route]])[0]
        return works[modes.bank(route, mode)[0]]
    natives = {'WorkGet': lambda vm, a: works.get(a[0], 0),
               'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
               'SetRank': lambda vm, a: log.append(('rank', a)),
               'FlagGet': lambda vm, a: 0,
               'GetMyWinCount': wins,
               'ListMenuAdd': lambda vm, a: log.append(('item', a))}
    calls = {labels[tower.MODE_APP]: app, labels[factory.CHALLENGE]: challenge,
             labels[f'L{factory.MENU_INIT:x}']: lambda vm, a: 0,
             labels[f'L{factory.MENU_RUN:x}']: lambda vm, a: choice}
    for addr in (factory.MSG, factory.MSG_WAIT, factory.MSG_CLOSE):
        calls[labels[f'L{addr:x}']] = lambda vm, a: 0
    result = VM(script, {s32(gf_hash(k)): v for k, v in natives.items()}, calls).run(labels[f'{name}_reception'])
    return result, before, works, log


@pytest.mark.parametrize('choice', (0, 1))
def test_new_challenge_clears_only_its_mode_bank(facility, choice):
    result, before, works, log = reception(facility, choice=choice)
    route = patch.ROUTE[facility[0]]
    state = next(e[2] for e in log if e[0] == 'challenge')
    assert result == 0
    assert ('rank', [0]) in log
    assert state[modes.CONFIG[route]] == (0x13C if choice else 0)
    assert state[patch.ACTIVE_WORK[facility[0]]] == tower.NEW_ACTIVE
    assert state[modes.bank(route, choice)[0]] == 0
    assert state[modes.bank(route, 1-choice)[0]] == before[modes.bank(route, 1-choice)[0]]
    for mode in (0, 1):
        record = modes.bank(route, mode)[1]
        assert works[record] == before[record]


@pytest.mark.parametrize('config', (0, 50, 0x13C, 0x149, 0x164))
def test_resume_keeps_config_banks_and_has_no_level_menu(facility, config):
    _, before, works, log = reception(facility, active=1, config=config)
    assert all(works[w] == v for w, v in before.items())
    assert [e[1][0] for e in log if e[0] == 'item'] == [tower.LINE_RESUME, tower.LINE_ABANDON, 55]
    assert next(e[1] for e in log if e[0] == 'challenge') == [0, 0, 7]


@pytest.mark.parametrize('config', (0, 50, 0x149))
def test_retire_preserves_records_other_bank_and_bp(facility, config):
    result, before, works, log = reception(facility, active=1, config=config, choice=1)
    route = patch.ROUTE[facility[0]]
    mode = modes.unpack_config(route, config)[0]
    expected = dict(before)
    expected[modes.bank(route, mode)[0]] = 0
    expected[patch.ACTIVE_WORK[facility[0]]] = 0
    assert result == 1 and works == expected
    assert not [e for e in log if e[0] in ('app', 'rank', 'challenge')]


@pytest.mark.parametrize('active,config', ((0, 0), (1, 0x149)))
@pytest.mark.parametrize('choice', (2, -1, 65535, 3))
def test_menu_cancel_does_not_write_any_state(facility, active, config, choice):
    result, before, works, log = reception(facility, active=active, config=config, choice=choice)
    assert result == 1 and works == before
    assert not [e for e in log if e[0] in ('app', 'rank', 'challenge')]


@pytest.mark.parametrize('config', (0x100, 0x13B, 0x165, 0x232, 0x349, 0xFFFF))
def test_corrupt_paused_config_is_refused_without_destroying_it(facility, config):
    result, before, works, log = reception(facility, active=1, config=config)
    assert result == 1 and works == before and not log


@pytest.mark.parametrize('accepted,kind', ((0, 0), (1, 1), (1, 2), (1, 3), (1, 4)))
def test_selector_cancel_or_wrong_format_keeps_saved_state(facility, accepted, kind):
    result, before, works, log = reception(facility, choice=1, accepted=accepted, kind=kind)
    assert result == 1
    assert all(works[w] == v for w, v in before.items())
    assert not [e for e in log if e[0] in ('rank', 'challenge')]


def test_unregistered_open_cancellation_does_not_read_retail_streak(facility):
    result, before, works, _ = reception(facility, choice=1, declined=True)
    route = patch.ROUTE[facility[0]]
    assert result == 1 and works[patch.ACTIVE_WORK[facility[0]]] == 0
    assert works[modes.bank(route, 0)[0]] == before[modes.bank(route, 0)[0]]
    assert works[modes.CONFIG[route]] == 0x13C  # valid fallback until accepted selection fixes L


@pytest.mark.parametrize('round_number', (1, 2, 29, 30, 31))
@pytest.mark.parametrize('delta', (-1, 0, 1))
def test_reward_boundaries_use_facility_table(facility, round_number, delta):
    import data
    from test_frontier_tower import battle_points_run
    name, script, labels = facility
    route = patch.ROUTE[name]
    streak = round_number * tower.STAGES.get(name, 7) + delta
    log = battle_points_run((None, None, script, labels, None, None), streak, route=route)
    expected = data.FRONTIER_BP[name][min(round_number, 30) - 1]
    assert log == ([('bp', expected), ('number', expected)] if delta == 0 else [])


@pytest.mark.parametrize('symbols', (0, 1, 3))
def test_brain_boundaries_and_symbols_are_shared_with_level_50(facility, symbols):
    import brains
    name, script, labels = facility
    route = patch.ROUTE[name]
    open_streak, _ = modes.bank(route, 1)
    symbols_word = symbols << (2 * (route - 1))
    for threshold in brains.APPEARANCES[name][:2]:
        for offset in (-1, 0, 1):
            unit = threshold + offset
            works = {patch.WORK_ROUTE: route, modes.CONFIG[route]: 0x149,
                     open_streak: unit - 1, brains.WORK_SYMBOLS: symbols_word}
            def count(vm, args):
                assert args == [0, 0]
                return works[open_streak]
            stubs = {'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                     'GetMyWinCount': count, 'GlobalCall': lambda vm, a: 0}
            VM(script, {s32(gf_hash(k)): v for k, v in stubs.items()}, {}).run(labels['brains_check'])
            variant = brains.due(name, unit, symbols)
            assert works[brains.WORK_BRAIN] == (route + 8 * variant if variant else 0)
            assert works[brains.WORK_SYMBOLS] == symbols_word
