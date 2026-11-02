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


def set_of_line(line):
    """(rank, index) shown by a TEXT_FACTORY line."""
    if line < factory.LINE_S:
        return 'N', line - factory.LINE_N
    return next(('S', first + line - start) for first, last, start in factory.super_lines()
                if start <= line <= start + last - first)


def offered(menus, table):
    return [set_of_line(line) for line, _, _ in menus[0]]


@pytest.mark.parametrize('streak, level', [(0, 0), (6, 0), (7, 1), (20, 2), (21, 3), (48, 6), (49, 7), (400, 7)])
def test_draft_from_the_round_level(game, streak, level):
    sets, table, levels, *_ = game
    works, menus, log = draft(game, [2, 0, 5], streak=streak)
    first, count = levels[level]
    assert [len(m) for m in menus] == [6, 5, 4]
    lines = [line for line, _, _ in menus[0]]
    assert all(set_of_line(line) in table[first:first + count] for line in lines)
    drawn = [sets[r][i] for r, i in offered(menus, table)]
    assert len({s['species'] for s in drawn}) == 6 and len({s['item'] for s in drawn}) == 6
    assert log[-1] == ('result', [0, 1])
    assert works[fp.WORK_IV] == fd.fixed_iv(level + 1)
    for work, k in zip(fp.WORK_SETS, (2, 0, 5)):
        rank, index = set_of_line(lines[k])
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
    assert fp.WORK_IV not in works and log[-1] == ('result', [0, 0])
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


def reception(game, chosen, declined=False, streak_before=0, streak_after=0, iv=0):
    """iv: WORK_IV on entry (0 = new sign-up). The stubbed draft writes IV 21 when it reports a choice."""
    *_, script, labels = game
    works, log = {fp.WORK_IV: iv}, []
    wins = [streak_before, streak_after]

    def challenge(vm, args):
        log.append(('challenge', args, dict(works)))
        return 1 if declined else 0

    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'GlobalCall': lambda vm, a: log.append(('global', a)) or (chosen and works.__setitem__(fp.WORK_IV, 21)),
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


def test_reception_resumes_a_paused_factory_without_a_draft(game):
    result, works, log = reception(game, chosen=0, streak_before=4, iv=21)  # paused: WORK_IV != 0 on entry
    assert result == 0 and not [e for e in log if e[0] == 'global']
    assert [e for e in log if e[0] == 'challenge'][0][1] == [0, 0, 0] and works[fp.WORK_IV] == 21


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
    assert any(labels[factory.LOST] <= a < labels[factory.LOST] + 0x10 for a in clears)


def test_every_level_can_complete_a_draft(game):
    sets, table, levels, *_ = game
    factory.check_draws(sets, table, levels)
    assert [c for _, c in levels] == [66, 38, 38, 196, 196, 196, 196, 784]


def test_text_lines_cover_rentals_and_rivals(game):
    sets, table, *_ = game
    seen = {factory.line_of(r, i) for r, i in table} | {factory.line_of('N', i) for i in range(208)}
    assert len(seen) == len(set(table) | {('N', i) for i in range(208)})
    assert all(set_of_line(factory.line_of(r, i)) == (r, i) for r, i in table)


def swap(game, choices, mine, rivals):
    script, labels = game[3], game[4]
    works = {**dict(zip(fp.WORK_SETS, mine)), **dict(zip(fp.WORK_RIVAL, rivals))}
    menus, log, state = [], [], {'menu': None}

    def run_menu(vm, args):
        menus.append(state['menu'])
        return choices.pop(0)

    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]) or log.append(('set', a)),
        'ListMenuAdd': lambda vm, a: state['menu'].append((a[0], a[1], a[2])),
    })
    helper = {name: labels[f'z{name}_{address:x}'] for name, address in factory.HELPERS.items()}
    calls = {helper['msg']: lambda vm, a: log.append(('msg', a[0])),
             helper['msg_wait']: lambda vm, a: 0,
             helper['msg_close']: lambda vm, a: log.append(('close', a)),
             helper['menu_init']: lambda vm, a: state.__setitem__('menu', []),
             helper['menu_run']: run_menu}
    VM(script, stubs, calls).run(labels['factory_swap'])
    return works, menus, log


MINE = (66 | 1 << fp.ABILITY_SHIFT, fp.SUPER | 500, fp.SUPER | fp.ABILITY_RANDOM << fp.ABILITY_SHIFT | 907)
RIVALS = (12, 140, 207)


