"""Battle Pike v1 (frontier/pike.py, frontier/asm/pike.s): zone script, room routine and the HP/status hooks."""
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
import pike  # noqa: E402
import tower  # noqa: E402
from formats import garc_entries, zo_build  # noqa: E402
from pawn import OP, Script, decode, gf_hash, s32  # noqa: E402
from pawn_vm import VM  # noqa: E402


def natives(table):
    return {s32(gf_hash(name)): fn for name, fn in table.items()}


@pytest.fixture(scope='module')
def zone():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    files, retail = overlay.maison_retail(overlay.ZONES.read_bytes())
    program = pike.pike_program(retail)
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
    program = factory.shared_program(script5, retail, cells, levels, dome.shared_cases(levels) + pike.shared_cases())
    labels = program.layout()
    script = program.build_script(f'L{script5.main:x}')
    assert Script.parse(script.build(pad=False)).build(pad=False) == script.build(pad=False)
    return script, labels


# --- constants -----------------------------------------------------------------------------------------------------

def test_pike_works_are_distinct_free_and_outside_the_cleared_block():
    works = [*fp.PIKE_HP, *fp.PIKE_ST, *(w for pair in fp.PIKE_PP for w in pair),
             pike.WORK_RNG, fp.PIKE_WILD, pike.STREAK, pike.ACTIVE, pike.RECORD]
    others = [fp.WORK_IV, *fp.WORK_SETS, *fp.WORK_RIVAL, fp.WORK_ROUTE, *dome.WORKS, factory.WORK_RNG,
              *(w for f, s in fp.STREAK_ROUTES.values() if f != 'pike' for w in (s, s + 1, s + 2))]
    assert len(set(works)) == len(works) and not set(works) & set(others)
    assert not any(0x4010 <= w <= 0x401F for w in works)
    assert pike.ROUTE == 6 and pike.ACTIVE == fp.ACTIVE_WORK['pike'] == 16478
    assert pike.ROOMS == 14 and sum(pike.STATUS_ODDS) == 100


def test_pike_global_case_is_in_the_row():
    assert fp.GLOBAL_ROW_BEFORE[0] < pike.GLOBAL_ROOM <= fp.GLOBAL_ROW_BEFORE[1]
    assert pike.GLOBAL_ROOM not in (factory.GLOBAL_DRAFT, factory.GLOBAL_SWAP, dome.GLOBAL_ENTRY, dome.GLOBAL_ROUND,
                                    dome.GLOBAL_WON)


@pytest.mark.parametrize('lang', [2, 7])
def test_pike_text_lines(lang):
    out = pike.lines(lang)
    assert len(out) == pike.LINE_END - pike.LINE_BASE == 43 and pike.LINE_BASE == dome.LINE_WON + 1
    assert out[0].count('[VAR 0203 1,0]') == 1
    assert all(len(line.split('\n')) <= 2 for line in out)


# --- zone script --------------------------------------------------------------------------------------------------

def test_pike_script_round_trips_and_fits(zone):
    files, retail, script, _ = zone
    raw = pike.zone_script(retail)
    assert raw == script.build() and Script.parse(raw).build() == raw
    assert len(zo_build([*files[:2], raw, *files[3:]])) <= 17248     # the largest zone container measured to load


def test_tower_and_palace_scripts_are_unchanged_by_the_stages_table():
    """tower.STAGES only applies to the Pike: the Tower keeps 7 battles a round."""
    assert tower.STAGES == {'pike': 14} and fd.STAGES_PER_ROUND == 7


def rooms_run(zone, works, results):
    _, _, script, labels = zone
    log, results = [], list(results)
    stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                     'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                     'GlobalCall': lambda vm, a: log.append(('global', a[0])),
                     'GlobalGetChildParam': lambda vm, a: results.pop(0),
                     'SetRank': lambda vm, a: log.append(('rank', a[0]))})
    VM(script, stubs, {}).run(labels['pike_rooms'])
    return log


def test_a_new_challenge_gets_a_fresh_team_and_plays_until_a_battle(zone):
    works = {fp.WORK_ROUTE: 6, **{w: 7 for w in (*fp.PIKE_HP, *fp.PIKE_ST)}}
    log = rooms_run(zone, works, [pike.ROOM_DONE, pike.ROOM_DONE, pike.ROOM_BATTLE])
    assert log == [('global', pike.GLOBAL_ROOM)] * 3
    assert all(works[w] == fp.PIKE_FULL for w in fp.PIKE_HP) and all(works[w] == 0 for w in fp.PIKE_ST)
    assert works[pike.STREAK] == 2 and works[pike.RECORD] == 2


def test_a_resumed_challenge_keeps_hp_status_and_record(zone):
    works = {fp.WORK_ROUTE: 6, pike.STREAK: 5, pike.RECORD: 30, fp.PIKE_HP[1]: 12, fp.PIKE_ST[2]: 3}
    log = rooms_run(zone, works, [pike.ROOM_DONE, pike.ROOM_HARD])
    assert log == [('global', pike.GLOBAL_ROOM)] * 2 + [('rank', 1)]
    assert works[fp.PIKE_HP[1]] == 12 and works[fp.PIKE_ST[2]] == 3
    assert works[pike.STREAK] == 6 and works[pike.RECORD] == 30


@pytest.mark.parametrize('route', [0, 2, 5])
def test_no_rooms_without_the_pike_route(zone, route):
    works = {fp.WORK_ROUTE: route}
    assert rooms_run(zone, works, []) == [] and works == {fp.WORK_ROUTE: route}


