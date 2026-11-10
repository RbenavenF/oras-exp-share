"""Battle Pyramid v1 (frontier/pyramid.py, frontier/asm/pyramid.s): lobby and floor scripts in the Pawn VM, the
shared say routine, the plan lines and the code.bin hooks in Unicorn. VM runs are not evidence of the game: that is
reports/frontier.md §30 (Azahar)."""
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
import island_build  # noqa: E402
import overlay  # noqa: E402
import patch as fp  # noqa: E402
import pike  # noqa: E402
import pyramid as py  # noqa: E402
from formats import garc_entries  # noqa: E402
from pawn import Script, gf_hash, s32  # noqa: E402
from pawn_vm import VM  # noqa: E402

YES, NO = py.YES, py.NO


def natives(table):
    return {s32(gf_hash(name)): fn for name, fn in table.items()}


@pytest.fixture(scope='module')
def retail():
    if not overlay.ZONES.exists():
        pytest.skip('Local baseline required')
    return overlay.maison_retail(overlay.ZONES.read_bytes())[1]


@pytest.fixture(scope='module')
def lobby(retail):
    p = py.lobby_program(retail)
    return p.build_script(f'L{retail.main:x}'), p.layout()


@pytest.fixture(scope='module')
def floor(retail):
    p = py.floor_program(retail)
    return p.build_script(f'L{retail.main:x}'), p.layout()


# --- constants -----------------------------------------------------------------------------------------------------

def test_pyramid_works_are_distinct_and_apart_from_the_others():
    works = [py.STREAK, py.ACTIVE, py.RECORD, py.WORK_BEATEN, py.WORK_MSG, py.WORK_ARG, *fp.PYRAMID_SEL,
             fp.PYRAMID_COUNT]
    others = [fp.WORK_IV, *fp.WORK_SETS, *fp.WORK_RIVAL, fp.WORK_ROUTE, *dome.WORKS, factory.WORK_RNG, pike.WORK_RNG,
              *fp.PIKE_HP, *fp.PIKE_ST, *fp.DOME_FIGHT, *fp.DOME_FORCED,
              *(w for f, s in fp.STREAK_ROUTES.values() if f != 'pyramid' for w in (s, s + 1, s + 2))]
    assert len(set(works)) == len(works) and not set(works) & set(others)
    assert not any(0x4010 <= w <= 0x401F for w in works)
    assert py.ROUTE == 7 and py.ACTIVE == fp.ACTIVE_WORK['pyramid'] == 16482


def test_pyramid_global_case_and_text_lines():
    assert fp.GLOBAL_ROW_BEFORE[0] < py.GLOBAL_SAY <= fp.GLOBAL_ROW_BEFORE[1]
    assert py.GLOBAL_SAY not in (factory.GLOBAL_DRAFT, factory.GLOBAL_SWAP, dome.GLOBAL_ENTRY, dome.GLOBAL_ROUND,
                                 dome.GLOBAL_WON, pike.GLOBAL_ROOM)
    assert py.LINE_BASE == pike.LINE_END and py.LINE_END - py.LINE_BASE == len(py.KEYS) < py.ASK
    for lang in (2, 7):
        out = py.lines(lang)
        assert len(out) == len(py.KEYS) and all(len(line.split('\n')) <= 3 for line in out)
        assert sum('[VAR 0203 1,0]' in line for line in out) == 3      # resume, floor, won


def test_plan_lines_give_each_floor_three_trainers_an_attendant_and_the_lobby_exit():
    lines = py.plan_lines()
    for zone in py.FLOORS:
        assert f'zone.{zone}.clearNpcs=1' in lines and f'zone.{zone}.clearTriggers=1' in lines
        assert f'text.{zone}=619' in lines
        assert f'zone.{zone}.loadBudget={island_build.LOAD_BUDGET}' in lines
        assert all(f'zone.{zone}.warp.{k}={k},{py.LOBBY},0' in lines for k in range(3))
        assert island_build.CLONES[zone] == 77 and island_build.native_donors()[zone] == 517
        npcs = [l.split('=')[1].split(',') for l in lines if l.startswith(f'zone.{zone}.npc.')]
        assert [int(n[2]) for n in npcs] == [2, 3, 4, py.STAIRS_EVENT]
        assert len({(n[4], n[5]) for n in npcs}) == 4
    plan = island_build.plan('s').splitlines()
    assert f'plaza.door.{list(island_build.FACILITIES).index("Pyramid")}={py.LOBBY},0' in plan
    assert f'zone.{py.LOBBY}.warp.0=0,{island_build.ZONE_ISLAND},{island_build.door_warp("Pyramid")}' in plan


