"""Battle Arena stage A (frontier/arena.py): its zone script, run in scripts/pawn_vm.py with stubbed natives and
retail routines, and the mutual exclusion. Checks the generated logic, not the game (Azahar: reports/frontier.md
§29)."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import data as fd  # noqa: E402
import factory  # noqa: E402
import island_build  # noqa: E402
import overlay  # noqa: E402
import arena  # noqa: E402
import palace  # noqa: E402
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
    program = arena.arena_program(retail)
    labels = program.layout()
    script = program.build_script(f'L{retail.main:x}')
    return files, retail, script, labels


def test_arena_ids_are_the_assigned_ones():
    """frontier/REPARTO.md: route 4, streak 16465, challenge in progress 16466, record 16467, zone 457."""
    assert (arena.ROUTE, arena.STREAK, arena.ACTIVE, arena.RECORD) == (4, 16465, 16466, 16467)
    assert fp.ACTIVE_WORK['arena'] == arena.ACTIVE and arena.ZONE == island_build.ZONE_ARENA == 457
    assert island_build.CLONES[arena.ZONE] == island_build.DONOR_HALL and arena.ZONE in island_build.KEEP_TEXT
    assert island_build.DOORS['Arena'] == (arena.ZONE, 0)


def test_arena_script_round_trips_fits_and_is_the_overlays(built):
    files, retail, script, _ = built
    raw = arena.zone_script(retail)
    assert raw == script.build() and Script.parse(raw).build() == raw
    assert len(zo_build([*files[:2], raw, *files[3:]])) <= 17248     # the largest container measured to load (§11)
    assert overlay.facility_scripts()[arena.ZONE] == raw
    assert raw != tower.zone_script(retail) and raw != palace.zone_script(retail)


def test_arena_menu_is_the_maisons_and_party_selection_is_retail(built):
    _, retail, script, labels = built
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    add = s32(gf_hash('ListMenuAdd'))
    menu = [ins[i - 1].args[0] for i, x in enumerate(ins) if labels['L14f4'] <= x.address < labels['L1634']
            and x.op == OP['SYSREQ_N'] and names[x.args[0]] == add]
    assert menu == tower.RECEPTION_MENU

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
    assert routine(arena.arena_program(retail)) == routine(Program.from_script(retail))


def reception(built, active=None, declined=False, streak_after=0, own_active=0, own_streak=0, mode=(1, 0, 7)):
    """Runs arena_reception. `active`: {facility: value} of other facilities' ACTIVE_WORK."""
    _, _, script, labels = built
    works = {fp.ACTIVE_WORK[f]: v for f, v in (active or {}).items()}
    works.update({arena.ACTIVE: own_active, arena.STREAK: own_streak})
    log = []

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
        'GetMyWinCount': lambda vm, a: log.append(('wins', dict(works))) or streak_after,
    })
    calls = {labels[factory.CHALLENGE]: challenge, labels[f'L{factory.MSG:x}']: lambda vm, a: log.append(('msg', a)),
             labels[tower.MODE_APP]: app}
    calls.update({labels[m]: (lambda vm, a: 0) for m in MSG - {f'L{factory.MSG:x}'}})
    result = VM(script, stubs, calls).run(labels['arena_reception'])
    return result, works, log


def test_a_new_arena_challenge_uses_route_4(built):
    result, works, log = reception(built, own_streak=9)
    assert result == 0 and ('rank', [0]) in log
    assert ('msg', [tower.MSG_MODE, 1, 0, 256, 0]) in log                 # the mode screen, then the party screen
    _, args, seen = next(e for e in log if e[0] == 'challenge')
    assert args == [0, 0, 7]                                              # rank 0, Singles, work 0x800E
    assert seen[fp.WORK_ROUTE] == 4 and seen[arena.ACTIVE] == 1 and seen[arena.STREAK] == 0
    assert works[fp.WORK_ROUTE] == 0 and works[arena.ACTIVE] == 0       # lost: no challenge in progress
    assert all(e[1][fp.WORK_ROUTE] == 4 for e in log if e[0] == 'wins')
    assert all(w not in works for w in (tower.ACTIVE, tower.STREAK, palace.ACTIVE, palace.STREAK))  # others' works untouched


