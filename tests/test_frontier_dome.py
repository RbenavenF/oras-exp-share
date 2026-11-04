"""Battle Dome v1 (frontier/dome.py, frontier/asm/dome.s): the zone script and the shared script 5 cases, run in
scripts/pawn_vm.py with stubbed natives and retail routines, and the code.bin hooks run in Unicorn. Checks the
generated logic, not the game (Azahar: reports/frontier.md §26)."""
from pathlib import Path
import shutil
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import data as fd  # noqa: E402
import dome  # noqa: E402
import factory  # noqa: E402
import overlay  # noqa: E402
import patch as fp  # noqa: E402
from formats import garc_entries, zo_build  # noqa: E402
from pawn import OP, Op, Program, Script, decode, gf_hash, s32  # noqa: E402
from pawn_vm import VM  # noqa: E402

MSG = {f'L{a:x}' for a in (factory.MSG, factory.MSG_WAIT, factory.MSG_CLOSE)}


def natives(table):
    return {s32(gf_hash(name)): fn for name, fn in table.items()}


@pytest.fixture(scope='module')
def zone():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    files, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    program = dome.dome_program(retail)
    return files, retail, program.build_script(f'L{retail.main:x}'), program.layout()


@pytest.fixture(scope='module')
def shared():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    sets, table, levels, cells = overlay.rentals()
    _, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    data = (overlay.ROMFS / overlay.SHARED).read_bytes()
    _, _, offset, length = garc_entries(data)[factory.SHARED_SCRIPT]
    script5 = Script.parse(data[offset:offset + length])
    program = factory.shared_program(script5, retail, cells, levels, dome.shared_cases(levels))
    labels = program.layout()
    script = program.build_script(f'L{script5.main:x}')
    assert Script.parse(script.build(pad=False)).build(pad=False) == script.build(pad=False)
    return sets, table, levels, cells, script, labels


# --- zone script --------------------------------------------------------------------------------------------------

def test_dome_script_round_trips_and_fits(zone):
    files, retail, script, _ = zone
    raw = dome.zone_script(retail)
    assert raw == script.build() and Script.parse(raw).build() == raw
    assert len(zo_build([*files[:2], raw, *files[3:]])) <= 17248     # the largest zone container measured to load


def test_dome_works_are_distinct_and_outside_the_cleared_block():
    works = list(dome.WORKS) + [dome.STREAK, dome.ACTIVE, dome.RECORD, fp.WORK_ROUTE]
    assert len(set(works)) == len(works)
    others = {fp.WORK_IV, *fp.WORK_SETS, *fp.WORK_RIVAL, factory.WORK_RNG, factory.WORK_STREAK,
              *(s + k for _, s in fp.STREAK_ROUTES.values() for k in range(3))}
    assert not set(dome.WORKS) & others
    assert not any(0x4010 <= w <= 0x401F for w in works)              # entering a hall clears that block (§25)
    assert (dome.STREAK, dome.ACTIVE) == (16473, fp.ACTIVE_WORK['dome'])


def reception(zone, active=None, entered=1, declined=False, streak_after=0, dome_active=0, dome_streak=0):
    _, _, script, labels = zone
    works = {fp.ACTIVE_WORK[f]: v for f, v in (active or {}).items()}
    works.update({dome.ACTIVE: dome_active, dome.STREAK: dome_streak})
    log = []

    def challenge(vm, args):
        log.append(('challenge', args, dict(works)))
        return 1 if declined else 0

    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'SetRank': lambda vm, a: log.append(('rank', a)),
        'GlobalCall': lambda vm, a: log.append(('global', a[0], dict(works))),
        'GlobalGetChildParam': lambda vm, a: entered,
        'GetMyWinCount': lambda vm, a: log.append(('wins', dict(works))) or streak_after,
    })
    calls = {labels[factory.CHALLENGE]: challenge, labels[f'L{factory.MSG:x}']: lambda vm, a: log.append(('msg', a))}
    calls.update({labels[m]: (lambda vm, a: 0) for m in MSG - {f'L{factory.MSG:x}'}})
    result = VM(script, stubs, calls).run(labels['dome_reception'])
    return result, works, log