def test_scripts_round_trip_and_fit(retail):
    scripts = py.zone_scripts(retail)
    assert set(scripts) == {py.LOBBY, *py.FLOORS}
    for raw in scripts.values():
        assert Script.parse(raw).build() == raw and len(raw) < 17000


# --- lobby ----------------------------------------------------------------------------------------------------------

def run_lobby(lobby, works=None, answers=(YES,), mode=(1, 0, 7), selected=1, saved=0, count_after=3):
    script, labels = lobby
    works = dict(works or {})
    log, answers = [], list(answers)

    def gcall(vm, a):
        if a[0] == py.GLOBAL_SAY:
            log.append(('say', works[py.WORK_MSG] & 0xFF, works.get(py.WORK_ARG)))
        else:
            log.append(('global', a[0]))

    def child(vm, a):
        return answers.pop(0)

    def delete(vm, a):
        log.append(('delete',))
        if works.get(fp.WORK_ROUTE) == py.ROUTE and selected:
            works[fp.PYRAMID_COUNT] = count_after        # what pyramid_save does (Unicorn tests below)

    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'GlobalCall': gcall, 'GlobalGetChildParam': child,
        'FlagGet': lambda vm, a: 0,
        'BattleInstWorkCreate': lambda vm, a: log.append(('create',)),
        'BattleInstWorkDelete': delete,
        'BattleHouse_End': lambda vm, a: log.append(('end',)),
        'SetRank': lambda vm, a: log.append(('rank', a[0])),
        '_MapChangeCore': lambda vm, a: log.append(('map', *a)),
    })

    def app(vm, a):
        works.update(zip((factory.WORK_SELECT_RESULT, factory.WORK_SELECT_TYPE, factory.WORK_SELECT_X), mode))

    calls = {labels[n]: (lambda vm, a: 0) for n in (py.TALK_START, py.TALK_END, f'L{factory.MSG:x}',
                                                    f'L{factory.MSG_WAIT:x}', f'L{factory.MSG_CLOSE:x}')}
    calls[labels['L12a0']] = app
    calls[labels[py.PARTY_SELECT]] = lambda vm, a: (log.append(('select', a[0])), selected)[1]
    calls[labels[py.SAVE]] = lambda vm, a: (log.append(('save',)), saved)[1]
    VM(script, stubs, calls).run(labels['pyramid_reception'])
    return works, log


def maps(log):
    return [x[1:] for x in log if x[0] == 'map']


def test_new_challenge_selects_saves_and_goes_to_floor_1(lobby):
    works, log = run_lobby(lobby, {py.STREAK: 7, py.RECORD: 7})
    assert works[py.ACTIVE] == 1 and works[fp.WORK_ROUTE] == py.ROUTE and works[py.WORK_BEATEN] == 0
    assert works[py.STREAK] == 7                    # the streak goes on after a completed challenge
    assert ('select', 7) in log and ('rank', 0) in log and log.index(('delete',)) < log.index(('save',))
    assert maps(log) == [(py.FLOORS[0], *py.FLOOR_ARRIVAL, 0, 0, 1, 0)]


def test_declined_challenge_changes_nothing(lobby):
    works, log = run_lobby(lobby, answers=[NO])
    assert works == {py.WORK_MSG: py.MSG['enter'] | py.ASK}
    assert not any(x[0] in ('create', 'map') for x in log)


