"""Battle Tower v1 (frontier/tower.py): its zone script, run in scripts/pawn_vm.py with stubbed natives and retail
routines, and the mutual exclusion with the Factory. Checks the generated logic, not the game (Azahar: reports/
frontier.md §25)."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import data as fd  # noqa: E402
import factory  # noqa: E402
import overlay  # noqa: E402
import patch as fp  # noqa: E402
import tower  # noqa: E402
from formats import zo_build  # noqa: E402
from pawn import OP, Op, Program, Script, decode, gf_hash, s32  # noqa: E402
from pawn_vm import VM  # noqa: E402

MSG = {f'L{a:x}' for a in (factory.MSG, factory.MSG_WAIT, factory.MSG_CLOSE)}


def natives(table):
    return {s32(gf_hash(name)): fn for name, fn in table.items()}


@pytest.fixture(scope='module')
def built():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    files, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    program = tower.tower_program(retail)
    labels = program.layout()
    script = program.build_script(f'L{retail.main:x}')
    factory_program = overlay.maison_program(retail)
    return files, retail, script, labels, factory_program.build_script(f'L{retail.main:x}'), factory_program.layout()


def test_tower_script_round_trips_and_fits(built):
    files, retail, script, _, _, _ = built
    raw = tower.zone_script(retail)
    assert raw == script.build() and Script.parse(raw).build() == raw
    container = zo_build([*files[:2], raw, *files[3:]])
    assert len(container) <= 17248          # the largest zone container measured to load (§11)



def test_tower_menu_is_the_maisons_and_party_selection_is_retail(built):
    _, retail, script, labels, _, _ = built
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    add = s32(gf_hash('ListMenuAdd'))
    menu = [ins[i - 1].args[0] for i, x in enumerate(ins) if labels['L14f4'] <= x.address < labels['L1634']
            and x.op == OP['SYSREQ_N'] and names[x.args[0]] == add]
    # no «Battle Factory» entry; «Symbols» (Anabel's, F8-CEREBRO-TORRE) before «Nothing»
    assert menu == tower.RECEPTION_MENU[:-1] + [factory.LINE_SYMBOLS] + tower.RECEPTION_MENU[-1:]

    def routine(program):
        at = program.items.index(('label', f'L{overlay.PARTY_SELECT:x}'))
        out = []
        for item in program.items[at + 1:]:
            if isinstance(item, Op):
                if item.op == OP['PROC'] and out:
                    break
                out.append((item.op, list(item.args)))
            else:
                out.append(item)
        return out
    assert routine(tower.tower_program(retail)) == routine(Program.from_script(retail))


def reception(built, active=None, declined=False, streak_after=0, tower_active=0, tower_streak=0, mode=(1, 0, 7),
              extra=None):
    """Runs tower_reception. `active`: {facility: value} of other facilities' ACTIVE_WORK."""
    _, _, script, labels, _, _ = built
    works = {fp.ACTIVE_WORK[f]: v for f, v in (active or {}).items()}
    works.update({tower.ACTIVE: tower_active, tower.STREAK: tower_streak, **(extra or {})})
    log = []
    wins = [streak_after]

    def challenge(vm, args):
        log.append(('challenge', args, dict(works)))
        return 1 if declined else 0

    def app(vm, args):
        log.append(('app', args))
        works.update({0x800C: mode[0], 0x800D: mode[1], 0x800E: mode[2]})
        return 0

    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'FlagGet': lambda vm, a: a[0] - 380,
        'SetRank': lambda vm, a: log.append(('rank', a)),
        'GetMyWinCount': lambda vm, a: log.append(('wins', dict(works))) or wins[0],
    })
    calls = {labels[factory.CHALLENGE]: challenge, labels[f'L{factory.MSG:x}']: lambda vm, a: log.append(('msg', a)),
             labels[tower.MODE_APP]: app}
    calls.update({labels[m]: (lambda vm, a: 0) for m in MSG - {f'L{factory.MSG:x}'}})
    result = VM(script, stubs, calls).run(labels['tower_reception'])
    return result, works, log


def test_a_new_tower_challenge(built):
    result, works, log = reception(built, tower_streak=9)
    assert result == 0 and ('rank', [0]) in log
    assert ('msg', [tower.MSG_MODE, 1, 0, 256, 0]) in log
    assert ('app', [0, 0x800C, 0x800D, 0x800E, 5, 6, 7, 8, 9]) in log      # as 0x16fc: flags 385-389
    _, args, seen = next(e for e in log if e[0] == 'challenge')
    assert args == [0, 0, 7]                                              # rank 0, Singles, work 0x800E
    assert seen[fp.WORK_ROUTE] == tower.ROUTE == 2 and seen[tower.ACTIVE] == 1 and seen[tower.STREAK] == 0
    assert works[fp.WORK_ROUTE] == 0 and works[tower.ACTIVE] == 0      # lost: no challenge in progress
    assert all(e[1][fp.WORK_ROUTE] == 2 for e in log if e[0] == 'wins')  # the streak read is the Tower's


def test_a_paused_tower_challenge_stays_active_and_resumes(built):
    _, works, _ = reception(built, streak_after=3)
    assert works[tower.ACTIVE] == 1 and works[fp.WORK_ROUTE] == 0
    result, works, log = reception(built, tower_active=1, tower_streak=6, streak_after=7)
    seen = next(e for e in log if e[0] == 'challenge')[2]
    assert result == 0 and seen[tower.STREAK] == 6 and works[tower.STREAK] == 6 and works[tower.ACTIVE] == 1