def test_a_new_dome_challenge(zone):
    result, works, log = reception(zone, dome_streak=9)
    assert result == 0 and ('rank', [0]) in log
    entry = next(e for e in log if e[0] == 'global')
    assert entry[1] == dome.GLOBAL_ENTRY and entry[2][fp.WORK_ROUTE] == dome.ROUTE == 5 and entry[2][dome.STREAK] == 0
    _, args, seen = next(e for e in log if e[0] == 'challenge')
    assert args == [0, 0, 0] and seen[dome.ACTIVE] == 1 and seen[fp.WORK_ROUTE] == 5
    assert (seen[0x800C], seen[0x800D], seen[0x800E]) == (1, 0, 0)
    assert works[fp.WORK_ROUTE] == 0 and works[dome.ACTIVE] == 0      # lost: no challenge in progress
    assert all(e[1][fp.WORK_ROUTE] == 5 for e in log if e[0] == 'wins')


def test_a_paused_dome_challenge_stays_active_and_resumes_with_a_new_entry(zone):
    _, works, _ = reception(zone, streak_after=3)
    assert works[dome.ACTIVE] == 1 and works[fp.WORK_ROUTE] == 0
    result, works, log = reception(zone, dome_active=1, dome_streak=6, streak_after=7)
    assert [e[1] for e in log if e[0] == 'global'] == [dome.GLOBAL_ENTRY]
    seen = next(e for e in log if e[0] == 'challenge')[2]
    assert result == 0 and seen[dome.STREAK] == 6 and works[dome.STREAK] == 6 and works[dome.ACTIVE] == 1


@pytest.mark.parametrize('active, streak', [(0, 0), (1, 5)])
def test_a_cancelled_entry_changes_nothing(zone, active, streak):
    result, works, log = reception(zone, entered=0, dome_active=active, dome_streak=streak)
    assert result == 1 and not [e for e in log if e[0] == 'challenge']
    assert works[dome.ACTIVE] == active and works[fp.WORK_ROUTE] == 0 and works[dome.STREAK] == streak


@pytest.mark.parametrize('active, streak, kept', [(0, 0, 0), (1, 4, 1)])
def test_declining_goes_back_to_the_menu(zone, active, streak, kept):
    result, works, _ = reception(zone, declined=True, dome_active=active, dome_streak=streak, streak_after=streak)
    assert result == 1 and works[dome.ACTIVE] == kept and works[fp.WORK_ROUTE] == 0


@pytest.mark.parametrize('other', [f for f in fp.ACTIVE_WORK if f != 'dome'])
def test_dome_refuses_while_another_facility_is_in_progress(zone, other):
    result, works, log = reception(zone, active={other: 21 if other == 'factory' else 1}, dome_streak=5)
    assert result == 1 and not [e for e in log if e[0] in ('challenge', 'rank', 'global')]
    assert ('msg', [factory.LINE_BUSY, 1, 0, 256, 0]) in log
    assert works[dome.STREAK] == 5 and fp.WORK_ROUTE not in works


@pytest.mark.parametrize('reception_of', ['factory', 'tower'])
def test_the_factory_and_the_tower_refuse_while_the_dome_is_in_progress(reception_of):
    """Their busy_check reads every patch.ACTIVE_WORK, the Dome's included."""
    import tower
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    _, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    program = overlay.maison_program(retail) if reception_of == 'factory' else tower.tower_program(retail)
    labels, script = program.layout(), program.build_script(f'L{retail.main:x}')
    works, log = {dome.ACTIVE: 1}, []
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1])})
    calls = {labels[f'L{factory.MSG:x}']: lambda vm, a: log.append(('msg', a))}
    calls.update({labels[m]: (lambda vm, a: 0) for m in MSG - {f'L{factory.MSG:x}'}})
    assert VM(script, stubs, calls).run(labels[f'{reception_of}_reception']) == 1
    assert log == [('msg', [factory.LINE_BUSY, 1, 0, 256, 0])] and works == {dome.ACTIVE: 1}