def test_a_paused_arena_challenge_stays_active_and_resumes(built):
    _, works, _ = reception(built, streak_after=3)
    assert works[arena.ACTIVE] == 1 and works[fp.WORK_ROUTE] == 0
    result, works, log = reception(built, own_active=1, own_streak=6, streak_after=7)
    seen = next(e for e in log if e[0] == 'challenge')[2]
    assert result == 0 and seen[arena.STREAK] == 6 and works[arena.STREAK] == 6 and works[arena.ACTIVE] == 1


@pytest.mark.parametrize('active, streak, kept', [(0, 0, 0), (1, 4, 1)])
def test_declining_goes_back_to_the_menu(built, active, streak, kept):
    result, works, _ = reception(built, declined=True, own_active=active, own_streak=streak, streak_after=streak)
    assert result == 1 and works[arena.ACTIVE] == kept and works[fp.WORK_ROUTE] == 0


@pytest.mark.parametrize('mode', [(0, 0, 0), (1, 1, 0)])
def test_only_accepted_singles_start_a_challenge(built, mode):
    result, works, log = reception(built, mode=mode, own_streak=5)
    assert result == 1 and not [e for e in log if e[0] in ('challenge', 'rank')]
    assert works[arena.STREAK] == 5 and fp.WORK_ROUTE not in works


@pytest.mark.parametrize('other', [f for f in fp.ACTIVE_WORK if f != 'arena'])
def test_arena_refuses_while_another_facility_is_in_progress(built, other):
    result, works, log = reception(built, active={other: 21 if other == 'factory' else 1}, own_streak=5)
    assert result == 1 and not [e for e in log if e[0] in ('challenge', 'rank', 'app')]
    assert ('msg', [factory.LINE_BUSY, 1, 0, 256, 0]) in log
    assert works[arena.STREAK] == 5 and fp.WORK_ROUTE not in works


def test_other_receptions_refuse_while_the_arena_is_in_progress(built):
    """Every other facility's reception checks the Arena's ACTIVE (factory.busy_check over patch.ACTIVE_WORK)."""
    _, retail, _, _ = built
    for program, label in ((tower.tower_program(retail), 'tower_reception'),
                           (palace.palace_program(retail), 'palace_reception'),
                           (overlay.maison_program(retail), 'factory_reception')):
        labels = program.layout()
        script = program.build_script(f'L{retail.main:x}')
        works = {arena.ACTIVE: 1}
        log = []
        stubs = natives({'WorkGet': lambda vm, a: works.get(a[0], 0),
                         'WorkSet': lambda vm, a: works.__setitem__(a[0], a[1]),
                         'FlagGet': lambda vm, a: 0, 'GlobalCall': lambda vm, a: log.append(('global', a)),
                         'GlobalGetChildParam': lambda vm, a: 0, 'GetMyWinCount': lambda vm, a: 0,
                         'SetRank': lambda vm, a: log.append(('rank', a))})
        calls = {labels[factory.CHALLENGE]: lambda vm, a: log.append(('challenge', a)) or 0,
                 labels[f'L{factory.MSG:x}']: lambda vm, a: log.append(('msg', a))}
        calls.update({labels[m]: (lambda vm, a: 0) for m in MSG - {f'L{factory.MSG:x}'}})
        assert VM(script, stubs, calls).run(labels[label]) == 1, label
        assert log == [('msg', [factory.LINE_BUSY, 1, 0, 256, 0])] and works == {arena.ACTIVE: 1}, label