@pytest.mark.parametrize('active, streak, kept', [(0, 0, 0), (1, 4, 1)])
def test_declining_goes_back_to_the_menu(built, active, streak, kept):
    result, works, _ = reception(built, declined=True, tower_active=active, tower_streak=streak, streak_after=streak)
    assert result == 1 and works[tower.ACTIVE] == kept and works[fp.WORK_ROUTE] == 0


@pytest.mark.parametrize('mode', [(0, 0, 0), (1, 1, 0), (1, 4, 0)])
def test_only_accepted_singles_start_a_challenge(built, mode):
    result, works, log = reception(built, mode=mode, tower_streak=5)
    assert result == 1 and not [e for e in log if e[0] in ('challenge', 'rank')]
    assert works[tower.STREAK] == 5 and fp.WORK_ROUTE not in works


@pytest.mark.parametrize('other', [f for f in fp.ACTIVE_WORK if f != 'tower'])
def test_tower_refuses_while_another_facility_is_in_progress(built, other):
    result, works, log = reception(built, active={other: 21 if other == 'factory' else 1}, tower_streak=5)
    assert result == 1 and not [e for e in log if e[0] in ('challenge', 'rank', 'app')]
    assert ('msg', [factory.LINE_BUSY, 1, 0, 256, 0]) in log
    assert works[tower.STREAK] == 5 and fp.WORK_ROUTE not in works


def factory_reception(built, active):
    *_, script, labels = built
    works = {fp.ACTIVE_WORK[f]: v for f, v in active.items()}
    log = []
    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'GlobalCall': lambda vm, a: log.append(('global', a)),
        'GlobalGetChildParam': lambda vm, a: 0,
        'SetRank': lambda vm, a: log.append(('rank', a)),
        'GetMyWinCount': lambda vm, a: 0,
    })
    calls = {labels[factory.CHALLENGE]: lambda vm, a: log.append(('challenge', a)) or 0,
             labels[f'L{factory.MSG:x}']: lambda vm, a: log.append(('msg', a))}
    calls.update({labels[m]: (lambda vm, a: 0) for m in MSG - {f'L{factory.MSG:x}'}})
    return VM(script, stubs, calls).run(labels['factory_reception']), works, log


def test_factory_refuses_while_the_tower_is_in_progress(built):
    result, works, log = factory_reception(built, {'tower': 1})
    assert result == 1 and ('msg', [factory.LINE_BUSY, 1, 0, 256, 0]) in log
    assert not [e for e in log if e[0] in ('global', 'challenge', 'rank')]
    assert works == {tower.ACTIVE: 1}                 # nothing written
    result, _, log = factory_reception(built, {'tower': 0})
    assert [e for e in log if e[0] == 'global'] and not [e for e in log if e[0] == 'msg']


def test_lost_and_cleanup_clear_the_tower_challenge(built):
    _, _, script, labels, _, _ = built
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    work_set = s32(gf_hash('WorkSet'))
    clears = [x.address for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[i - 1].args == [tower.ACTIVE] and ins[i - 2].args == [0]]
    assert any(labels[factory.CLEANUP] < a < labels[factory.CLEANUP] + 0x20 for a in clears)
    assert any(labels[factory.LOST] <= a < labels[factory.LOST] + 0x10 for a in clears)
    routes = [x.address for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[i - 1].args == [fp.WORK_ROUTE] and ins[i - 2].args == [0]]
    create = s32(gf_hash('BattleInstWorkCreate'))
    at = next(x.address for x in ins if x.op == OP['SYSREQ_N'] and names[x.args[0]] == create
              and labels['L14f4'] <= x.address)
    assert any(at < a < at + 0x20 for a in routes)


def battle_points_run(built, streak, route=2):
    _, _, script, labels, _, _ = built
    log = []
    stubs = natives({
        'WorkGet': lambda vm, a: route if a[0] == fp.WORK_ROUTE else 0,
        'GetMyWinCount': lambda vm, a: streak,
        'GetWinCount': lambda vm, a: 99,
    })
    calls = {labels['L30']: lambda vm, a: log.append(('bp', a[0]))}
    for name in ('Lfc', 'L2c8', 'L634', 'L5d4', 'L618'):
        calls[labels[name]] = lambda vm, a: 0
    stubs[s32(gf_hash('WordSetNumber'))] = lambda vm, a: log.append(('number', a[1]))
    VM(script, stubs, calls).run(labels[factory.BATTLE_POINTS], 0, 0, 0)
    return log


@pytest.mark.parametrize('streak, bp', [(7, 1), (14, 2), (98, 14), (105, 15), (112, 15), (700, 15)])
def test_tower_battle_points_at_the_end_of_a_round(built, streak, bp):
    assert bp == fd.FRONTIER_BP['tower'][min(streak // 7, 30) - 1]
    assert battle_points_run(built, streak) == [('bp', bp), ('number', bp)]


@pytest.mark.parametrize('streak', [1, 6, 8, 13])
def test_no_tower_battle_points_inside_a_round(built, streak):
    assert battle_points_run(built, streak) == []


@pytest.mark.parametrize('route', [0, 1])
def test_maison_battle_points_without_the_tower_route(built, route):
    assert battle_points_run(built, 7, route=route) == [('bp', 2), ('number', 2)]   # GetWinCount 99 > 10: 2 BP
