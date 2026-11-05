"""Battle Factory hook (frontier/patch.py) run in Unicorn from the patched site.

The game functions it calls are stubbed and recorded; this checks the calling convention, the work
layout and the control flow, not the game's behaviour (that is the Azahar test in reports/frontier.md).
"""
from pathlib import Path
import shutil
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
unicorn = pytest.importorskip('unicorn')
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE  # noqa: E402
from unicorn import arm_const as A  # noqa: E402

import patch as fp  # noqa: E402

WORK, PARTY, STACK, HEAP, VTABLE, FREE = 0x08000000, 0x08001000, 0x09000000, 0x0A000000, 0x0B000000, 0x0B000100
CTX, GAMEDATA, PLAYER_PARTY, SAVE = 0x0C000000, 0x0C000100, 0x0C000200, 0x0D000000
REGS = {name: getattr(A, f'UC_ARM_REG_{name.upper()}') for name in
        ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'sb', 'sl', 'fp', 'sp', 'lr', 'pc')}
AFTER_ORIGINAL_PREPARE = 0x1E3DA0


@pytest.fixture(scope='module')
def patched():
    if not fp.REPOLISHED.exists() or not shutil.which('arm-none-eabi-as'):
        pytest.skip('Local baseline and arm-none-eabi binutils required')
    return fp.build()


def work_address(number):
    return SAVE + 0x13144 + 2 * (number - 0x4000)


def run(code, count, iv, sets=(0, 0, 0), stop=fp.RESUME):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x100000, (len(code) + 0xFFF) & ~0xFFF)
    uc.mem_write(0x100000, code)
    for base in (WORK, STACK - 0x10000, HEAP, VTABLE, CTX):
        uc.mem_map(base, 0x10000)
    uc.mem_map(SAVE, 0x20000)
    uc.mem_write(WORK + 0x48, struct.pack('<I', count))
    uc.mem_write(WORK + 0xB70, struct.pack('<I', 0x1234))
    uc.mem_write(WORK + 0xB78, struct.pack('<I', CTX))
    uc.mem_write(CTX + 0x1C, struct.pack('<I', GAMEDATA))
    uc.mem_write(GAMEDATA, struct.pack('<I', SAVE))
    uc.mem_write(GAMEDATA + 0x14, struct.pack('<I', PLAYER_PARTY))
    uc.mem_write(work_address(fp.WORK_IV), struct.pack('<H', iv))
    for number, value in zip(fp.WORK_SETS, sets):
        uc.mem_write(work_address(number), struct.pack('<H', value))
    uc.mem_write(VTABLE + 8, struct.pack('<I', FREE))
    regs = {'r4': WORK + 0x2C, 'r5': 0x55, 'r6': WORK, 'r7': 1, 'r8': 0x88, 'sb': PARTY, 'sl': 0xAA,
            'fp': 0xBB, 'sp': STACK - 0x100, 'lr': 0xDEAD0000, 'pc': fp.SITE}
    for name, value in regs.items():
        uc.reg_write(REGS[name], value)
    calls, made = [], []
    stubs = {fp.FUNCTIONS['LOAD_SET']: 'load', fp.FUNCTIONS['MAKE_PARAM']: 'make',
             fp.FUNCTIONS['ADD_MEMBER']: 'add', fp.FUNCTIONS['PARTY_PREPARE']: 'prepare', FREE: 'free'}

    def hook(uc, address, size, _):
        if address not in stubs:
            return
        r = [uc.reg_read(REGS[f'r{i}']) for i in range(4)]
        sp = uc.reg_read(REGS['sp'])
        kind = stubs[address]
        if kind == 'load':
            calls.append(('load', r[0], r[1], r[2]))
            uc.mem_write(r[3], struct.pack('<H', 1000 + r[2]) + bytes(14))
        elif kind == 'make':
            stack = struct.unpack('<iI', uc.mem_read(sp, 8))
            species = struct.unpack('<H', uc.mem_read(r[0], 2))[0]
            obj = HEAP + 0x100 * len(made)
            made.append(obj)
            uc.mem_write(obj, struct.pack('<I', VTABLE))
            calls.append(('make', species, r[1], r[2], r[3], *stack))
            uc.reg_write(REGS['r0'], obj)
        elif kind == 'add':
            calls.append(('add', r[0], r[1]))
        else:
            calls.append((kind, r[0]))
        uc.reg_write(REGS['pc'], uc.reg_read(REGS['lr']))

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(fp.SITE, stop, count=5000)
    return uc, calls, made