@pytest.mark.parametrize('mode,selected', [((0, 0, 7), 1), ((1, 1, 7), 1), ((1, 0, 7), 0)])
def test_cancelled_screens_release_the_work(lobby, mode, selected):
    works, log = run_lobby(lobby, mode=mode, selected=selected)
    assert works.get(py.ACTIVE, 0) == 0 and works[fp.WORK_ROUTE] == 0 and not maps(log)
    assert log[-2:] == [('end',), ('delete',)]


def test_battle_box_or_unsaved_selection_is_refused(lobby):
    works, log = run_lobby(lobby, count_after=0)
    assert works.get(py.ACTIVE, 0) == 0 and works[fp.WORK_ROUTE] == 0 and not maps(log)
    assert ('say', py.MSG['box'], None) in log


def test_not_saving_keeps_nothing(lobby):
    works, log = run_lobby(lobby, saved=1)
    assert works[py.ACTIVE] == 0 and works[fp.WORK_ROUTE] == 0 and not maps(log)


@pytest.mark.parametrize('floor_number', [1, 2, 7])
def test_resume_goes_back_to_the_saved_floor(lobby, floor_number):
    works, log = run_lobby(lobby, {py.ACTIVE: floor_number, fp.WORK_ROUTE: 0}, answers=[YES])
    assert works[fp.WORK_ROUTE] == py.ROUTE and ('say', py.MSG['resume'], floor_number) in log
    assert maps(log) == [(py.FLOORS[(floor_number - 1) % 2], *py.FLOOR_ARRIVAL, 0, 0, 1, 0)]
    assert not any(x[0] == 'create' for x in log)


def test_retire_ends_the_challenge(lobby):
    works, log = run_lobby(lobby, {py.ACTIVE: 3, py.STREAK: 9, fp.WORK_ROUTE: 7, py.WORK_BEATEN: 5}, answers=[NO, YES])
    assert (works[py.ACTIVE], works[fp.WORK_ROUTE], works[py.STREAK], works[py.WORK_BEATEN]) == (0, 0, 0, 0)
    assert not maps(log)


def test_resume_declined_twice_keeps_the_challenge(lobby):
    before = {py.ACTIVE: 3, py.STREAK: 9, fp.WORK_ROUTE: 0}
    works, log = run_lobby(lobby, before, answers=[NO, NO])
    assert works[py.ACTIVE] == 3 and works[py.STREAK] == 9 and not maps(log)


@pytest.mark.parametrize('other', [f for f in fp.ACTIVE_WORK if f != 'pyramid'])
def test_refused_while_another_facility_is_in_progress(lobby, other):
    before = {fp.ACTIVE_WORK[other]: 1}
    works, log = run_lobby(lobby, before)
    assert works == before and not any(x[0] in ('create', 'map', 'say') for x in log)


# --- floors ---------------------------------------------------------------------------------------------------------

def run_floor(floor, routine, works, win=1):
    script, labels = floor
    works = dict(works)
    log = []
    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
        'GlobalCall': lambda vm, a: log.append(('say', works[py.WORK_MSG] & 0xFF, works.get(py.WORK_ARG))),
        'BattleInstWorkCreate': lambda vm, a: log.append(('create',)),
        'BattleInstWorkDelete': lambda vm, a: log.append(('delete',)),
        'SetRank': lambda vm, a: log.append(('rank', a[0])),
        'SetTrainer': lambda vm, a: log.append(('trainer', a[0])),
        'StartBattle': lambda vm, a: log.append(('battle', *a)),
        'IsWin': lambda vm, a: win,
        '_MapChangeCore': lambda vm, a: log.append(('map', *a)),
    })
    calls = {labels[n]: (lambda vm, a: 0) for n in (py.TALK_START, py.TALK_END, *(c[0] for c in py.AFTER_BATTLE))}
    calls[labels[py.ADD_BP]] = lambda vm, a: log.append(('bp', a[0]))
    VM(script, stubs, calls).run(labels[routine])
    return works, log


@pytest.mark.parametrize('k', range(py.TRAINERS))
def test_trainer_battle_as_the_maison_and_marked_beaten(floor, k):
    works, log = run_floor(floor, f'pyramid_trainer{k}', {py.ACTIVE: 2, fp.WORK_ROUTE: 0, py.WORK_BEATEN: 0})
    assert works[py.WORK_BEATEN] == 1 << k and works[fp.WORK_ROUTE] == py.ROUTE
    assert [x for x in log if x[0] != 'say'] == [('create',), ('rank', 0), ('trainer', 0), ('battle', 0, 1),
                                                 ('delete',)]