def test_rooms_run_before_the_rival_and_rank_is_reset_after_start_battle(zone):
    _, _, script, labels = zone
    ins = decode(script.code)
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    calls = [k for k, x in enumerate(ins) if x.op == OP['CALL'] and x.address + x.args[0] == labels['pike_rooms']]
    assert len(calls) == 1
    k = calls[0]
    assert names[ins[k - 2].args[0]] == s32(gf_hash('AcmdListClear'))
    assert labels['L1e1c'] < ins[k].address < labels['L1edc']
    after = [k for k, x in enumerate(ins) if x.op == OP['CALL'] and x.address + x.args[0] == labels['pike_after_start']]
    assert len(after) == 1 and names[ins[after[0] - 2].args[0]] == s32(gf_hash('StartBattle'))
    for route, rank in ((6, [0]), (2, [])):
        log = []
        stubs = natives({'WorkGet': lambda vm, a: route, 'SetRank': lambda vm, a: log.append(a[0])})
        VM(script, stubs, {}).run(labels['pike_after_start'])
        assert log == rank


def battle_points_run(zone, streak, route=6):
    _, _, script, labels = zone
    log = []
    stubs = natives({
        'WorkGet': lambda vm, a: route if a[0] == fp.WORK_ROUTE else 0,
        'GetMyWinCount': lambda vm, a: streak,
        'GetWinCount': lambda vm, a: 99,
        'WordSetNumber': lambda vm, a: log.append(('number', a[1])),
    })
    calls = {labels['L30']: lambda vm, a: log.append(('bp', a[0]))}
    for name in ('Lfc', 'L2c8', 'L634', 'L5d4', 'L618'):
        calls[labels[name]] = lambda vm, a: 0
    VM(script, stubs, calls).run(labels[factory.BATTLE_POINTS], 0, 0, 0)
    return log


