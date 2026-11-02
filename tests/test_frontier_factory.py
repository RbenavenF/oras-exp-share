"""Battle Factory reception (frontier/factory.py): the generated Pawn run in scripts/pawn_vm.py.

Natives and the retail routines the new code calls are stubbed; this checks the generated logic (levels,
draw rules, menus, saved works, exits), not GF's VM or the game (that is the Azahar test in
reports/frontier.md).
"""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import data as fd  # noqa: E402
import factory  # noqa: E402
import overlay  # noqa: E402
import patch as fp  # noqa: E402
from formats import garc_entries  # noqa: E402
from pawn import OP, Script, decode, gf_hash, s32  # noqa: E402
from pawn_vm import VM  # noqa: E402


def natives(table):
    return {s32(gf_hash(name)): fn for name, fn in table.items()}


@pytest.fixture(scope='module')
def game():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    sets, table, levels, cells = overlay.rentals()
    _, zone = overlay.maison_retail(overlay.ZONES.read_bytes())
    data = (overlay.ROMFS / overlay.SHARED).read_bytes()
    _, _, offset, length = garc_entries(data)[factory.SHARED_SCRIPT]
    shared = Script.parse(data[offset:offset + length])
    program = factory.shared_program(shared, zone, cells, levels)
    labels = program.layout()
    script = program.build_script(f'L{shared.main:x}')
    assert Script.parse(script.build(pad=False)).build(pad=False) == script.build(pad=False)
    reception = overlay.maison_program(zone)
    return sets, table, levels, script, labels, reception.build_script(f'L{zone.main:x}'), reception.layout()


def draft(game, choices, streak=0, seconds=1234567, rng=0):
    sets, table, levels, script, labels, _, _ = game
    works, menus, log = {factory.WORK_RNG: rng, factory.WORK_STREAK: streak}, [], []
    state = {'menu': None}

    def run_menu(vm, args):
        menus.append(state['menu'])
        return choices.pop(0)

    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        '_GetRealTimeToSecond': lambda vm, a: seconds,
        'ListMenuAdd': lambda vm, a: state['menu'].append((a[0], a[1], a[2])),
        'GlobalSetParentParam': lambda vm, a: log.append(('result', a)),
    })
    helper = {name: labels[f'z{name}_{address:x}'] for name, address in factory.HELPERS.items()}
    calls = {helper['msg']: lambda vm, a: log.append(('msg', a)),
             helper['msg_wait']: lambda vm, a: 0,
             helper['msg_close']: lambda vm, a: log.append(('close', a)),
             helper['menu_init']: lambda vm, a: state.__setitem__('menu', []),
             helper['menu_run']: run_menu}
    VM(script, stubs, calls).run(labels['factory_draft'])
    return works, menus, log


def offered(menus, table):
    return [table[line - factory.LINE_SLOTS] for line, _, _ in menus[0]]


@pytest.mark.parametrize('streak, level', [(0, 0), (6, 0), (7, 1), (20, 2), (21, 3), (48, 6), (49, 7), (400, 7)])
def test_draft_from_the_round_level(game, streak, level):
    sets, table, levels, *_ = game
    works, menus, log = draft(game, [2, 0, 5], streak=streak)
    first, count = levels[level]
    assert [len(m) for m in menus] == [6, 5, 4]
    lines = [line for line, _, _ in menus[0]]
    assert all(first <= line - factory.LINE_SLOTS < first + count for line in lines)
    drawn = [sets[r][i] for r, i in offered(menus, table)]
    assert len({s['species'] for s in drawn}) == 6 and len({s['item'] for s in drawn}) == 6
    assert log[-1] == ('result', [0, 1])
    assert works[fp.WORK_IV] == fd.fixed_iv(level + 1)
    for work, k in zip(fp.WORK_SETS, (2, 0, 5)):
        rank, index = table[lines[k] - factory.LINE_SLOTS]
        value = works[work]
        assert value & 0x3FF == index and bool(value & fp.SUPER) == (rank == 'S')
        assert (value >> fp.ABILITY_SHIFT) & 3 in (0, 1)


def test_menus_offer_only_the_remaining_rentals(game):
    _, menus, log = draft(game, [3, 1, 4])
    assert [v for _, v, _ in menus[0]] == [0, 1, 2, 3, 4, 5]
    assert [v for _, v, _ in menus[1]] == [0, 1, 2, 4, 5]
    assert [v for _, v, _ in menus[2]] == [0, 2, 4, 5]
    assert [a for e, a in log if e == 'msg'] == [[line, 1, 0, 256, 0] for line in factory.LINE_PICK]
    assert all(z == 0 for m in menus for _, _, z in m)


