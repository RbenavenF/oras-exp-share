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
    """Isolated engine experiment: execute actual ARM udiv, without a ROM patch."""
    import shutil
    import subprocess
    if not fp.REPOLISHED.exists() or not shutil.which('arm-none-eabi-as'):
        pytest.skip('Local baseline and ARM binutils required')
    tmp = tmp_path_factory.mktemp('arena-judge')
    obj, elf, binary = (tmp / name for name in ('judge.o', 'judge.elf', 'judge.bin'))
    subprocess.run(['arm-none-eabi-as', '-mcpu=mpcore', '-o', obj, ROOT / 'frontier/asm/arena.s'], check=True)
    subprocess.run(['arm-none-eabi-ld', f'-Ttext={fp.CAVE:#x}', '-e', 'arena_judge',
                    '--defsym=ARENA_UDIV=0x15ec10', '-o', elf, obj], check=True)
    subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', '-j', '.text', elf, binary], check=True)
    code = bytearray(fp.REPOLISHED.read_bytes())
    helper = binary.read_bytes()
    assert len(helper) <= 128 and fp.CAVE + len(helper) < fp.CAVE_END
    # Preserve the retail implementation of udiv and its tail at 0x300788.
    code[fp.CAVE - fp.BASE:fp.CAVE - fp.BASE + len(helper)] = helper
    return bytes(code)


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
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(fp.BASE, (len(arena_judge_code) + 0xFFF) & ~0xFFF)
    uc.mem_write(fp.BASE, arena_judge_code)
    stack, finish = 0x8001000, 0x9000000
    uc.mem_map(stack - 0x1000, 0x1000)
    uc.mem_map(finish, 0x1000)
    uc.reg_write(reg.UC_ARM_REG_SP, stack)
    uc.reg_write(reg.UC_ARM_REG_LR, finish)
    for index, value in enumerate(hp):
        uc.reg_write(getattr(reg, f'UC_ARM_REG_R{index}'), value)
    for index in range(4, 12):
        uc.reg_write(getattr(reg, f'UC_ARM_REG_R{index}'), 0xCAFE0000 + index)
    uc.emu_start(fp.CAVE, finish, count=1000)
    assert uc.reg_read(reg.UC_ARM_REG_PC) == finish
    assert uc.reg_read(reg.UC_ARM_REG_R0) == expected
    assert uc.reg_read(reg.UC_ARM_REG_SP) == stack
    for index in range(4, 12):
        assert uc.reg_read(getattr(reg, f'UC_ARM_REG_R{index}')) == 0xCAFE0000 + index