@pytest.mark.parametrize('streak', [14, 28, 70, 140, 420, 1400])
def test_pike_battle_points_after_each_fourteenth_room(zone, streak):
    bp = fd.FRONTIER_BP['pike'][min(streak // 14, 30) - 1]
    assert battle_points_run(zone, streak) == [('bp', bp), ('number', bp)]


@pytest.mark.parametrize('streak', [1, 7, 13, 15, 21, 27])
def test_no_pike_battle_points_inside_a_round(zone, streak):
    assert battle_points_run(zone, streak) == []


def test_lost_and_cleanup_clear_the_pike_challenge(zone):
    _, _, script, labels = zone
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    work_set = s32(gf_hash('WorkSet'))
    clears = [x.address for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[i - 1].args == [pike.ACTIVE] and ins[i - 2].args == [0]]
    assert any(labels[factory.CLEANUP] < a < labels[factory.CLEANUP] + 0x20 for a in clears)
    assert any(labels[factory.LOST] <= a < labels[factory.LOST] + 0x10 for a in clears)


@pytest.mark.parametrize('other', [f for f in fp.ACTIVE_WORK if f != 'pike'])
def test_pike_refuses_while_another_facility_is_in_progress(zone, other):
    """factory.busy_check covers every patch.ACTIVE_WORK (the other receptions check the Pike's the same way)."""
    _, _, script, labels = zone
    log = []
    stubs = natives({'WorkGet': lambda vm, a: 1 if a[0] == fp.ACTIVE_WORK[other] else 0,
                     'WorkSet': lambda vm, a: log.append(('set', a[0], a[1]))})
    calls = {labels[f'L{factory.MSG:x}']: lambda vm, a: log.append(('msg', a[0])),
             labels[f'L{factory.MSG_WAIT:x}']: lambda vm, a: 0, labels[f'L{factory.MSG_CLOSE:x}']: lambda vm, a: 0}
    assert VM(script, stubs, calls).run(labels['pike_reception']) == 1
    assert log == [('msg', factory.LINE_BUSY)]


# --- shared script 5: the room ------------------------------------------------------------------------------------

def helpers(labels):
    return {name: labels[f'z{name}_{address:x}'] for name, address in factory.HELPERS.items()}


def room_run(shared, streak, door, team=None, seconds=1234567, rng=0, answers=None, traits=None):
    """pike_room with the door menu answering `door` (an int, or 'hint' / 'other' relative to the hinted door)."""
    return _room_run(shared, streak, door, team, seconds, rng, answers, traits)


def _room_run(shared, streak, door, team=None, seconds=1234567, rng=0, answers=None, traits=None, extra=None):
    script, labels = shared
    works = {**(extra or {}), pike.STREAK: streak, pike.WORK_RNG: rng}
    for k, (hp, st) in enumerate(team or [(fp.PIKE_FULL, 0)] * 3):
        works[fp.PIKE_HP[k]], works[fp.PIKE_ST[k]] = hp, st
    log, state, answers = [], {'menu': None, 'hint': None}, list(answers or [])

    def msg(vm, a):
        line = a[0]
        log.append(('msg', line))
        if pike.LINE_HINT <= line < pike.LINE_HINT + 12:
            state['hint'] = divmod(line - pike.LINE_HINT, 3)
        return 0

    def run_menu(vm, a):
        log.append(('menu', state['menu']))
        if answers:
            return answers.pop(0)
        cat, hinted = state['hint']
        return hinted if door == 'hint' else (hinted + 1) % 3 if door == 'other' else door

    stubs = natives({
        'PokePartyGetParam': lambda vm, a: (traits or [(0, 0, 0)] * 3)[a[0] - pike.SELECTED_SLOT][
            {6: 0, 7: 1, 22: 2}[a[1]]],
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        '_GetRealTimeToSecond': lambda vm, a: seconds,
        'ListMenuAdd': lambda vm, a: state['menu'].append((a[0], a[1])),
        'WordSetNumber': lambda vm, a: log.append(('number', a[0], a[1])),
        'GlobalSetParentParam': lambda vm, a: log.append(('result', a[0], a[1])),
    })
    h = helpers(labels)
    calls = {h['msg']: msg, h['msg_wait']: lambda vm, a: 0, h['msg_close']: lambda vm, a: 0,
             h['menu_init']: lambda vm, a: state.__setitem__('menu', []), h['menu_run']: run_menu}
    VM(script, stubs, calls).run(labels['pike_room'])
    return works, log, state['hint']


def room_type(log):
    """The room type the chosen door led to, from its messages."""
    msgs = [x[1] for x in log if x[0] == 'msg']
    for line, kind in ((pike.LINE_SINGLE, pike.SINGLE), (pike.LINE_HARD, pike.HARD), (pike.LINE_NPC, pike.NPC),
                       (pike.LINE_HEAL_FULL, pike.HEAL_FULL), (pike.LINE_STATUS_INTRO, pike.STATUS),
                       (pike.LINE_WILD, pike.WILD)):
        if line in msgs:
            return kind
    if any(pike.LINE_HEALED <= m < pike.LINE_HEALED + 3 for m in msgs):
        return pike.HEAL_PART
    raise AssertionError(f'no room message in {msgs}')


RESULT = {pike.SINGLE: pike.ROOM_BATTLE, pike.HARD: pike.ROOM_HARD, pike.WILD: pike.ROOM_BATTLE}


def test_room_number_and_doors_menu(shared):
    works, log, hint = room_run(shared, streak=17, door=0)
    assert ('number', 1, 4) in log and log[1] == ('msg', pike.LINE_ROOM)   # room 17 % 14 + 1
    menus = [x[1] for x in log if x[0] == 'menu']
    assert menus == [[(pike.LINE_DOOR + d, d) for d in range(3)]]
    assert log[-1] == ('result', 0, RESULT.get(room_type(log), pike.ROOM_DONE))


@pytest.mark.parametrize('streak', [13, 27, 41])
def test_the_last_room_of_a_round_is_a_battle(shared, streak):
    _, log, _ = room_run(shared, streak, door=0)
    assert ('msg', pike.LINE_LAST) in log and not any(x[0] == 'menu' for x in log)
    assert log[-1] == ('result', 0, pike.ROOM_BATTLE)


def test_hinted_door_is_of_its_category_and_the_others_are_not(shared):
    seen_cat, seen_type = set(), {}
    for seed in range(300):
        for door in ('hint', 'other'):
            works, log, (cat, hinted) = room_run(shared, streak=seed % 13, door=door, seconds=seed * 7919, rng=seed)
            kind = room_type(log)
            assert (pike.CATEGORY[kind] == cat) == (door == 'hint')
            seen_cat.add(cat)
            seen_type[kind] = seen_type.get(kind, 0) + 1
    assert seen_cat == {0, 1, 2, 3} and set(seen_type) == set(range(pike.TYPES))


def test_b_asks_for_a_door_again(shared):
    _, log, _ = room_run(shared, streak=3, door=1, answers=[65535])
    assert sum(1 for x in log if x[0] == 'menu') == 2


def test_no_status_room_without_a_healthy_pokemon(shared):
    team = [(0, 0), (30, 1), (fp.PIKE_FULL, 2)]
    for seed in range(200):
        for door in ('hint', 'other'):
            _, log, _ = room_run(shared, streak=5, door=door, team=team, seconds=seed * 31, rng=seed)
            assert room_type(log) != pike.STATUS


def find_room(shared, kind, streak, team=None, limit=400):
    for seed in range(limit):
        for door in ('hint', 'other'):
            works, log, hint = room_run(shared, streak, door, team=team, seconds=seed * 7919, rng=seed)
            if room_type(log) == kind:
                yield works, log
    return


def test_full_heal_restores_everyone(shared):
    team = [(0, 0), (12, 5), (fp.PIKE_FULL, 3)]
    works, log = next(find_room(shared, pike.HEAL_FULL, 2, team))
    assert all(works[w] == fp.PIKE_FULL for w in fp.PIKE_HP) and all(works[w] == 0 for w in fp.PIKE_ST)
    assert log[-1] == ('result', 0, pike.ROOM_DONE)


def test_partial_heal_restores_one_or_two(shared):
    team = [(0, 0), (12, 5), (40, 3)]
    counts = set()
    for works, log in find_room(shared, pike.HEAL_PART, 2, team):
        healed = [k for k in range(3) if works[fp.PIKE_HP[k]] == fp.PIKE_FULL]
        assert sorted(m[1] - pike.LINE_HEALED for m in log if m[0] == 'msg'
                      and pike.LINE_HEALED <= m[1] < pike.LINE_HEALED + 3) == healed
        assert all(works[fp.PIKE_ST[k]] == 0 for k in healed)
        assert all((works[fp.PIKE_HP[k]], works[fp.PIKE_ST[k]]) == team[k] for k in range(3) if k not in healed)
        counts.add(len(healed))
        assert log[-1] == ('result', 0, pike.ROOM_DONE)
    assert counts == {1, 2}


@pytest.mark.parametrize('streak, targets', [(0, 1), (3, 1), (4, 2), (8, 2), (9, 3), (12, 3), (17, 1), (23, 3)])
def test_status_room_affects_one_two_or_three_by_room(shared, streak, targets):
    statuses = set()
    for works, log in find_room(shared, pike.STATUS, streak, limit=150):
        hit = [k for k in range(3) if works[fp.PIKE_ST[k]]]
        assert len(hit) == targets and len({works[fp.PIKE_ST[k]] for k in hit}) == 1
        statuses.add(works[fp.PIKE_ST[hit[0]]])
        lines = [m[1] - pike.LINE_STATUS for m in log if m[0] == 'msg' and m[1] >= pike.LINE_STATUS]
        assert sorted(line // 5 for line in lines) == hit
        assert all(pike.STATUS_VALUE[pike.STATUSES[line % 5]] == works[fp.PIKE_ST[hit[0]]] for line in lines)
        assert all(works[w] == fp.PIKE_FULL for w in fp.PIKE_HP)
    assert statuses <= set(pike.STATUS_VALUE.values()) and len(statuses) >= 3


def test_status_room_skips_fainted_and_already_affected(shared):
    team = [(0, 0), (20, 4), (fp.PIKE_FULL, 0)]
    for works, log in find_room(shared, pike.STATUS, 12, team, limit=150):
        assert works[fp.PIKE_ST[0]] == 0 and works[fp.PIKE_ST[1]] == 4 and works[fp.PIKE_ST[2]] != 0


@pytest.mark.parametrize('streak, third', [(0, 0), (280, 0), (281, 1), (560, 1), (561, 2), (840, 2), (841, 3),
                                           (5000, 3)])
def test_wild_room_sets_one_of_three_wild_sets_by_streak(shared, streak, third):
    picks = set()
    for works, log in find_room(shared, pike.WILD, streak, limit=200):
        value = works[fp.PIKE_WILD]
        assert value in (fp.PIKE_WILD_FIRST, fp.PIKE_WILD_FIRST + 1, fp.PIKE_WILD_FAR + third)
        assert value == pike.wild_set(streak, value - fp.PIKE_WILD_FIRST if value < fp.PIKE_WILD_FAR else 2)
        assert log[-1] == ('result', 0, pike.ROOM_BATTLE)
        picks.add(value)
    assert len(picks) == 3


def test_every_other_room_clears_the_wild_set(shared):
    seen = set()
    for seed in range(200):
        for door in ('hint', 'other'):
            works, log, _ = _room_run(shared, seed % 14, door, seconds=seed * 7919, rng=seed,
                                      extra={fp.PIKE_WILD: fp.PIKE_WILD_FAR + 1})
            kind = room_type(log) if ('msg', pike.LINE_LAST) not in log else 'last'
            seen.add(kind)
            if kind != pike.WILD:
                assert works[fp.PIKE_WILD] == 0
    assert seen >= {'last', *range(pike.TYPES)}


def test_wild_sets_are_emeralds_and_written_to_empty_entries():
    sets = [fd.parse_set(raw) for raw in pike.wild_sets()]
    assert [s['species'] for s in sets] == [336, 350, 356, 101, 286, 202]
    assert all(s['evs'] == s['item'] == s['form'] == 0 for s in sets)
    if not overlay.ROMFS.exists():
        pytest.skip('Local baseline required')
    data = overlay.maison_sets()
    entries = garc_entries(data)
    maison = fd.load()
    assert len(entries) == len(maison['maisonpkN']) == 999
    trainers = [fd.parse_trainer(t) for t in maison['maisontrN']]
    assert max(max(t['sets']) for t in trainers) < fp.PIKE_WILD_FIRST
    for k, (_, _, offset, length) in enumerate(entries):
        raw = data[offset:offset + length]
        if fp.PIKE_WILD_FIRST <= k < fp.PIKE_WILD_FIRST + 6:
            assert raw == pike.wild_sets()[k - fp.PIKE_WILD_FIRST]
        else:
            assert raw == maison['maisonpkN'][k]


def test_generator_state_is_saved(shared):
    works, _, _ = room_run(shared, streak=3, door=0, rng=5)
    assert works[pike.WORK_RNG] != 5


@pytest.fixture(scope='module')
def status_seeds(shared):
    seeds = {}
    for seed in range(150):
        for door in ('hint', 'other'):
            works, log, _ = room_run(shared, 10, door, seconds=seed*7919, rng=seed)
            if room_type(log) == pike.STATUS:
                status = works[fp.PIKE_ST[0]]
                seeds.setdefault(status, (seed, door))
        if len(seeds) == 5:
            break
    assert set(seeds) == set(pike.STATUS_VALUE.values())
    return seeds


# Explicit expectations, independent of the implementation's immunity tables.
@pytest.mark.parametrize('status,type_id,ability', [
    ('toxic', 3, 0), ('toxic', 8, 0), ('toxic', 0, 17),
    ('freeze', 14, 0), ('freeze', 0, 40),
    ('paralysis', 4, 0), ('paralysis', 12, 0), ('paralysis', 0, 7),
    ('sleep', 0, 15), ('sleep', 0, 72), ('burn', 9, 0), ('burn', 0, 41)])
@pytest.mark.parametrize('secondary', [False, True])
def test_status_respects_current_types_and_actual_ability(shared, status_seeds, status, type_id, ability, secondary):
    seed, door = status_seeds[pike.STATUS_VALUE[status]]
    immune = (0, type_id, ability) if secondary else (type_id, 0, ability)
    works, log, _ = room_run(shared, 10, door, seconds=seed*7919, rng=seed,
                             traits=[immune, (0, 0, 0), immune])
    assert [works[w] for w in fp.PIKE_ST] == [0, pike.STATUS_VALUE[status], 0]
    assert log.count(('msg', pike.LINE_IMMUNE)) == 2
    assert log[-1] == ('result', 0, pike.ROOM_DONE)


# ORAS type numbers: Emerald's Fire 10 / Electric 13 / Ice 15 are Water / Psychic / Dragon here and protect nothing.
@pytest.mark.parametrize('status,type_id', [('burn', 10), ('paralysis', 13), ('freeze', 15), ('sleep', 9),
                                            ('toxic', 9)])
def test_status_is_not_blocked_by_other_types(shared, status_seeds, status, type_id):
    seed, door = status_seeds[pike.STATUS_VALUE[status]]
    works, log, _ = room_run(shared, 10, door, seconds=seed*7919, rng=seed, traits=[(type_id, type_id, 0)] * 3)
    assert [works[w] for w in fp.PIKE_ST] == [pike.STATUS_VALUE[status]] * 3
    assert ('msg', pike.LINE_IMMUNE) not in log


def test_immune_target_counts_toward_room_limit(shared):
    for seed in range(200):
        for door in ('hint', 'other'):
            works, log, _ = room_run(shared, 0, door, seconds=seed*7919, rng=seed)
            if room_type(log) == pike.STATUS:
                value = next(works[w] for w in fp.PIKE_ST if works[w])
                immune = {5: (8, 0, 0), 3: (14, 0, 0), 1: (12, 0, 0),
                          2: (0, 0, 15), 4: (9, 0, 0)}[value]
                works, log, _ = room_run(shared, 0, door, seconds=seed*7919, rng=seed, traits=[immune]*3)
                assert log.count(('msg', pike.LINE_IMMUNE)) == 1
                assert [works[w] for w in fp.PIKE_ST] == [0, 0, 0]
                return
    pytest.fail('No status room found')


# --- code.bin hooks (Unicorn) -------------------------------------------------------------------------------------

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE  # noqa: E402
from unicorn import arm_const as A  # noqa: E402

WORK, PARTY, STACK, MEMBERS = 0x08000000, 0x08001000, 0x09000000, 0x0B000000
CTX, GAMEDATA, SAVE = 0x0C000000, 0x0C000100, 0x0D000000
REGS = {name: getattr(A, f'UC_ARM_REG_{name.upper()}') for name in
        ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'sb', 'sl', 'fp', 'ip', 'sp', 'lr', 'pc')}
RETURN = 0xDEAD0000


@pytest.fixture(scope='module')
def code():
    if not fp.REPOLISHED.exists() or not shutil.which('arm-none-eabi-as'):
        pytest.skip('Local baseline and arm-none-eabi binutils required')
    return fp.build()[0]


def work_address(number):
    return SAVE + 0x13144 + 2 * (number - 0x4000)


def machine(code, works, members):
    """members: [(hp, max hp, status)]; member k is a PokemonParam at MEMBERS + 0x100k whose core (+0xc) is
    MEMBERS + 0x100k + 0x80, with the stubbed accessors reading and writing a fake block: hp +0, max +4, status +8."""
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x100000, (len(code) + 0xFFF) & ~0xFFF)
    uc.mem_write(0x100000, code)
    for base in (WORK, STACK - 0x10000, CTX, MEMBERS, RETURN):
        uc.mem_map(base, 0x10000)
    uc.mem_map(SAVE, 0x20000)
    uc.mem_write(WORK + 0xB78, struct.pack('<I', CTX))
    uc.mem_write(CTX + 0x1C, struct.pack('<I', GAMEDATA))
    uc.mem_write(GAMEDATA, struct.pack('<I', SAVE))
    for number, value in works.items():
        uc.mem_write(work_address(number), struct.pack('<H', value))
    pointers = [MEMBERS + 0x100 * k for k in range(len(members))]
    uc.mem_write(PARTY, struct.pack('<6I', *(pointers + [0] * (6 - len(pointers)))) + bytes([len(members)]))
    uc.mem_write(WORK + 0x66C, struct.pack('<I', PARTY))
    for p, (hp, top, st) in zip(pointers, members):
        uc.mem_write(p + 0xC, struct.pack('<I', p + 0x80))
        uc.mem_write(p + 0x80, struct.pack('<3I', hp, top, st))
        uc.mem_write(p + 0x90, bytes([20, 15, 10, 5]))  # fake PP storage
    uc.mem_write(WORK + 0x73C, b'\x01')
    return uc


def block(uc, k):
    return struct.unpack('<3I', uc.mem_read(MEMBERS + 0x100 * k + 0x80, 12))


def stub_accessors(uc, calls):
    f = fp.FUNCTIONS
    offsets = {f['GET_HP']: 0, f['GET_MAX_HP']: 4, f['GET_SICK']: 8}
    setters = {f['SET_HP']: 0, f['SET_SICK']: 8}

    def hook(uc, address, size, _):
        r0, r1 = uc.reg_read(REGS['r0']), uc.reg_read(REGS['r1'])
        if address in offsets:
            calls.append(('get', address, r0))
            uc.reg_write(REGS['r0'], struct.unpack('<I', uc.mem_read(r0 + offsets[address], 4))[0])
        elif address in setters:
            calls.append(('set', address, r0, r1))
            uc.mem_write(r0 + setters[address], struct.pack('<I', r1))
        elif address == f['BUILD_PARTY']:
            calls.append(('build', r0, uc.reg_read(REGS['r3'])))
        elif address == f['PARTY_PREPARE']:
            calls.append(('heal', r0))
            for k in range(uc.mem_read(r0+0x18, 1)[0]):
                mon, = struct.unpack('<I', uc.mem_read(r0+4*k, 4))
                core, = struct.unpack('<I', uc.mem_read(mon+0xc, 4))
                uc.mem_write(core, bytes(uc.mem_read(core+4, 4)))
                uc.mem_write(core+8, bytes(4))
        elif address == f['GET_PP']:
            uc.reg_write(REGS['r0'], uc.mem_read(r0 + 0x10 + r1, 1)[0])
        elif address == f['SET_PP']:
            uc.mem_write(r0 + 0x10 + r1, bytes([uc.reg_read(REGS['r2'])]))
        else:
            return
        uc.reg_write(REGS['pc'], uc.reg_read(REGS['lr']))

    uc.hook_add(UC_HOOK_CODE, hook)


def run_build(code, route, saved, members):
    works = {fp.WORK_ROUTE: route}
    for k, (hp, st) in enumerate(saved):
        works[fp.PIKE_HP[k]], works[fp.PIKE_ST[k]] = hp, st
    uc = machine(code, works, members)
    calls = []
    stub_accessors(uc, calls)
    for name, value in {'r0': WORK, 'r1': 0, 'r2': WORK + 0x2C, 'r3': PARTY, 'r4': 0x44, 'r5': 0x55, 'r6': 0x66,
                        'r7': 0x77, 'r8': 0x88, 'sb': 0x99, 'sl': 0xAA, 'fp': 0xBB, 'sp': STACK - 0x100,
                        'lr': RETURN}.items():
        uc.reg_write(REGS[name], value)
    # the patched call site: bl pike_build
    uc.emu_start(fp.BUILD_SITE, fp.BUILD_SITE + 4, count=20000)
    for name, value in {'r4': 0x44, 'r5': 0x55, 'r6': 0x66, 'r7': 0x77, 'r8': 0x88, 'sb': 0x99, 'sl': 0xAA,
                        'fp': 0xBB, 'sp': STACK - 0x100}.items():
        assert uc.reg_read(REGS[name]) == value, name
    return uc, calls


def test_h1_sets_the_saved_hp_and_status_on_the_pike_route(code):
    saved = [(fp.PIKE_FULL, 0), (30, 4), (500, 2)]
    uc, calls = run_build(code, 6, saved, [(150, 150, 0), (120, 120, 0), (100, 100, 0)])
    assert calls[0] == ('build', WORK, PARTY)
    assert block(uc, 0) == (150, 150, 0)            # 0xFFFF: left full
    assert block(uc, 1) == (30, 120, 4)
    assert block(uc, 2) == (100, 100, 2)            # capped to the max HP
    sets = [c for c in calls if c[0] == 'set']
    assert len(sets) == 5


def test_h1_fainted_stays_fainted(code):
    uc, _ = run_build(code, 6, [(0, 0)] * 3, [(80, 80, 0)] * 3)
    assert [block(uc, k)[0] for k in range(3)] == [0, 0, 0]


@pytest.mark.parametrize('route', [0, 1, 2, 5])
def test_h1_only_builds_on_other_routes(code, route):
    uc, calls = run_build(code, route, [(10, 3)] * 3, [(80, 80, 0)] * 3)
    assert calls == [('build', WORK, PARTY)] and block(uc, 0) == (80, 80, 0)


def run_iswin(code, route, members, won=1, party=PARTY):
    uc = machine(code, {fp.WORK_ROUTE: route}, members)
    uc.mem_write(WORK + 0x73C, bytes([won]))
    uc.mem_write(WORK + 0x66C, struct.pack('<I', party))
    calls = []
    stub_accessors(uc, calls)
    for name, value in {'r0': WORK, 'r4': 0x44, 'r5': 0x55, 'r6': 0x66, 'r7': 0x77, 'r8': 0x88, 'sb': 0x99,
                        'sl': 0xAA, 'fp': 0xBB, 'sp': STACK - 0x100, 'lr': RETURN}.items():
        uc.reg_write(REGS[name], value)
    uc.emu_start(fp.ISWIN, RETURN, count=20000)
    for name, value in {'r4': 0x44, 'r5': 0x55, 'r6': 0x66, 'r7': 0x77, 'r8': 0x88, 'sb': 0x99, 'sl': 0xAA,
                        'fp': 0xBB, 'sp': STACK - 0x100}.items():
        assert uc.reg_read(REGS[name]) == value, name
    saved = [struct.unpack('<H', uc.mem_read(work_address(w), 2))[0] for w in (*fp.PIKE_HP, *fp.PIKE_ST)]
    return uc.reg_read(REGS['r0']), saved, calls


@pytest.mark.parametrize('won, result', [(1, 1), (0, 0), (2, 0)])
def test_h2_copies_hp_and_status_back_and_returns_iswin(code, won, result):
    r0, saved, _ = run_iswin(code, 6, [(0, 90, 0), (45, 120, 1), (100, 100, 5)], won=won)
    assert r0 == result and saved == [0, 45, 100, 0, 1, 5]


@pytest.mark.parametrize('route', [0, 1, 2, 5])
def test_h2_is_iswin_on_other_routes(code, route):
    r0, saved, calls = run_iswin(code, route, [(1, 9, 1)] * 3)
    assert r0 == 1 and saved == [0] * 6 and calls == []


def test_h2_without_a_battle_party(code):
    r0, saved, calls = run_iswin(code, 6, [(1, 9, 1)] * 3, party=0)
    assert r0 == 1 and saved == [0] * 6 and calls == []


@pytest.mark.parametrize('route', range(8))
def test_pp_survive_two_battles_only_in_pike(code, route):
    """IsWin captures all four PP; a rebuilt/healed party restores them, including zero PP."""
    uc = machine(code, {fp.WORK_ROUTE: route}, [(80, 80, 0)] * 3)
    spent = [bytes([0, 14, 8, 1]), bytes([11, 0, 7, 4]), bytes([19, 9, 0, 3])]
    for k, pp in enumerate(spent):
        uc.mem_write(MEMBERS + 0x100 * k + 0x90, pp)
    stub_accessors(uc, [])
    def run(address, stop, regs):
        for name, value in {'sp': STACK - 0x100, 'lr': RETURN, **regs}.items():
            uc.reg_write(REGS[name], value)
        uc.emu_start(address, stop, count=20000)
    run(fp.ISWIN, RETURN, {'r0': WORK})
    for k, pp in enumerate(spent):
        pair = [struct.unpack('<H', uc.mem_read(work_address(group[k]), 2))[0] for group in fp.PIKE_PP]
        assert struct.pack('<2H', *pair) == (pp if route == pike.ROUTE else b'\x00' * 4)
        uc.mem_write(MEMBERS + 0x100 * k + 0x90, bytes([20, 15, 10, 5]))
    run(fp.BUILD_SITE, fp.BUILD_SITE + 4, {'r0': WORK, 'r3': PARTY})
    for k, pp in enumerate(spent):
        assert bytes(uc.mem_read(MEMBERS + 0x100 * k + 0x90, 4)) == (
            pp if route == pike.ROUTE else bytes([20, 15, 10, 5]))


@pytest.mark.parametrize('saved, expected', [(0xffff, [20, 15, 10, 5]), (0xfefe, [20, 15, 10, 5]),
                                            (0, [0, 0, 0, 0]), (0x0102, [2, 1, 2, 1])])
def test_pp_restore_full_sentinel_and_cap_to_new_moves(code, saved, expected):
    works = {fp.WORK_ROUTE: pike.ROUTE, **{w: saved for pair in fp.PIKE_PP for w in pair}}
    uc = machine(code, works, [(80, 80, 0)] * 3)
    stub_accessors(uc, [])
    for name, value in {'sp': STACK - 0x100, 'lr': RETURN, 'r0': WORK, 'r3': PARTY}.items():
        uc.reg_write(REGS[name], value)
    uc.emu_start(fp.BUILD_SITE, fp.BUILD_SITE + 4, count=20000)
    for k in range(3):
        assert list(uc.mem_read(MEMBERS + 0x100 * k + 0x90, 4)) == expected


@pytest.mark.parametrize('shuffle', range(32))
def test_pp_retail_accessors_preserve_encryption_checksum_and_other_fields(code, shuffle):
    """Execute the actual getter/setter, including the game's crypto, for every block order."""
    from save_fixture import encode_pk, decode_pk, PKSIZE
    uc = machine(code, {}, [])
    core, pk, battle = MEMBERS, MEMBERS + 0x100, MEMBERS + 0x300
    raw = bytearray(PKSIZE)
    struct.pack_into('<I', raw, 0, (shuffle << 13) | 0x10000001)
    raw[0x62:0x66] = bytes([20, 15, 10, 5])
    encoded = encode_pk(raw)
    uc.mem_write(pk, bytes(encoded[:0xe8]))
    uc.mem_write(battle, bytes(encoded[0xe8:]))
    uc.mem_write(core, struct.pack('<3I', 0, battle, pk) + b'\x01\x00')
    def run(name, slot, value=0):
        for reg, v in {'r0': core, 'r1': slot, 'r2': value, 'sp': STACK - 0x100, 'lr': RETURN}.items():
            uc.reg_write(REGS[reg], v)
        uc.emu_start(fp.FUNCTIONS[name], RETURN, count=100000)
        return uc.reg_read(REGS['r0'])
    for slot, pp in enumerate([20, 15, 10, 5]):
        assert run('GET_PP', slot) == pp
        run('SET_PP', slot, slot)
    final = decode_pk(bytes(uc.mem_read(pk, 0xe8)) + bytes(uc.mem_read(battle, 0x1c)))
    original = decode_pk(encoded)
    assert final[0x62:0x66] == bytes(range(4))
    final[6:8] = original[6:8]
    final[0x62:0x66] = original[0x62:0x66]
    assert final == original


@pytest.fixture(scope='module')
def battle_module():
    if not (fp.MOD_ROMFS / fp.BATTLE_CRO).exists():
        pytest.skip('Local v0.5 mod required')
    return fp.battle_cro()


def test_battle_copy_back_changes_only_gate_and_validates_hashes(battle_module):
    import hashlib
    from build_patch import cro_hashes
    original = (fp.MOD_ROMFS / fp.BATTLE_CRO).read_bytes()
    changed = battle_module[fp.BATTLE_CRO]
    assert len(changed) == len(original)
    assert changed[:0x80] == b''.join(cro_hashes(changed))
    assert all(i < 0x80 or fp.COPY_BACK <= i < fp.COPY_BACK + 12
               or any(site <= i < site + 16 for site in [*fp.ae.SITES, *fp.pe.SITES])
               for i, (a, b) in enumerate(zip(original, changed)) if a != b)
    crr = battle_module[fp.CRR]
    offset, count = struct.unpack_from('<II', crr, 0x350)
    hashes = [crr[offset + 32*i:offset + 32*(i+1)] for i in range(count)]
    assert hashes == sorted(hashes)
    assert hashes.count(hashlib.sha256(changed[:0x80]).digest()) == 1
    assert hashlib.sha256(original[:0x80]).digest() not in hashes


@pytest.mark.parametrize('competitor', [0, 1, 2, 3, 255, 0xffffffff])
def test_battle_copy_back_gate_preserves_other_competitor_types(battle_module, competitor):
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
    from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_PC
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x10000, 0x10000)
    # Use file offsets as addresses: only relative instructions in this gate.
    uc.mem_write(fp.COPY_BACK, battle_module[fp.BATTLE_CRO][fp.COPY_BACK:fp.COPY_BACK + 12])
    uc.reg_write(UC_ARM_REG_R1, competitor)
    uc.emu_start(fp.COPY_BACK, 0x20000, count=3)
    assert uc.reg_read(UC_ARM_REG_PC) == (fp.COPY_BACK + 12 if competitor <= 2 else 0x1580c)