def test_beaten_trainer_does_not_fight_again(floor):
    works, log = run_floor(floor, 'pyramid_trainer1', {py.ACTIVE: 2, py.WORK_BEATEN: 2})
    assert log == [('say', py.MSG['beaten'], None)] and works[py.WORK_BEATEN] == 2


def test_loss_ends_the_challenge_and_returns_to_the_lobby(floor):
    works, log = run_floor(floor, 'pyramid_trainer0', {py.ACTIVE: 5, py.STREAK: 30, py.RECORD: 30,
                                                       fp.WORK_ROUTE: 7, py.WORK_BEATEN: 2}, win=0)
    assert (works[py.ACTIVE], works[fp.WORK_ROUTE], works[py.STREAK], works[py.WORK_BEATEN]) == (0, 0, 0, 0)
    assert works[py.RECORD] == 30 and maps(log) == [(*py.LOBBY_RETURN, 0, 0, 1, 0)]


def test_attendant_refuses_until_the_floor_is_cleared(floor):
    works, log = run_floor(floor, 'pyramid_stairs', {py.ACTIVE: 3, py.STREAK: 2, py.WORK_BEATEN: 5})
    assert works[py.ACTIVE] == 3 and works[py.STREAK] == 2 and not maps(log)
    assert ('say', py.MSG['not_yet'], 3) in log


@pytest.mark.parametrize('floor_number', range(1, 7))
def test_cleared_floor_climbs_and_counts(floor, floor_number):
    works, log = run_floor(floor, 'pyramid_stairs', {py.ACTIVE: floor_number, py.STREAK: floor_number - 1,
                                                     py.RECORD: 3, py.WORK_BEATEN: 7})
    assert works[py.ACTIVE] == floor_number + 1 and works[py.STREAK] == floor_number
    assert works[py.RECORD] == max(3, floor_number) and works[py.WORK_BEATEN] == 0
    assert maps(log) == [(py.FLOORS[floor_number % 2], *py.FLOOR_ARRIVAL, 0, 0, 1, 0)]
    assert not any(x[0] == 'bp' for x in log)


@pytest.mark.parametrize('challenge', [1, 2, 3, 20, 21, 40])
def test_top_floor_gives_emerald_bp_and_returns(floor, challenge):
    works, log = run_floor(floor, 'pyramid_stairs', {py.ACTIVE: 7, py.STREAK: 7 * challenge - 1, py.RECORD: 0,
                                                     fp.WORK_ROUTE: 7, py.WORK_BEATEN: 7})
    bp = fd.FRONTIER_BP['pyramid'][min(challenge, len(fd.FRONTIER_BP['pyramid'])) - 1]
    assert ('bp', bp) in log and ('say', py.MSG['won'], bp) in log
    assert works[py.ACTIVE] == 0 and works[fp.WORK_ROUTE] == 0 and works[py.STREAK] == 7 * challenge
    assert works[py.RECORD] == 7 * challenge and maps(log) == [(*py.LOBBY_RETURN, 0, 0, 1, 0)]


# --- shared script 5 ------------------------------------------------------------------------------------------------

@pytest.fixture(scope='module')
def shared(retail):
    sets, table, levels, cells = overlay.rentals()
    data = (overlay.ROMFS / overlay.SHARED).read_bytes()
    _, _, offset, length = garc_entries(data)[factory.SHARED_SCRIPT]
    script5 = Script.parse(data[offset:offset + length])
    program = factory.shared_program(script5, retail, cells, levels,
                                     dome.shared_cases(levels) + pike.shared_cases() + py.shared_cases())
    return program.build_script(f'L{script5.main:x}'), program.layout()


@pytest.mark.parametrize('msg,answer,expected', [(py.MSG['floor'], None, NO), (py.MSG['enter'] | py.ASK, YES, YES),
                                                 (py.MSG['enter'] | py.ASK, NO, NO),
                                                 (py.MSG['enter'] | py.ASK, 0xFFFF, NO)])
