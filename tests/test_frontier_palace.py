"""Battle Palace stage A (frontier/palace.py): its zone script, run in scripts/pawn_vm.py with stubbed natives and
retail routines, and the mutual exclusion. Checks the generated logic, not the game (Azahar: reports/frontier.md
§27)."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import data as fd  # noqa: E402
import factory  # noqa: E402
import island_build  # noqa: E402
import overlay  # noqa: E402
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
    program = palace.palace_program(retail)
    labels = program.layout()
    script = program.build_script(f'L{retail.main:x}')
    return files, retail, script, labels


def test_palace_ids_are_the_assigned_ones():
    """frontier/REPARTO.md: route 3, streak 16461, challenge in progress 16462, record 16463, zone 340."""
    assert (palace.ROUTE, palace.STREAK, palace.ACTIVE, palace.RECORD) == (3, 16461, 16462, 16463)
    assert fp.ACTIVE_WORK['palace'] == palace.ACTIVE and palace.ZONE == island_build.ZONE_PALACE == 340
    assert island_build.CLONES[palace.ZONE] == island_build.DONOR_HALL and palace.ZONE in island_build.KEEP_TEXT
    assert island_build.DOORS['Palace'] == (palace.ZONE, 0)


def test_palace_script_round_trips_fits_and_is_the_overlays(built):
    files, retail, script, _ = built
    raw = palace.zone_script(retail)
    assert raw == script.build() and Script.parse(raw).build() == raw
    assert len(zo_build([*files[:2], raw, *files[3:]])) <= 17248     # the largest container measured to load (§11)
    assert overlay.facility_scripts()[palace.ZONE] == raw
    assert raw != tower.zone_script(retail)


def test_palace_menu_is_the_maisons_and_party_selection_is_retail(built):
    _, retail, script, labels = built
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    add = s32(gf_hash('ListMenuAdd'))
    menu = [ins[i - 1].args[0] for i, x in enumerate(ins) if labels['L14f4'] <= x.address < labels['L1634']
            and x.op == OP['SYSREQ_N'] and names[x.args[0]] == add]
    assert menu == tower.RECEPTION_MENU[:-1] + [factory.LINE_SYMBOLS] + tower.RECEPTION_MENU[-1:]   # «Símbolos» (F8)

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
    assert routine(palace.palace_program(retail)) == routine(Program.from_script(retail))


def reception(built, active=None, declined=False, streak_after=0, own_active=0, own_streak=0, mode=(1, 0, 7)):
    """Runs palace_reception. `active`: {facility: value} of other facilities' ACTIVE_WORK."""
    _, _, script, labels = built
    works = {fp.ACTIVE_WORK[f]: v for f, v in (active or {}).items()}
    works.update({palace.ACTIVE: own_active, palace.STREAK: own_streak})
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
    result = VM(script, stubs, calls).run(labels['palace_reception'])
    return result, works, log


def test_a_new_palace_challenge_uses_route_3(built):
    result, works, log = reception(built, own_streak=9)
    assert result == 0 and ('rank', [0]) in log
    assert ('msg', [tower.MSG_MODE, 1, 0, 256, 0]) in log                 # the mode screen, then the party screen
    _, args, seen = next(e for e in log if e[0] == 'challenge')
    assert args == [0, 0, 7]                                              # rank 0, Singles, work 0x800E
    assert seen[fp.WORK_ROUTE] == 3 and seen[palace.ACTIVE] == 1 and seen[palace.STREAK] == 0
    assert works[fp.WORK_ROUTE] == 0 and works[palace.ACTIVE] == 0       # lost: no challenge in progress
    assert all(e[1][fp.WORK_ROUTE] == 3 for e in log if e[0] == 'wins')
    assert tower.ACTIVE not in works and tower.STREAK not in works        # the Tower's works untouched


def test_a_paused_palace_challenge_stays_active_and_resumes(built):
    _, works, _ = reception(built, streak_after=3)
    assert works[palace.ACTIVE] == 1 and works[fp.WORK_ROUTE] == 0
    result, works, log = reception(built, own_active=1, own_streak=6, streak_after=7)
    seen = next(e for e in log if e[0] == 'challenge')[2]
    assert result == 0 and seen[palace.STREAK] == 6 and works[palace.STREAK] == 6 and works[palace.ACTIVE] == 1