@pytest.mark.parametrize('route, skipped', [(5, True), (0, False), (2, False), (1, False)])
def test_party_selection_is_skipped_only_on_the_dome_route(zone, route, skipped):
    _, _, script, labels = zone
    works, log = {fp.WORK_ROUTE: route}, []
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                     'BattleHouse_CallPartySelectApp': lambda vm, a: log.append(('app', a)) or 0})
    stubs.update({h: (lambda vm, a: 0) for _, h in script.natives if h not in stubs})
    try:
        result = VM(script, stubs, {}).run(labels[dome.PARTY_SELECT], 0, limit=2000)
    except Exception:            # the retail routine goes on to code the stubs do not model
        result = None
    if skipped:
        assert result == 1 and works[0x800C] == 1 and not log
    else:
        assert log and log[0][0] == 'app'


@pytest.mark.parametrize('route, called', [(5, True), (0, False), (2, False)])
def test_before_each_battle_the_round_is_played_only_on_the_dome_route(zone, route, called):
    _, _, script, labels = zone
    works, log = {fp.WORK_ROUTE: route}, []
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                     'GetMyWinCount': lambda vm, a: 6,
                     'GlobalCall': lambda vm, a: log.append(('global', a[0], works.get(dome.WORK_STREAK)))})
    VM(script, stubs, {}).run(labels['dome_before_battle'])
    assert log == ([('global', dome.GLOBAL_ROUND, 6)] if called else [])


def test_the_round_runs_right_before_start_battle(zone):
    _, _, script, labels = zone
    ins = decode(script.code)
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    at = next(k for k, x in enumerate(ins) if x.address == labels[dome.BEFORE_BATTLE])
    assert ins[at].op == OP['PUSH_P_C'] and ins[at + 1].op == OP['CALL']
    assert ins[at + 1].address + ins[at + 1].args[0] == labels['dome_before_battle']
    assert names[ins[at + 4].args[0]] == s32(gf_hash('StartBattle'))


def test_lost_and_cleanup_clear_the_dome_challenge(zone):
    _, _, script, labels = zone
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    work_set = s32(gf_hash('WorkSet'))
    clears = [x.address for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[i - 1].args == [dome.ACTIVE] and ins[i - 2].args == [0]]
    assert any(labels[factory.CLEANUP] < a < labels[factory.CLEANUP] + 0x20 for a in clears)
    assert any(labels[factory.LOST] <= a < labels[factory.LOST] + 0x10 for a in clears)


def battle_points_run(zone, streak, route=5):
    _, _, script, labels = zone
    log = []
    stubs = natives({
        'WorkGet': lambda vm, a: route if a[0] == fp.WORK_ROUTE else 0,
        'GetMyWinCount': lambda vm, a: streak,
        'GetWinCount': lambda vm, a: 99,
        'GlobalCall': lambda vm, a: log.append(('global', a[0])),
        'WordSetNumber': lambda vm, a: log.append(('number', a[1])),
    })
    calls = {labels['L30']: lambda vm, a: log.append(('bp', a[0]))}
    for name in ('Lfc', 'L2c8', 'L634', 'L5d4', 'L618'):
        calls[labels[name]] = lambda vm, a: 0
    VM(script, stubs, calls).run(labels[factory.BATTLE_POINTS], 0, 0, 0)
    return log


