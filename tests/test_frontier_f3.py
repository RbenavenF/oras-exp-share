"""F3 hook (frontier/f3_patch.py) run in Unicorn from the patched site to the builder's common tail.

The three game functions it calls are stubbed and recorded; this checks the calling convention and the
control flow, not the game's behaviour (that is the Azahar test in reports/frontier.md §8).
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

import f3_patch  # noqa: E402

WORK, PARTY, STACK, HEAP, VTABLE, FREE = 0x08000000, 0x08001000, 0x09000000, 0x0A000000, 0x0B000000, 0x0B000100
REGS = {name: getattr(A, f'UC_ARM_REG_{name.upper()}') for name in
        ('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'sb', 'sl', 'fp', 'sp', 'lr', 'pc')}


@pytest.fixture(scope='module')
def patched():
    if not f3_patch.REPOLISHED.exists() or not shutil.which('arm-none-eabi-as'):
        pytest.skip('Local baseline and arm-none-eabi binutils required')
    return f3_patch.build()


def run(code, count):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x100000, (len(code) + 0xFFF) & ~0xFFF)
    uc.mem_write(0x100000, code)
    for base in (WORK, STACK - 0x10000, HEAP, VTABLE):
        uc.mem_map(base, 0x10000)
    uc.mem_write(WORK + 0x48, struct.pack('<I', count))
    uc.mem_write(WORK + 0xB70, struct.pack('<I', 0x1234))
    uc.mem_write(VTABLE + 8, struct.pack('<I', FREE))
    regs = {'r4': WORK + 0x2C, 'r5': 0x55, 'r6': WORK, 'r7': 1, 'r8': 0x88, 'sb': PARTY, 'sl': 0xAA,
            'fp': 0xBB, 'sp': STACK - 0x100, 'lr': 0xDEAD0000, 'pc': f3_patch.SITE}
    for name, value in regs.items():
        uc.reg_write(REGS[name], value)
    calls, made = [], []
    stubs = {f3_patch.FUNCTIONS['LOAD_SET']: 'load', f3_patch.FUNCTIONS['MAKE_PARAM']: 'make',
             f3_patch.FUNCTIONS['ADD_MEMBER']: 'add', FREE: 'free'}

    def hook(uc, address, size, _):
        if address not in stubs:
            return
        r = [uc.reg_read(REGS[f'r{i}']) for i in range(4)]
        sp = uc.reg_read(REGS['sp'])
        kind = stubs[address]
        if kind == 'load':
            calls.append(('load', r[0], r[1], r[2], r[3]))
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
            calls.append(('free', r[0]))
        uc.reg_write(REGS['pc'], uc.reg_read(REGS['lr']))

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(f3_patch.SITE, f3_patch.RESUME, count=5000)
    return uc, calls, made


@pytest.mark.parametrize('count', [3, 4, 6, 0])
def test_hook_builds_rentals_and_resumes(patched, count):
    code, hook, site = patched
    uc, calls, made = run(code, count)
    assert uc.reg_read(REGS['pc']) == f3_patch.RESUME
    assert uc.reg_read(REGS['r0']) == struct.unpack('<I', uc.mem_read(WORK + 0x2C + 0x1C, 4))[0] == count
    expected = []
    for i in range(count):
        index = 208 + i
        expected += [('load', 0x1234, 0xB8, index, None),
                     ('make', 1000 + index, 50, 31, 0x1234, -1, 0xFF),
                     ('add', PARTY, made[i]), ('free', made[i])]
    assert [c[:4] + (None,) if c[0] == 'load' else c for c in calls] == expected
    for name, value in {'r4': WORK + 0x2C, 'r5': 0x55, 'r6': WORK, 'r7': 1, 'r8': 0x88, 'sb': PARTY,
                        'sl': 0xAA, 'fp': 0xBB, 'sp': STACK - 0x100}.items():
        assert uc.reg_read(REGS[name]) == value, name


def test_patch_only_touches_site_and_padding(patched):
    code, hook, _ = patched
    original = f3_patch.REPOLISHED.read_bytes()
    diff = [i for i in range(len(original)) if original[i] != code[i]]
    site = f3_patch.SITE - f3_patch.BASE
    cave = f3_patch.CAVE - f3_patch.BASE
    assert all(site <= i < site + 20 or cave <= i < cave + len(hook) for i in diff)
    assert len(code) == len(original)