def test_battle_copy_back_rejects_wrong_input(tmp_path):
    if not (fp.MOD_ROMFS / fp.BATTLE_CRO).exists():
        pytest.skip('Local v0.5 mod required')
    original = bytearray((fp.MOD_ROMFS / fp.BATTLE_CRO).read_bytes())
    original[-1] ^= 1
    (tmp_path / fp.BATTLE_CRO).write_bytes(original)
    with pytest.raises(SystemExit, match='not the v0.5 one'):
        fp.battle_cro(tmp_path)


def test_field_bridge_changes_only_guarded_instructions_and_updates_crr(battle_module):
    import hashlib
    from build_patch import cro_hashes
    from cro import Cro
    from analyze_assets import CRO
    original = (fp.MOD_ROMFS / fp.FIELD_CRO).read_bytes()
    changed = battle_module[fp.FIELD_CRO]
    assert len(original) == len(changed)
    assert changed[:0x80] == b''.join(cro_hashes(changed))
    assert all(i < 0x80 or fp.PIKE_PARAM_SITE <= i < fp.PIKE_PARAM_SITE+16
               for i, (a, b) in enumerate(zip(original, changed)) if a != b)
    assert not any(fp.PIKE_PARAM_SITE <= t < fp.PIKE_PARAM_SITE+16 for t, _, _ in Cro(original).relocs)
    imports = CRO(fp.MOD_ROMFS / fp.FIELD_CRO).static_imports(CRO(overlay.ROMFS / 'static.crs'))
    assert not any(fp.PIKE_PARAM_SITE <= item['offset'] < fp.PIKE_PARAM_SITE+16 for item in imports)
    crr = battle_module[fp.CRR]
    off, count = struct.unpack_from('<II', crr, 0x350)
    hashes = [crr[off+32*i:off+32*(i+1)] for i in range(count)]
    assert hashes.count(hashlib.sha256(changed[:0x80]).digest()) == 1
    assert hashlib.sha256(original[:0x80]).digest() not in hashes