@pytest.mark.parametrize('streak, bp', [(4, 1), (8, 1), (12, 2), (40, 5), (120, 15), (400, 15)])
def test_dome_battle_points_after_a_final(zone, streak, bp):
    assert bp == fd.FRONTIER_BP['dome'][min(streak // 4, 30) - 1]
    assert battle_points_run(zone, streak) == [('global', dome.GLOBAL_WON), ('bp', bp), ('number', bp)]


@pytest.mark.parametrize('streak', [1, 2, 3, 5, 7, 13])
def test_no_dome_battle_points_inside_a_tournament(zone, streak):
    assert battle_points_run(zone, streak) == []


@pytest.mark.parametrize('route', [0, 2])
def test_maison_battle_points_without_the_dome_route(zone, route):
    assert battle_points_run(zone, 4, route=route) == [('bp', 2), ('number', 2)]


# --- shared script 5 --------------------------------------------------------------------------------------------

def helpers(labels):
    return {name: labels[f'z{name}_{address:x}'] for name, address in factory.HELPERS.items()}


def entry_run(shared, picks, party):
    """dome_entry with CallPokeSelect answering `picks` in turn; party = [(species, item, egg)] per slot."""
    *_, script, labels = shared
    works, log, picks = {}, [], list(picks)

    def select(vm, a):
        log.append(('select', a))
        works[0x800C] = picks.pop(0)
        return 0

    def param(vm, a):
        species, item, egg = party[a[0]]
        return {dome.PARAM_SPECIES: species, dome.PARAM_ITEM: item, dome.PARAM_EGG: egg}[a[1]]

    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'CallPokeSelect': select,
        'PokePartyGetParam': param,
        'GlobalSetParentParam': lambda vm, a: log.append(('result', a)),
    })
    h = helpers(labels)
    calls = {h['msg']: lambda vm, a: log.append(('msg', a[0])), h['msg_wait']: lambda vm, a: 0,
             h['msg_close']: lambda vm, a: 0}
    VM(script, stubs, calls).run(labels['dome_entry'])
    return works, log, picks


PARTY = [(25, 0, 0), (6, 234, 0), (25, 1, 0), (9, 234, 0), (150, 0, 0), (0, 0, 1)]  # Pikachu, Charizard (Leftovers)…


def test_entry_writes_three_party_slots(shared):
    works, log, rest = entry_run(shared, [4, 1, 0], PARTY)
    assert [works[w] for w in dome.TEAM] == [4, 1, 0] and ('result', [0, 1]) in log and not rest
    assert [e[1] for e in log if e[0] == 'select'] == [list(dome.POKE_SELECT_ARGS)] * 3
    assert [e[1] for e in log if e[0] == 'msg'] == list(dome.LINE_ENTRY)


@pytest.mark.parametrize('picks, team, line', [
    ([5, 4, 1, 0], [4, 1, 0], dome.LINE_EGG),     # an egg
    ([0, 0, 1, 4], [0, 1, 4], dome.LINE_DUP),     # the same slot twice
    ([0, 2, 1, 4], [0, 1, 4], dome.LINE_DUP),     # Pikachu twice
    ([1, 3, 0, 4], [1, 0, 4], dome.LINE_DUP),     # Leftovers twice
])
def test_entry_refuses_eggs_and_repeats(shared, picks, team, line):
    works, log, rest = entry_run(shared, picks, PARTY)
    assert line in [e[1] for e in log if e[0] == 'msg'] and not rest
    assert [works[w] for w in dome.TEAM] == team and ('result', [0, 1]) in log


def test_two_pokemon_holding_nothing_are_fine(shared):
    works, log, _ = entry_run(shared, [0, 4, 1], PARTY)
    assert [works[w] for w in dome.TEAM] == [0, 4, 1] and dome.LINE_DUP not in [e[1] for e in log if e[0] == 'msg']


@pytest.mark.parametrize('picks', [[6], [0, 6], [1, 4, 6]])
def test_cancelling_the_entry(shared, picks):
    works, log, _ = entry_run(shared, picks, PARTY)
    assert ('result', [0, 0]) in log and not any(w in works for w in dome.TEAM)


