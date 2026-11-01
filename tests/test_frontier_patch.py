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


def test_patch_only_touches_site_and_padding(patched):
    code, hook, _ = patched
    original = fp.REPOLISHED.read_bytes()
    diff = [i for i in range(len(original)) if original[i] != code[i]]
    site = fp.SITE - fp.BASE
    cave = fp.CAVE - fp.BASE
    assert all(site <= i < site + 20 or cave <= i < cave + len(hook) for i in diff)
    assert len(code) == len(original)