@pytest.mark.parametrize('route', range(8))
@pytest.mark.parametrize('boxed', [False, True])
@pytest.mark.parametrize('slot', [0, 2, 5, 6, 255, 256, 257, 258, 259, 65535])
def test_virtual_selected_slots_and_retail_slots(code, battle_module, route, boxed, slot):
    """Execute actual CRO bridge and code stub, including retail party-count accessor.

    Nontrivial selection 5/0/3 verifies it is selected position, not raw party slot.
    """
    base, box = 0x01000000, PARTY+0x100
    uc = machine(code, {fp.WORK_ROUTE: route}, [(90, 90, 0)] * 6)
    uc.mem_map(base, 0x100000)
    uc.mem_write(base+fp.PIKE_PARAM_SITE,
                 battle_module[fp.FIELD_CRO][fp.PIKE_PARAM_SITE:fp.PIKE_PARAM_SITE+16])
    uc.mem_write(CTX+0x64, struct.pack('<I', WORK))
    uc.mem_write(WORK+0x2C, struct.pack('<4I', boxed, 5, 0, 3))
    uc.mem_write(WORK+0xB84, struct.pack('<I', box))
    uc.mem_write(box+0x18, b'\x06')
    regs = {'r3': 0x33, 'r4': 0x44, 'r5': CTX, 'r6': slot, 'r7': 22, 'r8': PARTY,
            'sb': 0x99, 'sl': 0xaa, 'fp': 0xbb, 'sp': STACK-0x100}
    for name, value in regs.items(): uc.reg_write(REGS[name], value)
    mapped = [5, 0, 3][slot-256] if route == 6 and 256 <= slot <= 258 else slot
    valid = mapped < 6
    resume = base + (0x4E654 if valid else 0x4EAAC)
    uc.emu_start(base+fp.PIKE_PARAM_SITE, resume, count=100)
    assert uc.reg_read(REGS['pc']) == resume
    assert uc.reg_read(REGS['r6']) == mapped
    assert uc.reg_read(REGS['r8']) == (box if boxed and route == 6 and 256 <= slot <= 258 else PARTY)
    for name in ('r3', 'r4', 'r5', 'r7', 'sb', 'sl', 'fp', 'sp'):
        assert uc.reg_read(REGS[name]) == regs[name], name