def test_lost_and_cleanup_clear_the_arena_challenge(built):
    _, _, script, labels = built
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    work_set = s32(gf_hash('WorkSet'))
    clears = [x.address for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[i - 1].args == [arena.ACTIVE] and ins[i - 2].args == [0]]
    assert any(labels[factory.CLEANUP] < a < labels[factory.CLEANUP] + 0x20 for a in clears)
    assert any(labels[factory.LOST] <= a < labels[factory.LOST] + 0x10 for a in clears)
    assert not [x for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
                and ins[i - 1].args == [tower.ACTIVE]]                     # no Tower code left in the Arena
    routes = [x.address for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[i - 1].args == [fp.WORK_ROUTE] and ins[i - 2].args == [0]]
    create = s32(gf_hash('BattleInstWorkCreate'))
    at = next(x.address for x in ins if x.op == OP['SYSREQ_N'] and names[x.args[0]] == create
              and labels['L14f4'] <= x.address)
    assert any(at < a < at + 0x20 for a in routes)


def battle_points_run(built, streak, route=4):
    _, _, script, labels = built
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


@pytest.mark.parametrize('streak, bp', [(7, 1), (14, 1), (21, 1), (28, 2), (63, 4), (140, 14), (700, 15)])
def test_arena_battle_points_at_the_end_of_a_round(built, streak, bp):
    assert bp == fd.FRONTIER_BP['arena'][min(streak // 7, 30) - 1]
    assert battle_points_run(built, streak) == [('bp', bp), ('number', bp)]


@pytest.mark.parametrize('streak', [1, 6, 8, 13])
def test_no_arena_battle_points_inside_a_round(built, streak):
    assert battle_points_run(built, streak) == []


@pytest.mark.parametrize('route', [0, 1, 2, 3])
def test_maison_battle_points_without_the_arena_route(built, route):
    assert battle_points_run(built, 7, route=route) == [('bp', 2), ('number', 2)]   # GetWinCount 99 > 10: 2 BP


def test_arena_space_survey_excludes_relocated_zero_jump_tables():
    from types import SimpleNamespace
    from arena_survey import zero_runs
    cro = SimpleNamespace(data=bytes(32), segments=[(4, 24, 0)],
                          relocs=[(8, 2, 0x100), (12, 2, 0x104)])
    assert list(zero_runs(cro, minimum=8)) == [(16, 12)]


def test_arena_space_survey_stops_at_text_boundary_and_nonzero_words():
    from types import SimpleNamespace
    from arena_survey import zero_runs
    cro = SimpleNamespace(data=bytes(16) + b'CODE' + bytes(28),
                          segments=[(4, 32, 0)], relocs=[])
    assert list(zero_runs(cro, minimum=8)) == [(4, 12), (20, 16)]


@pytest.fixture(scope='module')
def arena_judge_code(tmp_path_factory):
    """Execute the linked Arena helper and actual retail ARM udiv in Unicorn."""
    import shutil
    if not fp.REPOLISHED.exists() or not shutil.which('arm-none-eabi-as'):
        pytest.skip('Local baseline and ARM binutils required')
    return fp.build()[0], fp.assemble()[1]['arena_judge']


@pytest.mark.parametrize('hp, expected', [
    ((75, 100, 25, 50), 2),                # 75% vs 50%: player wins
    ((40, 100, 50, 100), 1),               # 40% vs 50%: player loses
    ((50, 100, 25, 50), 3),                # equal ratios, different HP
    ((1, 101, 2, 300), 3),                 # both floor to 0%, not exact fractions
    ((0, 100, 1, 100), 1),
    ((1, 100, 0, 100), 2),
    ((0, 100, 0, 100), 3),
    ((65535, 65535, 65534, 65535), 2),       # unsigned u16 limits
    ((150, 100, 100, 100), 2),              # healing above entry HP is counted
    ((0, 0, 10, 100), 0),                  # missing entry snapshot: no judgement
    ((10, 100, 0, 0), 0),
])
def test_arena_cuerpo_arm_judgement(arena_judge_code, hp, expected):
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
    from unicorn import arm_const as reg
    code, entry = arena_judge_code
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(fp.BASE, (len(code) + 0xFFF) & ~0xFFF)
    uc.mem_write(fp.BASE, code)
    stack, finish = 0x8001000, 0x9000000
    uc.mem_map(stack - 0x1000, 0x1000)
    uc.mem_map(finish, 0x1000)
    uc.reg_write(reg.UC_ARM_REG_SP, stack)
    uc.reg_write(reg.UC_ARM_REG_LR, finish)
    for index, value in enumerate(hp):
        uc.reg_write(getattr(reg, f'UC_ARM_REG_R{index}'), value)
    for index in range(4, 12):
        uc.reg_write(getattr(reg, f'UC_ARM_REG_R{index}'), 0xCAFE0000 + index)
    uc.emu_start(entry, finish, count=1000)
    assert uc.reg_read(reg.UC_ARM_REG_PC) == finish
    assert uc.reg_read(reg.UC_ARM_REG_R0) == expected
    assert uc.reg_read(reg.UC_ARM_REG_SP) == stack
    for index in range(4, 12):
        assert uc.reg_read(getattr(reg, f'UC_ARM_REG_R{index}')) == 0xCAFE0000 + index


# CRO bridge execution: real patched CRO instructions and linked code.bin, with
# only allocation/dispatch/the displaced retail call replaced by ABI stubs.
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm_const as AR
import arena_engine as ae

AMEM, ASTACK, ARETURN = 0x08000000, 0x09001000, 0x0A000000
ASERVER, AMAIN, ACLIENT = AMEM, AMEM + 0x5000, AMEM + 0x6000
ASETUP, AMON0, AMON1 = AMEM + 0x7000, AMEM + 0x8000, AMEM + 0x9000
ALIST, AGAME, AWORK, ACTX, ASAVE = (AMEM + n for n in (0xA000, 0xB000, 0xC000, 0xD000, 0x10000))
AREGS = [getattr(AR, f'UC_ARM_REG_R{k}') for k in range(13)]


@pytest.fixture(scope='module')
def arena_engine_code(arena_judge_code):
    return arena_judge_code[0], fp.battle_cro()[fp.BATTLE_CRO]


def amachine(binaries, flag=True, cro_base=0x02000000):
    code, cro = binaries
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for address, data in ((fp.BASE, code), (cro_base, cro)):
        uc.mem_map(address, (len(data) + 0xFFF) & ~0xFFF)
        uc.mem_write(address, data)
    uc.mem_map(AMEM, 0x40000)
    uc.mem_map(ASTACK - 0x1000, 0x1000)
    uc.mem_map(ARETURN, 0x1000)
    for k, reg in enumerate(AREGS):
        uc.reg_write(reg, 0xCAFE0000 + k)
    uc.reg_write(AR.UC_ARM_REG_SP, ASTACK)
    uc.reg_write(AR.UC_ARM_REG_LR, ARETURN)
    def put(address, value, fmt='<I'):
        uc.mem_write(address, struct.pack(fmt, value))
    for address, value in [(ASERVER + 4, AMAIN), (AMAIN + 0x10, ASETUP), (ACLIENT, AMAIN),
                           (ASETUP + 0x7C, AGAME), (AGAME, ASAVE), (ASERVER + 0x1254, ALIST),
                           (ALIST, AMON0), (ALIST + 4, AMON1), (AWORK + 0xB78, ACTX), (ACTX + 0x1C, AGAME)]:
        put(address, value)
    put(ASETUP + 0xA8, ae.RULE if flag else 0)
    put(ALIST + 0x6E, 2, '<B')
    for mon, who in ((AMON0, 2), (AMON1, 13)):
        put(mon + 0x19, who, '<B')
        put(mon + 0x10, 100, '<H')
        put(mon + 0x158, 3, '<H')
        put(mon + 0x100, 7, '<B')       # Ghost type; the Arena hook precedes the exception
    for work in ae.HP_WORKS:
        put(ASAVE + fp.SAVE_WORKS + 2 * (work - 0x4000), 100, '<H')
    return uc, put


def au16(uc, address):
    return struct.unpack('<H', uc.mem_read(address, 2))[0]


@pytest.mark.parametrize('route, active, style, enabled', [(4, 1, 0, True), (4, 0, 0, False),
    (0, 1, 0, False), (3, 0, 0, False), (6, 0, 0, False), (4, 1, 1, False)])
def test_arena_start_marks_only_its_active_singles_setup(arena_engine_code, route, active, style, enabled):
    uc, put = amachine(arena_engine_code)
    put(AWORK + 0x6C8, ae.RULE | 0x12345)
    put(AWORK + 0x621, style, '<B')
    for work, value in ((fp.WORK_ROUTE, route), (ae.CONSTANTS['ARENA_ACTIVE'], active)):
        put(ASAVE + fp.SAVE_WORKS + 2 * (work - 0x4000), value, '<H')
    uc.reg_write(AREGS[4], AWORK)
    uc.reg_write(AREGS[5], 0x12340000)
    before = [uc.reg_read(r) for r in AREGS[1:12]]
    uc.emu_start(ae.START, ae.START + 4, count=200)
    assert uc.reg_read(AR.UC_ARM_REG_PC) == ae.START + 4
    assert struct.unpack('<I', uc.mem_read(AWORK + 0x6C8, 4))[0] == 0x12345 | (ae.RULE if enabled else 0)
    assert uc.reg_read(AREGS[0]) == 0x12340000
    assert [uc.reg_read(r) for r in AREGS[1:12]] == before
    assert uc.reg_read(AR.UC_ARM_REG_SP) == ASTACK


@pytest.mark.parametrize('flag, entrant', [(True, AMON0), (True, AMON1), (False, AMON0)])
def test_arena_entry_snapshots_hp_and_resets_native_counter(arena_engine_code, flag, entrant):
    base, site = 0x02000000, 0x724C0
    uc, put = amachine(arena_engine_code, flag)
    put(entrant + 0x10, 73, '<H')
    put(entrant + 0x158, 8, '<H')
    uc.reg_write(AREGS[4], ASERVER)
    uc.reg_write(AREGS[5], entrant)
    uc.reg_write(AREGS[11], 42)
    before = [uc.reg_read(r) for r in AREGS[2:12]]
    uc.emu_start(base + site, base + site + 16, count=200)
    assert uc.reg_read(AR.UC_ARM_REG_PC) == base + site + 16
    assert au16(uc, entrant + 0x158) == 0 and au16(uc, entrant + 0x15A) == 42
    assert uc.reg_read(AREGS[0]) == entrant + 0x100 and uc.reg_read(AREGS[1]) == 0
    assert [uc.reg_read(r) for r in AREGS[2:12]] == before
    snapshots = [au16(uc, ASAVE + fp.SAVE_WORKS + 2 * (w - 0x4000)) for w in ae.HP_WORKS]
    expected = ([73, 100] if entrant == AMON0 else [100, 73]) if flag else [100, 100]
    assert snapshots == expected
    assert uc.reg_read(AR.UC_ARM_REG_SP) == ASTACK


@pytest.mark.parametrize('flag, hp', [(True, 100), (False, 100), (True, 0)])
def test_arena_switch_bridge_blocks_ghost_and_allows_forced_replacement(arena_engine_code, flag, hp):
    base, site = 0x02000000, 0x7945C
    uc, put = amachine(arena_engine_code, flag)
    put(AMON0 + 0x10, hp, '<H')
    out = AMEM + 0xF000
    for reg, value in zip(AREGS[:4], (ACLIENT, AMON0, out, out + 4)):
        uc.reg_write(reg, value)
    before = [uc.reg_read(r) for r in AREGS[4:12]]
    stop = ARETURN if flag and hp else base + site + 16
    uc.emu_start(base + 0x79458, stop, count=200)
    assert uc.reg_read(AR.UC_ARM_REG_PC) == stop
    if flag and hp:
        assert uc.reg_read(AREGS[0]) == 3
        assert uc.mem_read(out, 1) == b'\x02' and au16(uc, out + 4) == 0
        assert uc.reg_read(AR.UC_ARM_REG_SP) == ASTACK
        assert [uc.reg_read(r) for r in AREGS[4:12]] == before
    else:
        assert uc.reg_read(AR.UC_ARM_REG_SP) == ASTACK - 48
        assert [uc.reg_read(AREGS[k]) for k in (6, 8, 10)] == [ACLIENT, AMON0, out]


@pytest.mark.parametrize('cro_base', [0x02000000, 0x03000000])
@pytest.mark.parametrize('reverse_order', [False, True])
@pytest.mark.parametrize('flag, hp, ages, expected', [
    (True, (80, 50), (3, 3), [13]),         # victory
    (True, (40, 80), (3, 3), [2]),          # defeat
    (True, (50, 50), (3, 3), [2, 13]),      # both zero BEFORE either KO is dispatched
    (True, (80, 50), (2, 2), []),
    (True, (80, 50), (8, 0), []),           # new opponent resets the pairing timer
    (False, (80, 50), (8, 8), []),
    (True, (0, 50), (3, 3), []),            # natural KO: preserve retail handling
])
def test_arena_turn_bridge_judges_once_after_three_turns(arena_engine_code, cro_base, reverse_order,
                                                       flag, hp, ages, expected):
    uc, put = amachine(arena_engine_code, flag, cro_base)
    if reverse_order:
        put(ALIST, AMON1)
        put(ALIST + 4, AMON0)
    for mon, health, age in zip((AMON0, AMON1), hp, ages):
        put(mon + 0x10, health, '<H')
        put(mon + 0x158, age, '<H')
    uc.reg_write(AREGS[6], ASERVER)
    before = [uc.reg_read(r) for r in AREGS[3:12]]
    packets, deliveries, retail = [], [], []
    def hook(machine, address, size, data):
        r0, r1, r2 = [machine.reg_read(r) for r in AREGS[:3]]
        if address == cro_base + 0x6F920:
            assert (r0, r1) == (ASERVER, 0x12)
            packet = AMEM + 0xE000 + 0x40 * len(packets)
            packets.append(r2)
            machine.reg_write(AREGS[0], packet)
        elif address == cro_base + 0x6D4EC:
            assert r0 == ASERVER
            who, force = machine.mem_read(r1 + 4, 2)
            assert force == 1
            if len(expected) == 2:
                assert au16(machine, AMON0 + 0x10) == au16(machine, AMON1 + 0x10) == 0
            deliveries.append(who)
        elif address == cro_base + 0x6B6FC:
            retail.append(r0)
            machine.reg_write(AREGS[0], 0x1234)
        else:
            return
        machine.reg_write(AR.UC_ARM_REG_PC, machine.reg_read(AR.UC_ARM_REG_LR))
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(cro_base + 0x1D21C, cro_base + 0x1D22C, count=2000)
    assert uc.reg_read(AR.UC_ARM_REG_PC) == cro_base + 0x1D22C
    assert packets == deliveries == expected and retail == [ASERVER]
    assert uc.reg_read(AREGS[0]) == 0x1234
    assert uc.reg_read(AR.UC_ARM_REG_SP) == ASTACK
    assert [uc.reg_read(r) for r in AREGS[3:12]] == before


def test_arena_bridges_do_not_overwrite_relocations_or_incoming_destinations(arena_engine_code):
    import capstone
    from cro import Cro
    cro = Cro((fp.MOD_ROMFS / fp.BATTLE_CRO).read_bytes())
    middle = {site + delta for site in ae.SITES for delta in (4, 8, 12)}
    assert not any(target in middle or target in ae.SITES for target, _, _ in cro.relocs)
    assert not any(source in middle for _, _, source in cro.relocs)
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    md.skipdata = True
    start, length, _ = cro.segments[0]
    for ins in md.disasm(cro.data[start:start + length], start):
        if ins.mnemonic.startswith('b') and ins.op_str.startswith('#'):
            assert int(ins.op_str[1:], 16) not in middle
