#!/usr/bin/env python3
"""Battle Factory code.bin patch: Battle Maison battles use rental Pokémon while the Factory is active.

The rentals and their IV are read from free saved works (WORK_*, frontier/ids.py); with WORK_IV = 0 the
party builder behaves as in the retail game. Steps:
1. Check the clean and Repolished code.bin (SHA-256) and the exact words at the hook site and padding.
2. Assemble frontier/asm/rental.s with arm-none-eabi-as/ld at the start of the .text padding.
3. Redirect the player-party branch of the party builder (0x1e3d8c) to it.
4. Write code.bin and code.ips; the IPS is the diff from the clean code.bin, so it already contains
   Repolished's records and replaces its code.ips in the mod folder.

Usage: python frontier/patch.py --out work/frontier/patch
"""
import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from formats import apply_ips, read_ips, sha256  # noqa: E402
from build_patch import diff_ips  # noqa: E402

CLEAN = ROOT / 'baseline/oras/clean/exefs/code.bin'
REPOLISHED = ROOT / 'baseline/oras/repolished/exefs/code.bin'
REPOLISHED_IPS = ROOT / 'inputs/repolished/Omega Ruby Repolished (ver. 1.7.6)/code.ips'
HASHES = {
    CLEAN: 'd587c98ac5c4dedacf9be4baf2d6b7d10169e6a63f8bc35b132002cc27bc1a37',
    REPOLISHED: '3999d658b66d684df352a82c19e355b0afdb4561154bc8900e17dc0221d5f293',
    REPOLISHED_IPS: '0da174955afe9a7baf43254ce314bf5b65032f89c70a8e1065fa92ee4c2267df',
}
ASM = ROOT / 'frontier/asm/rental.s'
BASE = 0x100000
CAVE, CAVE_END = 0x579604, 0x57A000           # .text padding (reports/frontier.md §5)
SITE = 0x1E3D8C                               # player-party branch of the party builder 0x1e3d2c
SITE_BEFORE = [0xE5960B78, 0xE590001C, 0xE5908014, 0xE1A00008, 0xEB0747E4]  # ldr r0,[r6,#0xb78] .. bl 0x3b5d34
RESUME = 0x1E3DDC                             # common tail: level 50 adjust, per-member updates
FUNCTIONS = {'LOAD_SET': 0x1EFC18, 'MAKE_PARAM': 0x1EF904, 'ADD_MEMBER': 0x3B645C, 'PARTY_PREPARE': 0x3B5D34,
             'RESUME': RESUME}
FUNCTION_HEADS = {0x1EFC18: 0xE92D4030, 0x1EF904: 0xE92D4FF0, 0x3B645C: 0xE92D4070, 0x3B5D34: 0xE92D4070,
                  # saved work N at [[game data]] + 0x13140 + 4 + 2*(N - 0x4000): WorkGet (0x3fe118) ...
                  0x3FE128: 0xE592201C, 0x3FE12C: 0xE5922000, 0x3FE130: 0xE2822801, 0x3FE134: 0xE2822DC5,
                  # ... and the EventWork getter 0x11fa90 (r0 + 2*N - 0x7ffc)
                  0x11FABC: 0xE2400B1F, 0x11FAC0: 0xE2400FFF}
# Saved works, free in the retail scripts, entity data and code (frontier/ids.py) and 0 in the user's save.
WORK_IV = 16410            # Factory state: rentals' IV 1-31; 0 = inactive (retail behaviour)
WORK_SETS = (16411, 16412, 16413)   # rentals: bit 15 Super (0xb8) else Normal (0xb6), bits 0-9 set index
SUPER = 0x8000
CONSTANTS = {'WORK_IV': WORK_IV, 'ARCHIVE_NORMAL': 0xB6, 'ARCHIVE_SUPER': 0xB8, 'RENTAL_LEVEL': 50}


def word(data, va):
    return struct.unpack_from('<I', data, va - BASE)[0]


def arm_branch(source, target, link=False):
    delta = (target - source - 8) >> 2
    return (0xEB000000 if link else 0xEA000000) | (delta & 0xFFFFFF)


def assemble():
    with tempfile.TemporaryDirectory() as tmp:
        obj, elf, binary = (Path(tmp) / n for n in ('hook.o', 'hook.elf', 'hook.bin'))
        defs = [a for k, v in CONSTANTS.items() for a in ('--defsym', f'{k}={v}')]
        subprocess.run(['arm-none-eabi-as', '-mcpu=mpcore', *defs, '-o', obj, ASM], check=True)
        syms = [f'--defsym={k}={v:#x}' for k, v in FUNCTIONS.items()]
        subprocess.run(['arm-none-eabi-ld', f'-Ttext={CAVE:#x}', '-e', 'rental_hook', *syms, '-o', elf, obj],
                       check=True)
        subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', '-j', '.text', elf, binary], check=True)
        return binary.read_bytes()


def build():
    for path, expected in HASHES.items():
        if sha256(path) != expected:
            sys.exit(f'{path.relative_to(ROOT)}: unexpected sha256')
    clean, code = CLEAN.read_bytes(), bytearray(REPOLISHED.read_bytes())
    if apply_ips(clean, read_ips(REPOLISHED_IPS.read_bytes())) != bytes(code):
        sys.exit('Repolished code.bin is not clean code.bin + Repolished code.ips')
    got = [word(code, SITE + 4 * i) for i in range(len(SITE_BEFORE))]
    if got != SITE_BEFORE:
        sys.exit(f'hook site words differ: {[f"{w:08x}" for w in got]}')
    for va, head in FUNCTION_HEADS.items():
        if word(code, va) != head:
            sys.exit(f'{va:#x}: unexpected word {word(code, va):08x}')
    hook = assemble()
    if CAVE + len(hook) > CAVE_END or any(code[CAVE - BASE:CAVE - BASE + len(hook)]):
        sys.exit('hook does not fit in the zero padding')
    code[CAVE - BASE:CAVE - BASE + len(hook)] = hook
    site = [0xE1A00006,                               # mov r0, r6        (work)
            0xE1A01009,                               # mov r1, sb        (battle party)
            arm_branch(SITE + 8, CAVE, link=True),    # bl  rental_hook (Factory: continues at 0x1e3ddc)
            0xE1A08000,                               # mov r8, r0        (player party, as 0x1e3d94)
            0xE1A00000]                               # nop               (0x3b5d34 already called)
    struct.pack_into(f'<{len(site)}I', code, SITE - BASE, *site)
    return bytes(code), hook, site


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / 'work'):
        parser.error('--out must be under work/ (the output contains game code)')
    code, hook, site = build()
    out.mkdir(parents=True, exist_ok=True)
    (out / 'code.bin').write_bytes(code)
    ips = diff_ips(CLEAN.read_bytes(), code)
    if apply_ips(CLEAN.read_bytes(), read_ips(ips)) != code:
        sys.exit('IPS round trip failed')
    (out / 'code.ips').write_bytes(ips)
    print(f'hook {len(hook)} bytes at {CAVE:#x}-{CAVE + len(hook):#x}; site {SITE:#x}: '
          + ' '.join(f'{w:08x}' for w in site))
    print(f'wrote {out}/code.bin (sha256 {sha256(out / "code.bin")[:16]}…) and code.ips ({len(ips)} bytes)')


if __name__ == '__main__':
    main()