def round_run(shared, streak, menu_answers, team=(4, 1, 0), seconds=1234567, rng=0):
    *_, script, labels = shared
    works = {dome.WORK_STREAK: streak, dome.WORK_RNG: rng, **dict(zip(dome.TEAM, team))}
    log, menus, state, answers = [], [], {'menu': None}, list(menu_answers)

    def run_menu(vm, a):
        menus.append(state['menu'])
        return answers.pop(0)

    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        '_GetRealTimeToSecond': lambda vm, a: seconds,
        'ListMenuAdd': lambda vm, a: state['menu'].append((a[0], a[1])),
        'WordSetTemotiMonsNickName': lambda vm, a: log.append(('nick', a)),
    })
    h = helpers(labels)
    calls = {h['msg']: lambda vm, a: log.append(('msg', a[0])), h['msg_wait']: lambda vm, a: 0,
             h['msg_close']: lambda vm, a: 0, h['menu_init']: lambda vm, a: state.__setitem__('menu', []),
             h['menu_run']: run_menu}
    VM(script, stubs, calls).run(labels['dome_round'])
    return works, log, menus, answers


def value_of(table, slot):
    rank, index = table[slot]
    return index | (fp.SUPER if rank == 'S' else 0)


@pytest.mark.parametrize('streak, level', [(0, 0), (3, 0), (4, 1), (11, 2), (12, 3), (28, 7), (400, 7)])
def test_round_draws_three_different_sets_of_the_level(shared, streak, level):
    sets, table, levels, *_ = shared
    works, log, menus, _ = round_run(shared, streak, [0, 2, 1])
    first, count = levels[level]
    values = {value_of(table, s): table[s] for s in range(first, first + count)}
    rival = [works[w] for w in dome.RIVAL]
    assert all(v in values for v in rival)
    drawn = [sets[values[v][0]][values[v][1]] for v in rival]
    assert len({s['species'] for s in drawn}) == 3 and len({s['item'] for s in drawn}) == 3
    assert ('msg', dome.LINE_ROUNDS[streak % 4]) in log
    assert [line for line, _ in menus[0]] == [factory.line_of(*values[v]) for v in rival]   # the preview


def test_round_sets_the_fighters_and_the_rivals_two(shared):
    works, log, menus, rest = round_run(shared, 5, [1, 2, 0], team=(4, 1, 0))
    assert not rest and [works[w] for w in fp.DOME_FIGHT] == [0, 4]        # entries 2 then 0 of the team (4, 1, 0)
    assert menus[1] == [(dome.LINE_NICK[k], k) for k in range(3)]
    assert menus[2] == [(dome.LINE_NICK[0], 0), (dome.LINE_NICK[1], 1)]     # without the first pick
    assert [e[1] for e in log if e[0] == 'nick'] == [[0, 4], [1, 1], [2, 0]]
    rival = [works[w] for w in dome.RIVAL]
    forced = [works[w] for w in fp.DOME_FORCED]
    assert len(set(forced)) == 2 and set(forced) <= set(rival)


def test_b_in_a_pick_goes_back_to_the_rivals_team(shared):
    works, log, menus, rest = round_run(shared, 0, [0, 65535, 0, 0, 65535, 0, 1, 0])
    assert not rest and len(menus) == 8 and [works[w] for w in fp.DOME_FIGHT] == [1, 4]
    assert [m[0][0] for m in menus].count(menus[0][0][0]) == 3      # the preview shown three times


def test_the_rivals_two_vary(shared):
    seen = set()
    for seconds in range(40):
        works, *_ = round_run(shared, 0, [0, 0, 1], seconds=seconds)
        rival = [works[w] for w in dome.RIVAL]
        seen.add(tuple(rival.index(works[w]) for w in fp.DOME_FORCED))
    assert seen == {(a, b) for a in range(3) for b in range(3) if a != b}