@pytest.mark.parametrize('active, streak, kept', [(0, 0, 0), (1, 4, 1)])
def test_declining_goes_back_to_the_menu(built, active, streak, kept):
    result, works, _ = reception(built, declined=True, own_active=active, own_streak=streak, streak_after=streak)
    assert result == 1 and works[palace.ACTIVE] == kept and works[fp.WORK_ROUTE] == 0


@pytest.mark.parametrize('mode', [(0, 0, 0), (1, 1, 0)])
def test_only_accepted_singles_start_a_challenge(built, mode):
    result, works, log = reception(built, mode=mode, own_streak=5)
    assert result == 1 and not [e for e in log if e[0] in ('challenge', 'rank')]
    assert works[palace.STREAK] == 5 and fp.WORK_ROUTE not in works


@pytest.mark.parametrize('other', [f for f in fp.ACTIVE_WORK if f != 'palace'])
def test_palace_refuses_while_another_facility_is_in_progress(built, other):
    result, works, log = reception(built, active={other: 21 if other == 'factory' else 1}, own_streak=5)
    assert result == 1 and not [e for e in log if e[0] in ('challenge', 'rank', 'app')]
    assert ('msg', [factory.LINE_BUSY, 1, 0, 256, 0]) in log
    assert works[palace.STREAK] == 5 and fp.WORK_ROUTE not in works


def test_other_receptions_refuse_while_the_palace_is_in_progress(built):
    """Every other facility's reception checks the Palace's ACTIVE (factory.busy_check over patch.ACTIVE_WORK)."""
    _, retail, _, _ = built
    for program, label in ((tower.tower_program(retail), 'tower_reception'),
                           (overlay.maison_program(retail), 'factory_reception')):
        labels = program.layout()
        script = program.build_script(f'L{retail.main:x}')
        works = {palace.ACTIVE: 1}
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
        assert log == [('msg', [factory.LINE_BUSY, 1, 0, 256, 0])] and works == {palace.ACTIVE: 1}, label


def test_lost_and_cleanup_clear_the_palace_challenge(built):
    _, _, script, labels = built
    names = {i: h for i, (_, h) in enumerate(script.natives)}
    ins = decode(script.code)
    work_set = s32(gf_hash('WorkSet'))
    clears = [x.address for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[i - 1].args == [palace.ACTIVE] and ins[i - 2].args == [0]]
    assert any(labels[factory.CLEANUP] < a < labels[factory.CLEANUP] + 0x20 for a in clears)
    assert any(labels[factory.LOST] <= a < labels[factory.LOST] + 0x10 for a in clears)
    assert not [x for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
                and ins[i - 1].args == [tower.ACTIVE]]                     # no Tower code left in the Palace
    routes = [x.address for i, x in enumerate(ins) if x.op == OP['SYSREQ_N'] and names[x.args[0]] == work_set
              and ins[i - 1].args == [fp.WORK_ROUTE] and ins[i - 2].args == [0]]
    create = s32(gf_hash('BattleInstWorkCreate'))
    at = next(x.address for x in ins if x.op == OP['SYSREQ_N'] and names[x.args[0]] == create
              and labels['L14f4'] <= x.address)
    assert any(at < a < at + 0x20 for a in routes)


def battle_points_run(built, streak, route=3):
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