@pytest.mark.parametrize('choices', [[65535], [0, 65535], [0, 1, 65535], [0, 0]])
def test_cancel_reports_no_choice(game, choices):
    works, _, log = draft(game, choices)
    assert works.get(fp.WORK_IV) == 0 and log[-1] == ('result', [0, 0])
    assert ('close', [0]) in log
    assert all(works.get(w, 0) == 0 for w in fp.WORK_SETS)


def test_drafts_vary_with_the_clock_and_saved_state(game):
    sets, table, *_ = game
    seen = set()
    for seconds in range(20):
        works, menus, _ = draft(game, [0, 1, 2], seconds=1000 + seconds)
        seen.add(tuple(offered(menus, table)))
        assert works[factory.WORK_RNG] != 0
    assert len(seen) == 20
    _, a, _ = draft(game, [0, 1, 2], rng=0)
    _, b, _ = draft(game, [0, 1, 2], rng=1)
    assert offered(a, table) != offered(b, table)


def reception(game, chosen, declined=False, streak_before=0, streak_after=0, iv=21):
    *_, script, labels = game
    works, log = {fp.WORK_IV: iv}, []
    wins = [streak_before, streak_after]

    def challenge(vm, args):
        log.append(('challenge', args, dict(works)))
        return 1 if declined else 0

    stubs = natives({
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'GlobalCall': lambda vm, a: log.append(('global', a)),
        'GlobalGetChildParam': lambda vm, a: chosen,
        'SetRank': lambda vm, a: log.append(('rank', a)),
        'GetMyWinCount': lambda vm, a: wins.pop(0),
    })
    result = VM(script, stubs, {labels[factory.CHALLENGE]: challenge}).run(labels['factory_reception'])
    return result, works, log


def test_reception_plays_the_challenge(game):
    result, works, log = reception(game, chosen=1)
    assert result == 0 and log[0] == ('global', [factory.GLOBAL_DRAFT])
    assert ('rank', [0]) in log
    _, args, seen = next(e for e in log if e[0] == 'challenge')
    assert args == [0, 0, 0] and seen[0x800C] == 1 and seen[0x800D] == 0 and seen[0x800E] == 0
    assert seen[fp.WORK_IV] == 21 and works[fp.WORK_IV] == 0      # lost: Factory cleared


@pytest.mark.parametrize('before, passed', [(0, 0), (12, 12), (-1, 0)])
def test_reception_passes_the_streak_to_the_draft(game, before, passed):
    _, works, log = reception(game, chosen=0, streak_before=before)
    assert works[factory.WORK_STREAK] == passed and log[0] == ('global', [factory.GLOBAL_DRAFT])


def test_reception_keeps_a_paused_challenge(game):
    result, works, _ = reception(game, chosen=1, streak_after=3)
    assert result == 0 and works[fp.WORK_IV] == 21


@pytest.mark.parametrize('chosen, declined', [(0, False), (1, True)])
def test_reception_back_to_the_menu(game, chosen, declined):
    result, works, log = reception(game, chosen=chosen, declined=declined)
    assert result == 1 and works[fp.WORK_IV] == 0
    assert bool([e for e in log if e[0] == 'challenge']) == declined


def test_reception_entries(game):
    *_, script, labels = game
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    add = s32(gf_hash('ListMenuAdd'))
    menu = [ins[i - 1].args[0] for i, x in enumerate(ins) if labels['L14f4'] <= x.address < labels['L1634']
            and x.op == OP['SYSREQ_N'] and names[x.args[0]] == add]
    assert menu == [53, 54, 74, factory.LINE_OPTION, 55]
    work_set = s32(gf_hash('WorkSet'))
    clears = [x.address for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[i - 1].args == [fp.WORK_IV] and ins[i - 2].args == [0]]
    assert any(labels[factory.CLEANUP] < a < labels[factory.CLEANUP] + 0x20 for a in clears)
    assert any(labels[factory.RECEPTION_RESULT] < a < labels[factory.RECEPTION_RESULT] + 0x80 for a in clears)


def test_every_level_can_complete_a_draft(game):
    sets, table, levels, *_ = game
    factory.check_draws(sets, table, levels)
    assert [c for _, c in levels] == [66, 38, 38, 196, 196, 196, 196, 784]