def test_the_shared_cases_are_in_the_global_row():
    values = [v for v, _, _ in dome.shared_cases([])]
    assert values == [9773, 9774, 9775] and fp.GLOBAL_ROW_BEFORE[:2] == (9770, 9779)
    assert not {factory.GLOBAL_DRAFT, factory.GLOBAL_SWAP} & set(values)


def test_dome_text_lines():
    for lang in (1, 7):
        lines = dome.lines(lang)
        assert len(lines) == dome.LINE_WON - dome.LINE_BASE + 1
        assert lines[dome.LINE_NICK[1] - dome.LINE_BASE] == '[VAR 0102 1]'
        assert all(len(part) <= 46 for line in lines for part in line.split('\n'))


# --- code.bin hooks (Unicorn) -------------------------------------------------------------------------------------

unicorn = pytest.importorskip('unicorn')
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE  # noqa: E402
from unicorn import arm_const as A  # noqa: E402

WORK, PARTY_NEW, STACK, HEAP = 0x08000000, 0x08001000, 0x09000000, 0x0A000000
CTX, GAMEDATA, PLAYER_PARTY, SAVE = 0x0C000000, 0x0C000100, 0x0C000200, 0x0D000000
REGS = {name: getattr(A, f'UC_ARM_REG_{name.upper()}') for name in
        ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'sb', 'sl', 'fp', 'ip', 'sp', 'lr', 'pc')}


@pytest.fixture(scope='module')
def code():
    if not fp.REPOLISHED.exists() or not shutil.which('arm-none-eabi-as'):
        pytest.skip('Local baseline and arm-none-eabi binutils required')
    return fp.build()[0]


def work_address(number):
    return SAVE + 0x13144 + 2 * (number - 0x4000)


def machine(code, works):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x100000, (len(code) + 0xFFF) & ~0xFFF)
    uc.mem_write(0x100000, code)
    for base in (WORK, STACK - 0x10000, HEAP, CTX):
        uc.mem_map(base, 0x10000)
    uc.mem_map(SAVE, 0x20000)
    uc.mem_write(WORK + 0xB78, struct.pack('<I', CTX))
    uc.mem_write(CTX + 0x1C, struct.pack('<I', GAMEDATA))
    uc.mem_write(GAMEDATA, struct.pack('<I', SAVE))
    uc.mem_write(GAMEDATA + 0x14, struct.pack('<I', PLAYER_PARTY))
    for number, value in works.items():
        uc.mem_write(work_address(number), struct.pack('<H', value))
    return uc


def run_party(code, route, selection=(3, 5, 1), count=3):
    uc = machine(code, {fp.WORK_ROUTE: route, fp.DOME_FIGHT[0]: 4, fp.DOME_FIGHT[1]: 2})
    uc.mem_write(WORK + 0x30, struct.pack('<6i', *selection, 0, 0, 0))
    uc.mem_write(WORK + 0x48, struct.pack('<I', count))
    regs = {'r4': WORK + 0x2C, 'r5': 0x55, 'r6': WORK, 'r7': 1, 'r8': 0x88, 'sb': PARTY_NEW, 'sl': 0xAA,
            'fp': 0xBB, 'sp': STACK - 0x100, 'lr': 0xDEAD0000}
    for name, value in regs.items():
        uc.reg_write(REGS[name], value)
    prepared = []

    def hook(uc, address, size, _):
        if address == fp.FUNCTIONS['PARTY_PREPARE']:
            prepared.append(uc.reg_read(REGS['r0']))
            uc.reg_write(REGS['pc'], uc.reg_read(REGS['lr']))

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(fp.SITE, 0x1E3DA0, count=5000)
    sel = struct.unpack('<6i', uc.mem_read(WORK + 0x30, 24))
    n = struct.unpack('<I', uc.mem_read(WORK + 0x48, 4))[0]
    for name, value in {'r4': WORK + 0x2C, 'r5': 0x55, 'r6': WORK, 'r7': 1, 'r8': PLAYER_PARTY, 'sb': PARTY_NEW,
                        'sl': 0xAA, 'fp': 0xBB, 'sp': STACK - 0x100}.items():
        assert uc.reg_read(REGS[name]) == value, name
    assert prepared == [PLAYER_PARTY]
    return sel, n