def test_say_shows_the_line_and_answers(shared, msg, answer, expected):
    script, labels = shared
    log = []
    works = {py.WORK_MSG: msg, py.WORK_ARG: 4}
    stubs = natives({
        'WorkGet': lambda vm, a: works.get(a[0], 0),
        'WordSetNumber': lambda vm, a: log.append(('number', a[0], a[1])),
        'ListMenuAdd': lambda vm, a: log.append(('item', a[0], a[1])),
        'GlobalSetParentParam': lambda vm, a: log.append(('result', a[1])),
    })
    h = {name: labels[f'z{name}_{address:x}'] for name, address in factory.HELPERS.items()}
    calls = {h['msg']: lambda vm, a: log.append(('msg', a[0])), h['msg_wait']: lambda vm, a: 0,
             h['msg_close']: lambda vm, a: 0, h['menu_init']: lambda vm, a: 0, h['menu_run']: lambda vm, a: answer}
    VM(script, stubs, calls).run(labels['pyramid_say'])
    assert ('msg', py.LINE_BASE + (msg & 0xFF)) in log and ('number', 1, 4) in log
    assert (('item', py.LINE_BASE + py.MSG['yes'], YES) in log) == bool(msg & py.ASK)
    assert log[-1] == ('result', expected)


# --- code.bin hooks (Unicorn) -------------------------------------------------------------------------------------

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE  # noqa: E402
from unicorn import arm_const as A  # noqa: E402

WORK, PARTY_NEW, STACK, HOLDER = 0x08000000, 0x08001000, 0x09000000, 0x0A000000
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
    for base in (WORK, STACK - 0x10000, HOLDER, CTX):
        uc.mem_map(base, 0x10000)
    uc.mem_map(SAVE, 0x20000)
    uc.mem_write(WORK + 0xB78, struct.pack('<I', CTX))
    uc.mem_write(CTX + 0x1C, struct.pack('<I', GAMEDATA))
    uc.mem_write(GAMEDATA, struct.pack('<I', SAVE))
    uc.mem_write(GAMEDATA + 0x14, struct.pack('<I', PLAYER_PARTY))
    for number, value in works.items():
        uc.mem_write(work_address(number), struct.pack('<H', value))
    return uc


def read_work(uc, number):
    return struct.unpack('<H', uc.mem_read(work_address(number), 2))[0]


def run_party(code, route, saved=(4, 5, 3), selection=(1, 2, 0), count=3):
    works = {fp.WORK_ROUTE: route, **dict(zip(fp.PYRAMID_SEL, saved))}
    uc = machine(code, works)
    uc.mem_write(WORK + 0x30, struct.pack('<6i', *selection, 0, 0, 0))
    uc.mem_write(WORK + 0x48, struct.pack('<I', count))
    regs = {'r4': WORK + 0x2C, 'r5': 0x55, 'r6': WORK, 'r7': 1, 'r8': 0x88, 'sb': PARTY_NEW, 'sl': 0xAA,
            'fp': 0xBB, 'sp': STACK - 0x100, 'lr': 0xDEAD0000}
    for name, value in regs.items():
        uc.reg_write(REGS[name], value)

    def hook(uc, address, size, _):
        if address == fp.FUNCTIONS['PARTY_PREPARE']:
            uc.reg_write(REGS['pc'], uc.reg_read(REGS['lr']))

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(fp.SITE, 0x1E3DA0, count=5000)
    for name, value in {'r4': WORK + 0x2C, 'r5': 0x55, 'r6': WORK, 'r7': 1, 'r8': PLAYER_PARTY, 'sb': PARTY_NEW,
                        'sl': 0xAA, 'fp': 0xBB, 'sp': STACK - 0x100}.items():
        assert uc.reg_read(REGS[name]) == value, name
    sel = struct.unpack('<6i', uc.mem_read(WORK + 0x30, 24))
    return sel, struct.unpack('<I', uc.mem_read(WORK + 0x48, 4))[0]