def preserved(uc, **changed):
    expected = {'r4': WORK + 0x2C, 'r5': 0x55, 'r6': WORK, 'r7': 1, 'r8': 0x88, 'sb': PARTY, 'sl': 0xAA,
                'fp': 0xBB, 'sp': STACK - 0x100, **changed}
    for name, value in expected.items():
        assert uc.reg_read(REGS[name]) == value, name


def test_inactive_factory_keeps_the_retail_branch(patched):
    code, _, _ = patched
    uc, calls, _ = run(code, 3, iv=0, sets=(fp.SUPER | 208, 5, 6), stop=AFTER_ORIGINAL_PREPARE)
    assert uc.reg_read(REGS['pc']) == AFTER_ORIGINAL_PREPARE
    assert calls == [('prepare', PLAYER_PARTY)]
    preserved(uc, r8=PLAYER_PARTY)
    assert struct.unpack('<I', uc.mem_read(WORK + 0x48, 4))[0] == 3


@pytest.mark.parametrize('count', [3, 4, 6, 2, 0])
def test_active_factory_builds_the_rentals(patched, count):
    code, _, _ = patched
    a = fp.ABILITY_SHIFT
    sets = (fp.SUPER | 208, 1 << a | 66, fp.SUPER | fp.ABILITY_RANDOM << a | 907)
    uc, calls, made = run(code, count, iv=21, sets=sets)
    assert uc.reg_read(REGS['pc']) == fp.RESUME
    assert uc.reg_read(REGS['r0']) == 3
    assert struct.unpack('<I', uc.mem_read(WORK + 0x48, 4))[0] == 3
    want = []
    for i, (value, ability) in enumerate(zip(sets, (0, 1, -1))):
        archive, index = (0xB8 if value & fp.SUPER else 0xB6), value & 0x3FF
        want += [('load', 0x1234, archive, index), ('make', 1000 + index, 50, 21, 0x1234, ability, 0xFF),
                 ('add', PARTY, made[i]), ('free', made[i])]
    assert calls == want
    preserved(uc)


def test_patch_only_touches_site_padding_and_text_row(patched):
    code, hook, _ = patched
    original = fp.REPOLISHED.read_bytes()
    diff = [i for i in range(len(original)) if original[i] != code[i]]
    site = fp.SITE - fp.BASE
    cave = fp.CAVE - fp.BASE
    text = fp.GLOBAL_ROW - fp.BASE + 8
    singles = [va - fp.BASE for va in (fp.RIVAL_SITE, fp.COUNT_SITE, *fp.STREAK_SITES, fp.BUILD_SITE, fp.ISWIN,
                                        fp.DELETE_SITE, fp.ae.START)]
    assert all(site <= i < site + 20 or cave <= i < cave + len(hook) or text <= i < text + 2
               or any(s <= i < s + 4 for s in singles) for i in diff)
    assert struct.unpack_from('<8H', code, fp.GLOBAL_ROW - fp.BASE) == (9770, 9779, 5, 1, fp.TEXT_FACTORY, 0, 0, 0)
    assert len(code) == len(original)