@pytest.mark.parametrize('streak, bp', [(7, 4), (14, 4), (21, 5), (154, 14), (161, 15), (700, 15)])
def test_palace_battle_points_at_the_end_of_a_round(built, streak, bp):
    assert bp == fd.FRONTIER_BP['palace'][min(streak // 7, 30) - 1]
    assert battle_points_run(built, streak) == [('bp', bp), ('number', bp)]


@pytest.mark.parametrize('streak', [1, 6, 8, 13])
def test_no_palace_battle_points_inside_a_round(built, streak):
    assert battle_points_run(built, streak) == []


@pytest.mark.parametrize('route', [0, 1, 2])
def test_maison_battle_points_without_the_palace_route(built, route):
    assert battle_points_run(built, 7, route=route) == [('bp', 2), ('number', 2)]   # GetWinCount 99 > 10: 2 BP


# Stage B (reports/frontier.md §32): the linked code.bin stubs and the patched DllBattle.cro bridges executed in
# Unicorn, with the real instructions around each site. Checks the logic, not the game (Azahar: §32).
import struct  # noqa: E402
import palace_engine as pe  # noqa: E402

PMEM, PSTACK, PRETURN = 0x08000000, 0x09001000, 0x0A000000
PMAIN, PCLIENT, PSETUP, PWORK, PGAME, PSAVE = (PMEM + n for n in (0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x10000))


@pytest.fixture(scope='module')
def palace_engine_code():
    import shutil
    if not fp.REPOLISHED.exists() or not shutil.which('arm-none-eabi-as'):
        pytest.skip('Local baseline and ARM binutils required')
    return fp.build()[0], fp.battle_cro()[fp.BATTLE_CRO]


def pmachine(binaries, cro_base=0x02000000):
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
    from unicorn import arm_const as AR
    code, cro = binaries
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for address, data in ((fp.BASE, code), (cro_base, cro)):
        uc.mem_map(address, (len(data) + 0xFFF) & ~0xFFF)
        uc.mem_write(address, data)
    uc.mem_map(PMEM, 0x40000)
    uc.mem_map(PSTACK - 0x1000, 0x2000)
    uc.mem_map(PRETURN, 0x1000)
    regs = [getattr(AR, f'UC_ARM_REG_R{k}') for k in range(13)]
    for k, reg in enumerate(regs):
        uc.reg_write(reg, 0xCAFE0000 + k)
    uc.reg_write(AR.UC_ARM_REG_SP, PSTACK)
    uc.reg_write(AR.UC_ARM_REG_LR, PRETURN)

    def put(address, value, fmt='<I'):
        uc.mem_write(address, struct.pack(fmt, value))
    for address, value in [(PCLIENT, PMAIN), (PMAIN + 0x10, PSETUP), (PSETUP + 0x7C, PGAME), (PGAME, PSAVE),
                           (PWORK + 0xB78, PMEM + 0x6000), (PMEM + 0x601C, PGAME)]:
        put(address, value)
    return uc, put, regs, AR


def pclient(put, ident, thinker, flag, other_bits=0x10000):
    put(PCLIENT + 0x90, ident, '<B')
    put(PCLIENT + 0x91, thinker, '<B')
    put(PSETUP + 0xA8, other_bits | (pe.RULE if flag else 0))


def test_palace_engine_ids_and_sites():
    assert (pe.ROUTE, pe.ACTIVE) == (palace.ROUTE, palace.ACTIVE) == (fp.ROUTE['palace'], fp.ACTIVE_WORK['palace'])
    import arena_engine as ae
    assert pe.RULE != ae.RULE and not set(pe.SITES) & set(ae.SITES)
    assert all(abs(a - b) >= 16 for a in pe.SITES for b in [*ae.SITES, fp.COPY_BACK])


@pytest.mark.parametrize('route, active, style, enabled', [(3, 1, 0, True), (3, 0, 0, False), (3, 1, 1, False),
    (0, 1, 0, False), (1, 1, 0, False), (2, 1, 0, False), (4, 1, 0, False), (5, 1, 0, False), (6, 1, 0, False),
    (7, 1, 0, False)])
def test_palace_start_marks_only_its_active_singles_setup(palace_engine_code, route, active, style, enabled):
    import arena_engine as ae
    uc, put, regs, AR = pmachine(palace_engine_code)
    put(PWORK + 0x6C8, pe.RULE | 0x12345)          # a stale mark is always cleared first
    put(PWORK + 0x621, style, '<B')
    for work, value in ((fp.WORK_ROUTE, route), (pe.ACTIVE, active), (ae.CONSTANTS['ARENA_ACTIVE'], 0)):
        put(PSAVE + fp.SAVE_WORKS + 2 * (work - 0x4000), value, '<H')
    uc.reg_write(regs[4], PWORK)
    uc.reg_write(regs[5], 0x12340000)
    before = [uc.reg_read(r) for r in regs[1:12]]
    uc.emu_start(ae.START, ae.START + 4, count=300)
    assert uc.reg_read(AR.UC_ARM_REG_PC) == ae.START + 4
    assert struct.unpack('<I', uc.mem_read(PWORK + 0x6C8, 4))[0] == 0x12345 | (pe.RULE if enabled else 0)
    assert uc.reg_read(regs[0]) == 0x12340000
    assert [uc.reg_read(r) for r in regs[1:12]] == before and uc.reg_read(AR.UC_ARM_REG_SP) == PSTACK


def test_arena_and_palace_marks_are_exclusive(palace_engine_code):
    import arena_engine as ae
    for route in (3, 4):
        uc, put, regs, AR = pmachine(palace_engine_code)
        for work in (fp.WORK_ROUTE, pe.ACTIVE, ae.CONSTANTS['ARENA_ACTIVE']):
            put(PSAVE + fp.SAVE_WORKS + 2 * (work - 0x4000), route if work == fp.WORK_ROUTE else 1, '<H')
        put(PWORK + 0x6C8, ae.RULE | pe.RULE)
        uc.reg_write(regs[4], PWORK)
        uc.emu_start(ae.START, ae.START + 4, count=300)
        assert struct.unpack('<I', uc.mem_read(PWORK + 0x6C8, 4))[0] == (pe.RULE if route == 3 else ae.RULE)


@pytest.mark.parametrize('cro_base', [0x02000000, 0x03000000])
@pytest.mark.parametrize('ident, thinker, argument, flag, create', [
    (1, 1, 0, False, True),       # retail AI client
    (1, 1, 1, True, False),       # retail: no AI object with that argument
    (0, 0, 0, False, False),      # retail UI client
    (0, 0, 0, True, True),        # the Palace's client 0: AI object, thinker stays UI
    (0, 0, 1, True, False),
    (1, 0, 0, True, False),       # only client 0
    (0, 2, 0, True, False),       # a replaying client is never touched
])
def test_palace_constructor_bridge_requests_an_ai_object(palace_engine_code, cro_base, ident, thinker, argument,
                                                         flag, create):
    uc, put, regs, AR = pmachine(palace_engine_code, cro_base)
    pclient(put, ident, thinker, flag)
    put(PSTACK + 0x6C, argument)
    uc.reg_write(regs[4], PCLIENT)
    before = [uc.reg_read(r) for r in regs[1:12]]
    site = cro_base + 0x731F0
    uc.emu_start(site, site + 16, count=200)
    assert uc.reg_read(AR.UC_ARM_REG_PC) == site + 16
    assert bool(uc.reg_read(AR.UC_ARM_REG_CPSR) & (1 << 30)) == create       # Z: beq 0x7321c creates it
    assert [uc.reg_read(r) for r in regs[1:12]] == before and uc.reg_read(AR.UC_ARM_REG_SP) == PSTACK
    assert uc.mem_read(PCLIENT + 0x91, 1)[0] == thinker


@pytest.mark.parametrize('cro_base', [0x02000000, 0x03000000])
@pytest.mark.parametrize('ident, thinker, flag, system, flags, target', [
    (0, 0, True, 1, pe.AI_FLAGS, 0x732C0),
    (0, 0, False, 1, 0, 0x732C0),
    (1, 1, True, 1, 0x87, 0x732C0),      # the rival keeps its own flags
    (0, 1, True, 1, 0, 0x732C0),         # a retail AI client 0 keeps its own
    (0, 0, True, 0, pe.AI_FLAGS, 0x732B0),   # missing AI system: the retail assertion path
])
def test_palace_ai_flags_bridge(palace_engine_code, cro_base, ident, thinker, flag, system, flags, target):
    from unicorn import UC_HOOK_CODE
    uc, put, regs, AR = pmachine(palace_engine_code, cro_base)
    pclient(put, ident, thinker, flag)
    put(PMAIN + 0x820, PMEM + 0x7000 if system else 0)
    uc.reg_write(regs[4], PCLIENT)
    uc.reg_write(regs[5], PMAIN)
    uc.reg_write(regs[6], 0x87 if ident else 0)
    before = [uc.reg_read(r) for r in regs[1:6] + regs[7:12]]
    stops = []

    def hook(machine, address, size, data):
        if address in (cro_base + 0x732C0, cro_base + 0x732B0, cro_base + 0x73268):
            stops.append(address - cro_base)
            machine.emu_stop()
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(cro_base + 0x73258, PRETURN, count=200)
    assert stops == [target]
    assert uc.reg_read(regs[6]) == flags
    assert [uc.reg_read(r) for r in regs[1:6] + regs[7:12]] == before and uc.reg_read(AR.UC_ARM_REG_SP) == PSTACK


@pytest.mark.parametrize('cro_base', [0x02000000, 0x03000000])
@pytest.mark.parametrize('ident, thinker, flag, command, column', [
    (0, 0, True, 3, 1), (0, 0, True, 5, 1), (0, 0, True, 6, 1),    # decisions: AI
    (0, 0, True, 7, 0), (0, 0, True, 10, 0), (0, 0, True, 2, 0),   # display and the rest: UI
    (0, 0, True, 0x101, 0), (0, 0, True, 4, 0), (0, 0, True, 8, 0),
    (0, 0, True, 0x103, 0),                                        # 0x103: byte 0 = command 3 (with byte 1 set)
    (0, 0, False, 3, 0), (0, 0, False, 5, 0),                      # unmarked battle: retail
    (1, 1, True, 3, 1), (1, 1, False, 7, 1),                       # rival unchanged
    (0, 2, True, 3, 2),                                            # replay unchanged
])
@pytest.mark.parametrize('r1', [0, 1, 3])
def test_palace_dispatch_bridge_columns(palace_engine_code, cro_base, ident, thinker, flag, command, column, r1):
    """At CRO 0x49ec r1 holds the row's byte-1 flag, not the command (Azahar 2026-11-10, §33): the command is the
    row's byte 0, so r1 must not matter."""
    uc, put, regs, AR = pmachine(palace_engine_code, cro_base)
    pclient(put, ident, thinker, flag)
    table, row = PMEM + 0x8000, 5
    put(table + 0x1C * row, command)
    if command == 0x103:
        column = 1 if (ident, thinker, flag) == (0, 0, True) else column   # byte 0 = 3: a decision
    put(PSTACK, 0x11223344)                       # [sp] is read by 0x4a74 after the dispatch
    for reg, value in zip(regs, (row, r1, table)):
        uc.reg_write(reg, value)
    uc.reg_write(regs[4], PCLIENT)
    uc.reg_write(regs[6], 0)
    before = [uc.reg_read(r) for r in (regs[4], regs[6], *regs[7:12])]
    site = cro_base + 0x49EC
    uc.emu_start(site, site + 16, count=200)
    assert uc.reg_read(AR.UC_ARM_REG_PC) == site + 16
    assert uc.reg_read(regs[3]) == column
    assert uc.reg_read(regs[0]) == 7 * row and uc.reg_read(regs[2]) == table + 0x1C * row
    assert uc.reg_read(regs[5]) == PCLIENT + 0x1E4 and uc.reg_read(regs[1]) == r1
    assert [uc.reg_read(r) for r in (regs[4], regs[6], *regs[7:12])] == before
    assert uc.reg_read(AR.UC_ARM_REG_SP) == PSTACK and uc.mem_read(PSTACK, 4) == struct.pack('<I', 0x11223344)


def test_palace_command_table_columns_are_the_measured_ones():
    """DllBattle 0xdbc68: commands 3, 5 and 6 have an AI proc; 7 (server commands: display) only a UI one."""
    from cro import Cro
    cro = Cro((fp.MOD_ROMFS / fp.BATTLE_CRO).read_bytes())
    pointers = cro.pointer_at()
    rows = {}
    for row in range(16):
        at = 0xDBC68 + 0x1C * row
        rows[struct.unpack_from('<I', cro.data, at)[0]] = [pointers.get(at + 4 + 8 * k, 0) for k in range(3)]
    assert rows[3] == [0xD8D8, 0xD0C8, 0xE5C0] and rows[7] == [0x10E40, 0, 0]
    assert all(rows[c][1] for c in pe.DECISIONS)


def test_palace_bridges_do_not_overwrite_relocations_or_incoming_destinations(palace_engine_code):
    import capstone
    from cro import Cro
    cro = Cro((fp.MOD_ROMFS / fp.BATTLE_CRO).read_bytes())
    for site, (_, before) in pe.SITES.items():
        assert cro.data[site:site + 16] == before
    middle = {site + delta for site in pe.SITES for delta in (4, 8, 12)}
    assert not any(target in middle or target in pe.SITES for target, _, _ in cro.relocs)
    assert not any(source in middle for _, _, source in cro.relocs)
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    md.skipdata = True
    start, length, _ = cro.segments[0]
    for ins in md.disasm(cro.data[start:start + length], start):
        if ins.mnemonic.startswith('b') and ins.op_str.startswith('#'):
            assert int(ins.op_str[1:], 16) not in middle


def test_palace_and_tower_menus_have_no_video_item(built):
    _, retail, _, _ = built

    def video_jumps(program):
        return [(x.op, x.args) for x in program.items if isinstance(x, Op) and x.args == [palace.VIDEO_MENU]]
    assert video_jumps(palace.palace_program(retail)) == [(OP['JUMP'], [palace.VIDEO_MENU])]
    assert video_jumps(tower.tower_program(retail)) == [(OP['JUMP'], [palace.VIDEO_MENU])]


def test_palace_and_tower_record_routines_return_at_once(built):
    _, retail, _, _ = built

    def routine(program):
        i = [k for k, x in enumerate(program.items) if not isinstance(x, Op) and x[1] == palace.VIDEO_RECORD][0]
        return [(x.op, x.args) for x in program.items[i + 1:i + 4]]
    assert routine(palace.palace_program(retail)) == [(OP['PROC'], [0]), (OP['ZERO_PRI'], [0]), (OP['RETN'], [0])]
    tower_program = tower.tower_program(retail)
    assert routine(tower_program) == routine(palace.palace_program(retail))
    calls = [x for x in palace.palace_program(retail).items if isinstance(x, Op) and x.args == [palace.VIDEO_RECORD]]
    assert len(calls) == 3


# Stage C (reports/frontier.md §36): nature move groups. The patched DllBattle.cro runs in Unicorn from its real
# `bl` at 0xd468; only the retail usable-move function 0xe044, rand 0x490 and code.bin's nature getter are stubbed.
import palace_ai  # noqa: E402

PMON, PPARAM, PCORE, PUSABLE = PMEM + 0x9000, PMEM + 0xA000, PMEM + 0xA100, PMEM + 0xB000
TACKLE, SWORDS_DANCE, THUNDER_WAVE, PROTECT, SPIKES, METRONOME, EARTHQUAKE = 33, 14, 86, 182, 191, 118, 89


@pytest.fixture(scope='module')
def move_groups():
    if not palace_ai.MOVES_GARC.exists():
        pytest.skip('Local baseline required')
    return palace_ai.move_groups()


def emerald_group(nature, low, percent):
    odds = palace_ai.NATURE_ODDS[nature][2 if low else 0:][:2]
    return 0 if percent < odds[0] else 1 if percent < odds[1] else 2


def run_filter(binaries, *, nature=0, percent=0, hp=100, max_hp=100, moves=(TACKLE,), usable=None, ident=0,
               thinker=0, flag=True, cro_base=0x02000000):
    from unicorn import UC_HOOK_CODE
    uc, put, regs, AR = pmachine(binaries, cro_base)
    pclient(put, ident, thinker, flag)
    usable = [1] * len(moves) if usable is None else usable
    put(PMON, PPARAM)
    put(PPARAM + 0xC, PCORE)
    put(PMON + 0x10, hp, '<H')
    put(PMON + 0xE, max_hp, '<H')
    put(PMON + 0x152, len(moves), '<B')
    for slot, move in enumerate(moves):
        put(PMON + 0x11C + 14 * slot, move, '<H')
    calls = []

    def stub(machine, address, size, data):
        at = address - cro_base
        if at == 0xE044:
            assert [machine.reg_read(r) for r in regs[:3]] == [PCLIENT, PMON, PUSABLE]
            flags = (list(usable) + [0] * 4)[:4]
            machine.mem_write(PUSABLE, bytes(flags))
            result = next((k for k, f in enumerate(flags) if f), 4)
        elif at == 0x490:
            assert machine.reg_read(regs[0]) == 100
            result = percent
        elif address == palace_ai.CODE_NATURE:
            assert machine.reg_read(regs[0]) == PCORE
            result = nature
        else:
            return
        calls.append(at if address != palace_ai.CODE_NATURE else 'nature')
        machine.reg_write(regs[0], result)
        machine.reg_write(AR.UC_ARM_REG_PC, machine.reg_read(AR.UC_ARM_REG_LR))
    uc.hook_add(UC_HOOK_CODE, stub)
    for reg, value in zip(regs, (PCLIENT, PMON, PUSABLE)):
        uc.reg_write(reg, value)
    before = [uc.reg_read(r) for r in regs[4:12]]
    site = cro_base + palace_ai.SITE
    uc.emu_start(site, site + 4, count=500)
    assert uc.reg_read(AR.UC_ARM_REG_PC) == site + 4
    assert [uc.reg_read(r) for r in regs[4:12]] == before and uc.reg_read(AR.UC_ARM_REG_SP) == PSTACK
    return list(uc.mem_read(PUSABLE, 4)), uc.reg_read(regs[0]), calls


def test_palace_move_group_table_from_the_move_data(move_groups):
    assert len(move_groups) == 622 and set(move_groups) == {0, 1, 2}
    expected = {TACKLE: 0, EARTHQUAKE: 0, SWORDS_DANCE: 1, PROTECT: 1, THUNDER_WAVE: 2, SPIKES: 2,
                METRONOME: 2, 115: 1, 240: 1, 68: 2, 165: 0, 176: 1, 214: 2}   # Reflect, Rain Dance, Counter
    assert {move: move_groups[move] for move in expected} == expected
    packed = palace_ai.pack_groups(move_groups)
    assert len(packed) == 156
    assert all((packed[m >> 2] >> 2 * (m & 3)) & 3 == g for m, g in enumerate(move_groups))


def test_palace_nature_odds_are_emeralds():
    assert len(palace_ai.NATURE_ODDS) == 25
    assert palace_ai.NATURE_ODDS[0] == (61, 68, 61, 68)            # Hardy
    assert palace_ai.NATURE_ODDS[2] == (70, 85, 32, 92)            # Brave
    assert palace_ai.NATURE_ODDS[22] == (88, 94, 22, 42)           # Sassy
    assert palace_ai.NATURE_ODDS[21] == (18, 88, 90, 95)           # Gentle
    assert all(a <= b <= 100 and c <= d <= 100 for a, b, c, d in palace_ai.NATURE_ODDS)
    assert len(palace_ai.pack_odds()) == 100


def test_palace_cro_blob_fits_the_code_region_padding(palace_engine_code):
    from cro import Cro
    original = (fp.MOD_ROMFS / fp.BATTLE_CRO).read_bytes()
    cro = Cro(original)
    blob, symbols = palace_ai.assemble()
    start, length, kind = cro.segments[0]
    assert kind == 0 and start + length == palace_ai.TEXT_END <= palace_ai.AT
    assert cro.segments[1][0] == palace_ai.RODATA and palace_ai.AT + len(blob) <= palace_ai.RODATA
    code_offset, code_size = struct.unpack_from('<2I', original, 0xB0)     # the region ldr:ro maps as code
    assert code_offset <= palace_ai.AT and palace_ai.AT + len(blob) <= code_offset + code_size
    assert not any(original[palace_ai.TEXT_END:palace_ai.RODATA])
    # Only one relocation points at the padding: the end of the range [0xd7610, 0xd7628) set up at 0xd68a8-0xd68c4,
    # an exclusive end that is never read. None points into the blob or patches a word in the padding.
    assert [(t, s) for t, _, s in cro.relocs if palace_ai.TEXT_END <= t < palace_ai.RODATA
            or palace_ai.TEXT_END <= s < palace_ai.RODATA] == [(0xD68F8, palace_ai.TEXT_END)]
    assert [(t, s) for t, _, s in cro.relocs if s == 0xD7610] == [(0xD68F4, 0xD7610)]
    site = palace_ai.SITE
    assert original[site:site + 4] == palace_ai.SITE_BEFORE
    assert not any(t == site or s == site for t, _, s in cro.relocs)
    patched = palace_engine_code[1]
    assert patched[palace_ai.AT:palace_ai.AT + len(blob)] == blob
    assert patched[site:site + 4] == palace_ai.bl(site, symbols['palace_moves'])


@pytest.mark.parametrize('cro_base', [0x02000000, 0x03000000])
@pytest.mark.parametrize('nature', [0, 2, 9, 11, 21, 22])      # Hardy, Brave, Lax, Hasty, Gentle, Sassy
@pytest.mark.parametrize('hp, max_hp, low', [(100, 100, False), (50, 101, True), (51, 101, False),
                                             (50, 100, True), (51, 100, False), (1, 100, True)])
def test_palace_filter_keeps_the_drawn_group(palace_engine_code, cro_base, nature, hp, max_hp, low):
    moves = (TACKLE, SWORDS_DANCE, THUNDER_WAVE, EARTHQUAKE)
    odds = palace_ai.NATURE_ODDS[nature][2 if low else 0:][:2]
    for percent in sorted({0, odds[0] - 1, odds[0], odds[1] - 1, odds[1], 99} & set(range(100))):
        group = emerald_group(nature, low, percent)
        usable, result, calls = run_filter(palace_engine_code, nature=nature, percent=percent, hp=hp,
                                           max_hp=max_hp, moves=moves, cro_base=cro_base)
        assert usable == [int(g == group) for g in (0, 1, 2, 0)], (percent, group)
        assert result == 0 and calls == [0xE044, 0x490, 'nature']


def test_palace_filter_column_switch_changes_the_group(palace_engine_code):
    """Gentle at percent 50: attack below half HP (90), defense above it (18 / 88)."""
    moves = (TACKLE, PROTECT)
    assert run_filter(palace_engine_code, nature=21, percent=50, hp=60, max_hp=100, moves=moves)[0] == [0, 1, 0, 0]
    assert run_filter(palace_engine_code, nature=21, percent=50, hp=50, max_hp=100, moves=moves)[0] == [1, 0, 0, 0]


def test_palace_filter_empty_group_keeps_every_usable_move(palace_engine_code):
    """Drawn support (Sassy, percent 99) without usable support moves: the AI keeps the others."""
    moves = (TACKLE, SWORDS_DANCE, THUNDER_WAVE)
    usable, result, _ = run_filter(palace_engine_code, nature=22, percent=99, moves=moves, usable=[1, 1, 0])
    assert usable == [1, 1, 0, 0] and result == 0
    usable, _, _ = run_filter(palace_engine_code, nature=22, percent=99, moves=(TACKLE, EARTHQUAKE))
    assert usable == [1, 1, 0, 0]


def test_palace_filter_never_revives_an_unusable_move(palace_engine_code):
    moves = (THUNDER_WAVE, TACKLE, SPIKES, EARTHQUAKE)
    usable, result, _ = run_filter(palace_engine_code, nature=22, percent=0, moves=moves, usable=[1, 0, 1, 1])
    assert usable == [0, 0, 0, 1] and result == 0      # the retail first usable slot is returned unchanged


@pytest.mark.parametrize('ident, thinker, flag', [(0, 0, False), (1, 1, True), (0, 1, True), (0, 2, True),
                                                  (1, 0, True)])
def test_palace_filter_is_retail_elsewhere(palace_engine_code, ident, thinker, flag):
    moves = (TACKLE, SWORDS_DANCE, THUNDER_WAVE)
    usable, result, calls = run_filter(palace_engine_code, nature=22, percent=0, moves=moves, ident=ident,
                                       thinker=thinker, flag=flag)
    assert usable == [1, 1, 1, 0] and result == 0 and calls == [0xE044]


def test_palace_filter_without_usable_moves_is_retail_struggle(palace_engine_code):
    usable, result, calls = run_filter(palace_engine_code, moves=(TACKLE, PROTECT), usable=[0, 0])
    assert usable == [0, 0, 0, 0] and result == 4 and calls == [0xE044]