@pytest.mark.parametrize('give, take', [(0, 0), (1, 2), (2, 1)])
def test_swap_replaces_the_rental_given_away(game, give, take):
    works, menus, log = swap(game, [give, take], MINE, RIVALS)
    assert [e[1] for e in log if e[0] == 'msg'] == [factory.LINE_SWAP_GIVE, factory.LINE_SWAP_TAKE]
    assert [line for line, _, _ in menus[0]] == [factory.line_of('N', 66), factory.line_of('S', 500),
                                                factory.line_of('S', 907), factory.LINE_NO_SWAP]
    assert [line for line, _, _ in menus[1]] == [factory.line_of('N', r) for r in RIVALS]
    new = works[fp.WORK_SETS[give]]
    assert new & 0x3FF == RIVALS[take] and not new & fp.SUPER and (new >> fp.ABILITY_SHIFT) & 3 in (0, 1)
    assert all(works[fp.WORK_SETS[k]] == MINE[k] for k in range(3) if k != give)
    assert log[-1] == ('close', [0])


@pytest.mark.parametrize('choices', [[3], [65535], [0, 65535], [1, 7]])
def test_swap_declined_keeps_the_team(game, choices):
    works, _, log = swap(game, choices, MINE, RIVALS)
    assert not [e for e in log if e[0] == 'set'] and log[-1] == ('close', [0])


def after_win(game, streak, iv=21, draft_results=(1,)):
    *_, script, labels = game
    works, log, results = {fp.WORK_IV: iv}, [], list(draft_results)
    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'GetMyWinCount': lambda vm, a: streak,
        'GlobalCall': lambda vm, a: log.append(a[0]),
        'GlobalGetChildParam': lambda vm, a: results.pop(0),
    })
    VM(script, stubs).run(labels['factory_after_win'])
    return works, log


@pytest.mark.parametrize('streak', [1, 6, 8, 13, 20, 22])
def test_after_a_win_the_swap_is_offered(game, streak):
    works, log = after_win(game, streak)
    assert log == [factory.GLOBAL_SWAP] and works[factory.WORK_STREAK] == streak


@pytest.mark.parametrize('streak', [7, 14, 49])
def test_every_seven_wins_a_new_draft_until_chosen(game, streak):
    works, log = after_win(game, streak, draft_results=(0, 0, 1))
    assert log == [factory.GLOBAL_DRAFT] * 3 and works[factory.WORK_STREAK] == streak


def test_after_win_does_nothing_for_the_maison(game):
    works, log = after_win(game, 7, iv=0)
    assert log == [] and factory.WORK_STREAK not in works


def test_after_win_is_called_from_the_battle_loop(game):
    *_, script, labels = game
    ins = decode(script.code)
    calls = [x for x in ins if x.op == OP['CALL'] and x.address + x.args[0] == labels['factory_after_win']]
    assert len(calls) == 1 and labels[factory.AFTER_BATTLE] < calls[0].address < labels[factory.AFTER_BATTLE] + 0x20


def battle_points_run(game, streak, iv=21):
    *_, script, labels = game
    log = []
    stubs = natives({
        'WorkGet': lambda vm, a: iv if a[0] == fp.WORK_IV else 0,
        'GetMyWinCount': lambda vm, a: streak,
        'GetWinCount': lambda vm, a: 99,
    })
    calls = {labels['L30']: lambda vm, a: log.append(('bp', a[0]))}
    for name in ('Lfc', 'L2c8', 'L634', 'L5d4', 'L618'):
        calls[labels[name]] = lambda vm, a: 0
    stubs[s32(gf_hash('WordSetNumber'))] = lambda vm, a: log.append(('number', a[1]))
    VM(script, stubs, calls).run(labels[factory.BATTLE_POINTS], 0, 0, 0)
    return log


@pytest.mark.parametrize('streak, bp', [(7, 3), (14, 3), (21, 4), (49, 6), (91, 9), (700, 9)])
def test_factory_battle_points_at_the_end_of_a_round(game, streak, bp):
    assert battle_points_run(game, streak) == [('bp', bp), ('number', bp)]


@pytest.mark.parametrize('streak', [1, 6, 8, 13, 20])
def test_no_factory_battle_points_inside_a_round(game, streak):
    assert battle_points_run(game, streak) == []


def test_maison_battle_points_unchanged(game):
    assert battle_points_run(game, 7, iv=0) == [('bp', 2), ('number', 2)]       # GetWinCount 99 > 10: 2 BP