# --- wild rooms: rival count, set and level (Unicorn, patched code.bin) ---------------------------------------------

KEEP = {'r4': 0x44, 'r5': WORK, 'r7': 0, 'r8': 0x88, 'sb': 0x99, 'sl': 0xAA, 'fp': WORK, 'sp': STACK - 0x100}


def run_site(code, site, works, regs):
    uc = machine(code, works, [])
    for name, value in {**KEEP, 'lr': RETURN, **regs}.items():
        uc.reg_write(REGS[name], value)
    uc.emu_start(site, site + 4, count=2000)
    return {name: uc.reg_read(REGS[name]) for name in REGS}


@pytest.mark.parametrize('route, wild, count', [(6, 0, 3), (6, 219, 1), (6, 217, 1), (5, 0, 2), (5, 219, 2),
                                                (0, 219, 3), (2, 219, 3), (1, 219, 3), (7, 219, 3)])
def test_rival_count_is_one_only_in_a_pike_wild_room(code, route, wild, count):
    regs = run_site(code, fp.COUNT_SITE, {fp.WORK_ROUTE: route, fp.PIKE_WILD: wild}, {'r0': 0x1234})
    assert regs['r6'] == count and regs['r0'] == 0x1234
    assert all(regs[k] == v for k, v in KEEP.items() if k != 'r4')