def run_rival(code, slot, iv, index=0x1A7):
    """Execute the patched rival-builder instruction at 0x1e4b34 up to the next one."""
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x100000, (len(code) + 0xFFF) & ~0xFFF)
    uc.mem_write(0x100000, code)
    for base in (WORK, STACK - 0x10000, CTX, HEAP):
        uc.mem_map(base, 0x10000)
    uc.mem_map(SAVE, 0x20000)
    uc.mem_write(WORK + 0xB78, struct.pack('<I', CTX))
    uc.mem_write(CTX + 0x1C, struct.pack('<I', GAMEDATA))
    uc.mem_write(GAMEDATA, struct.pack('<I', SAVE))
    uc.mem_write(work_address(fp.WORK_IV), struct.pack('<H', iv))
    for number in fp.WORK_RIVAL:
        uc.mem_write(work_address(number), struct.pack('<H', 0xBEEF))
    uc.mem_write(HEAP + 4, struct.pack('<H', index))
    regs = {'r0': HEAP, 'r1': 0x11, 'r2': 0x22, 'r3': 0x33, 'r4': 0x44, 'r7': slot, 'fp': WORK,
            'sp': STACK - 0x100, 'lr': 0xDEAD0000}
    for name, value in regs.items():
        uc.reg_write(REGS[name], value)
    uc.emu_start(fp.RIVAL_SITE, fp.RIVAL_SITE + 4, count=100)
    rivals = [struct.unpack('<H', uc.mem_read(work_address(n), 2))[0] for n in fp.WORK_RIVAL]
    return uc, rivals


@pytest.mark.parametrize('slot', [0, 1, 2, 3, 5])
def test_rival_sets_are_copied_while_the_factory_is_active(patched, slot):
    code, _, _ = patched
    uc, rivals = run_rival(code, slot, iv=21)
    assert uc.reg_read(REGS['pc']) == fp.RIVAL_SITE + 4
    assert uc.reg_read(REGS['r4']) == 0x1A7                     # the original load still happens
    for name, value in {'r2': 0x22, 'r3': 0x33, 'r7': slot, 'fp': WORK, 'sp': STACK - 0x100}.items():
        assert uc.reg_read(REGS[name]) == value, name
    assert rivals == [0x1A7 if k == slot else 0xBEEF for k in range(3)]


def test_rival_sets_untouched_while_the_factory_is_inactive(patched):
    code, _, _ = patched
    uc, rivals = run_rival(code, 1, iv=0)
    assert uc.reg_read(REGS['r4']) == 0x1A7 and rivals == [0xBEEF] * 3


ENTRY = {'inc': 0x45CD98, 'get': 0x45CEE8, 'clear': 0x45CF8C, 'record': 0x45D010}


def run_streak(code, func, rank, route, maison=(5, 9, 40, 70), factory=(3, 30), streak=None):
    """Run a Maison Singles streak accessor; maison = (current N, current S, record N, record S). factory is the
    (streak, record) of the facility whose streak work is `streak` (default the Factory's)."""
    streak = fp.WORK_FSTREAK if streak is None else streak
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x100000, (len(code) + 0xFFF) & ~0xFFF)
    uc.mem_write(0x100000, code)
    uc.mem_map(STACK - 0x10000, 0x10000)
    uc.mem_map(SAVE, 0x20000)
    base = SAVE + fp.MAISON_BASE
    uc.mem_write(base + 0x1C4, struct.pack('<4H', *maison))
    uc.mem_write(work_address(fp.WORK_ROUTE), struct.pack('<H', route))
    uc.mem_write(work_address(streak), struct.pack('<H', factory[0]))
    uc.mem_write(work_address(streak + 2), struct.pack('<H', factory[1]))
    for name, value in {'r0': base, 'r1': 0, 'r2': rank, 'r3': 0x33, 'sp': STACK - 0x100, 'lr': 0xDEAD0000}.items():
        uc.reg_write(REGS[name], value)
    uc.mem_map(0xDEAD0000, 0x1000)
    uc.emu_start(ENTRY[func], 0xDEAD0000, count=200)
    maison_after = struct.unpack('<4H', uc.mem_read(base + 0x1C4, 8))
    factory_after = tuple(struct.unpack('<H', uc.mem_read(work_address(n), 2))[0]
                          for n in (streak, streak + 2))
    return uc.reg_read(REGS['r0']), maison_after, factory_after