def test_dome_route_selects_its_two_fighters(code):
    sel, n = run_party(code, route=5)
    assert n == 2 and sel[:2] == (4, 2)


@pytest.mark.parametrize('route', [0, 1, 2, 6])
def test_other_routes_keep_the_selection(code, route):
    sel, n = run_party(code, route=route)
    assert n == 3 and sel[:3] == (3, 5, 1)


def run_rival(code, route, slot, forced=(fp.SUPER | 907, 120), iv=0, index=0x1A7):
    uc = machine(code, {fp.WORK_ROUTE: route, fp.DOME_FORCED[0]: forced[0], fp.DOME_FORCED[1]: forced[1],
                        fp.WORK_IV: iv, **{n: 0xBEEF for n in fp.WORK_RIVAL}})
    uc.mem_write(HEAP + 4, struct.pack('<H', index))
    regs = {'r0': HEAP, 'r1': 0x11, 'r2': 0xB6, 'r3': 0x33, 'r4': 0x44, 'r7': slot, 'fp': WORK,
            'sp': STACK - 0x100, 'lr': 0xDEAD0000}
    for name, value in regs.items():
        uc.reg_write(REGS[name], value)
    uc.emu_start(fp.RIVAL_SITE, fp.RIVAL_SITE + 4, count=100)
    assert uc.reg_read(REGS['pc']) == fp.RIVAL_SITE + 4
    for name, value in {'r3': 0x33, 'r7': slot, 'fp': WORK, 'sp': STACK - 0x100}.items():
        assert uc.reg_read(REGS[name]) == value, name
    rivals = [struct.unpack('<H', uc.mem_read(work_address(n), 2))[0] for n in fp.WORK_RIVAL]
    return uc.reg_read(REGS['r4']), uc.reg_read(REGS['r2']), rivals


@pytest.mark.parametrize('slot, index, archive', [(0, 907, 0xB8), (1, 120, 0xB6)])
def test_dome_route_forces_the_rivals_sets(code, slot, index, archive):
    assert run_rival(code, 5, slot) == (index, archive, [0xBEEF] * 3)


def test_dome_route_leaves_further_slots_alone(code):
    assert run_rival(code, 5, 2) == (0x1A7, 0xB6, [0xBEEF] * 3)


@pytest.mark.parametrize('route', [0, 1, 2])
def test_other_routes_draw_as_before(code, route):
    assert run_rival(code, route, 0) == (0x1A7, 0xB6, [0xBEEF] * 3)
    r4, r2, rivals = run_rival(code, route, 1, iv=21)                     # an active Factory still copies its rival
    assert (r4, r2) == (0x1A7, 0xB6) and rivals == [0xBEEF, 0x1A7, 0xBEEF]


@pytest.mark.parametrize('route, members', [(5, 2), (0, 3), (1, 3), (2, 3)])
def test_rival_party_size(code, route, members):
    uc = machine(code, {fp.WORK_ROUTE: route})
    for name, value in {'r5': WORK, 'r6': 0x66, 'sp': STACK - 0x100, 'lr': 0xDEAD0000}.items():
        uc.reg_write(REGS[name], value)
    uc.emu_start(fp.COUNT_SITE, 0x1E3568, count=100)
    assert uc.reg_read(REGS['pc']) == 0x1E3568 and uc.reg_read(REGS['r6']) == members
    assert uc.reg_read(REGS['r5']) == WORK and uc.reg_read(REGS['sp']) == STACK - 0x100