@pytest.mark.parametrize('route, wild, expected', [(6, 0, (77, 0xB8)), (6, 219, (219, 0xB6)),
                                                   (6, 222, (222, 0xB6)), (0, 219, (77, 0xB8)),
                                                   (2, 219, (77, 0xB8))])
def test_rival_set_is_the_wild_one_only_in_a_pike_wild_room(code, route, wild, expected):
    lst = WORK + 0x800                       # the trainer's list: ldrh r4, [r0, #4] reads the drawn set
    uc_works = {fp.WORK_ROUTE: route, fp.PIKE_WILD: wild}
    uc = machine(code, uc_works, [])
    uc.mem_write(lst + 4, struct.pack('<H', 77))
    for name, value in {**KEEP, 'r0': lst, 'r2': 0xB8, 'lr': RETURN}.items():
        uc.reg_write(REGS[name], value)
    uc.emu_start(fp.RIVAL_SITE, fp.RIVAL_SITE + 4, count=2000)
    assert (uc.reg_read(REGS['r4']), uc.reg_read(REGS['r2'])) == expected
    assert uc.reg_read(REGS['sp']) == KEEP['sp'] and uc.reg_read(REGS['r7']) == 0


@pytest.mark.parametrize('route, wild, level', [(6, 0, 50), (6, 217, 46), (6, 218, 46), (6, 219, 45), (6, 222, 45),
                                                (5, 219, 50), (0, 217, 50), (1, 219, 50)])
def test_rival_level_is_emeralds_only_in_a_pike_wild_room(code, route, wild, level):
    regs = run_site(code, fp.LEVEL_SITE, {fp.WORK_ROUTE: route, fp.PIKE_WILD: wild}, {'r3': 0x3333})
    assert regs['r1'] == level and regs['r3'] == 0x3333
    assert all(regs[k] == v for k, v in KEEP.items())


def test_wild_levels_match_emerald():
    deltas = {336: 4, 350: 4, 356: 5, 101: 5, 286: 5, 202: 5}      # sLvl50_Mons levelDelta
    for k, (species, _) in enumerate(pike.WILD_SETS):
        index = fp.PIKE_WILD_FIRST + k
        assert (45 if index >= fp.PIKE_WILD_FAR else 46) == 50 - deltas[species]