@pytest.mark.parametrize('rank, route', [(0, 0), (1, 0), (1, 1), (0, len(fp.STREAK_ROUTES) + 1), (0, 0xFFFF)])
def test_maison_streaks_untouched_without_the_factory_route(patched, rank, route):
    code, _, _ = patched
    assert run_streak(code, 'get', rank, route)[0] == (5, 9)[rank]
    assert run_streak(code, 'record', rank, route)[0] == (40, 70)[rank]
    _, maison, factory = run_streak(code, 'inc', rank, route)
    assert maison == ((6, 9, 40, 70) if rank == 0 else (5, 10, 40, 70)) and factory == (3, 30)
    _, maison, factory = run_streak(code, 'clear', rank, route)
    assert maison == ((0, 9, 40, 70) if rank == 0 else (5, 0, 40, 70)) and factory == (3, 30)


def test_factory_route_uses_its_own_streak_and_record(patched):
    code, _, _ = patched
    assert run_streak(code, 'get', 0, 1)[0] == 3
    assert run_streak(code, 'record', 0, 1)[0] == 30
    _, maison, factory = run_streak(code, 'inc', 0, 1)
    assert maison == (5, 9, 40, 70) and factory == (4, 30)
    _, maison, factory = run_streak(code, 'inc', 0, 1, factory=(30, 30))
    assert maison == (5, 9, 40, 70) and factory == (31, 31)          # new Factory record
    _, maison, factory = run_streak(code, 'clear', 0, 1)
    assert maison == (5, 9, 40, 70) and factory == (0, 30)


@pytest.mark.parametrize('route', sorted(fp.STREAK_ROUTES))
def test_each_route_uses_its_facilitys_streak_and_record(patched, route):
    """WORK_ROUTE = r points the Normal Singles streak at STREAK_ROUTES[r]'s works, and at no other route's."""
    code, _, _ = patched
    streak = fp.STREAK_ROUTES[route][1]
    assert run_streak(code, 'get', 0, route, streak=streak)[0] == 3
    assert run_streak(code, 'record', 0, route, streak=streak)[0] == 30
    _, maison, own = run_streak(code, 'inc', 0, route, streak=streak, factory=(30, 30))
    assert maison == (5, 9, 40, 70) and own == (31, 31)
    for other, (_, works) in fp.STREAK_ROUTES.items():
        if other != route:      # another facility's works stay as they were
            assert run_streak(code, 'inc', 0, route, streak=works, factory=(7, 8))[2] == (7, 8)


def zone_mask(code, zone):
    return struct.unpack_from('<I', code, fp.ZONE_NATIVES - fp.BASE + 4 * zone)[0]


def test_zone_natives_give_a_clone_its_donors_groups():
    if not fp.REPOLISHED.exists():
        pytest.skip('Local baseline required')
    original = fp.REPOLISHED.read_bytes()
    assert (zone_mask(original, 213), zone_mask(original, 517)) == (fp.NATIVES_DEFAULT, 0x343)
    code = bytearray(original)
    fp.zone_natives(code, {213: 517})
    assert zone_mask(code, 213) & fp.NATIVES_MAISON
    diff = [i for i in range(len(code)) if code[i] != original[i]]
    word = fp.ZONE_NATIVES - fp.BASE + 4 * 213
    assert diff and all(word <= i < word + 4 for i in diff)


def test_zone_natives_refuse_an_unexpected_table():
    if not fp.REPOLISHED.exists():
        pytest.skip('Local baseline required')
    code = bytearray(fp.REPOLISHED.read_bytes())
    with pytest.raises(SystemExit):
        fp.zone_natives(code, {517: 448})                # the slot is not a default zone
    struct.pack_into('<I', code, fp.ZONE_NATIVES - fp.BASE + 4 * 520, fp.NATIVES_DEFAULT)
    with pytest.raises(SystemExit):
        fp.zone_natives(code, {213: 517})                # the Maison zones are not the measured ones