def test_pyramid_party_takes_the_saved_selection(code):
    sel, n = run_party(code, route=py.ROUTE, count=0)
    assert n == 3 and sel[:3] == (4, 5, 3)


@pytest.mark.parametrize('route', [0, 1, 2, 6])
def test_pyramid_party_leaves_other_routes(code, route):
    sel, n = run_party(code, route=route)
    assert n == 3 and sel[:3] == (1, 2, 0)


def run_delete(code, route, selection=(4, 5, 3), count=3, box=0, work=WORK):
    uc = machine(code, {fp.WORK_ROUTE: route, **{n: 0xBEEF for n in (*fp.PYRAMID_SEL, fp.PYRAMID_COUNT)}})
    uc.mem_write(WORK + 0x2C, bytes([box]))
    uc.mem_write(WORK + 0x30, struct.pack('<6i', *selection, *[0] * (6 - len(selection))))
    uc.mem_write(WORK + 0x48, struct.pack('<I', count))
    uc.mem_write(HOLDER + 0x64, struct.pack('<I', work))
    getter = []

    def hook(uc, address, size, _):
        if address == fp.FUNCTIONS['WORK_DELETE_CALL']:
            getter.append(uc.reg_read(REGS['lr']))
            uc.reg_write(REGS['pc'], uc.reg_read(REGS['lr']))

    uc.hook_add(UC_HOOK_CODE, hook)
    regs = {'r0': HOLDER, 'r4': 0x44, 'r5': 0x55, 'r6': 0x66, 'sp': STACK - 0x100, 'lr': 0xDEAD0000}
    for name, value in regs.items():
        uc.reg_write(REGS[name], value)
    # BattleInstWorkDelete 0x1e5c48 up to the instruction after the patched call (0x1e5c58)
    uc.emu_start(fp.WORK_DELETE, fp.DELETE_SITE + 4, count=5000)
    assert getter == [fp.DELETE_SITE + 4]
    assert uc.reg_read(REGS['r4']) == work and uc.reg_read(REGS['r5']) == HOLDER
    return [read_work(uc, n) for n in fp.PYRAMID_SEL], read_work(uc, fp.PYRAMID_COUNT)


def test_pyramid_save_keeps_the_selection_on_its_route(code):
    assert run_delete(code, py.ROUTE) == ([4, 5, 3], 3)


@pytest.mark.parametrize('kwargs', [dict(route=0), dict(route=2), dict(route=py.ROUTE, count=2),
                                    dict(route=py.ROUTE, box=1), dict(route=py.ROUTE, selection=(4, 6, 3)),
                                    dict(route=py.ROUTE, selection=(-1, 1, 2)), dict(route=py.ROUTE, selection=(6, 1, 2)),
                                    dict(route=py.ROUTE, selection=(1, 2, 6)), dict(route=py.ROUTE, work=0)])
def test_pyramid_save_writes_nothing_otherwise(code, kwargs):
    assert run_delete(code, **kwargs) == ([0xBEEF] * 3, 0xBEEF)


def test_complete_floor_container_guards(retail):
    from formats import zo_build
    head = bytearray(56)
    struct.pack_into('<H', head, 6, 619)
    ent = bytearray(12 + 4 * 0x30 + 3 * 0x18)
    ent[4:9] = bytes([0, 4, 3, 0, 0])
    for k in range(3):
        struct.pack_into('<HH', ent, 12 + 4 * 0x30 + k * 0x18, 140, 0)
    raw = py.zone_scripts(retail)[141]
    files = [head, ent, raw, b'', b'']
    assert py.check_floor(zo_build(files)) <= py.ZO_LIMIT
    with pytest.raises(ValueError, match='exceeds'):
        py.check_floor(zo_build(files + [bytes(py.ZO_LIMIT)]))
    ent[4] = 1
    with pytest.raises(ValueError, match='props'):
        py.check_floor(zo_build(files))
    ent[4] = 0
    struct.pack_into('<H', ent, 12 + 4 * 0x30 + 2 * 0x18, 77)
    with pytest.raises(ValueError, match='exit'):
        py.check_floor(zo_build(files))
