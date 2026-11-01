#!/usr/bin/env python3
"""F3 prototype patch: Battle Maison battles use 3 fixed rental Pokémon instead of the player's party.

Laboratory build only (it changes every Maison battle that does not use the Battle Box). Steps:
1. Check the clean and Repolished code.bin (SHA-256) and the exact words at the hook site and padding.
2. Assemble frontier/asm/rental_f3.s with arm-none-eabi-as/ld at the start of the .text padding.
3. Redirect the player-party branch of the party builder (0x1e3d8c) to it.
4. Write code.bin and code.ips; the IPS is the diff from the clean code.bin, so it already contains
   Repolished's records and replaces its code.ips in the mod folder.

Usage: python frontier/f3_patch.py --out work/frontier/f3
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
ASM = ROOT / 'frontier/asm/rental_f3.s'
BASE = 0x100000
CAVE, CAVE_END = 0x579604, 0x57A000           # .text padding (reports/frontier.md §5)
SITE = 0x1E3D8C                               # player-party branch of the party builder 0x1e3d2c
SITE_BEFORE = [0xE5960B78, 0xE590001C, 0xE5908014, 0xE1A00008, 0xEB0747E4]  # ldr r0,[r6,#0xb78] .. bl 0x3b5d34
RESUME = 0x1E3DDC                             # common tail: level 50 adjust, per-member updates
FUNCTIONS = {'LOAD_SET': 0x1EFC18, 'MAKE_PARAM': 0x1EF904, 'ADD_MEMBER': 0x3B645C}
FUNCTION_HEADS = {0x1EFC18: 0xE92D4030, 0x1EF904: 0xE92D4FF0, 0x3B645C: 0xE92D4070}
# Prototype rentals: Super tier 0 starters (maisonpkS 208-213: Venusaur, Charizard, Blastoise, Meganium,
# Typhlosion, Feraligatr; frontier/data.py round 4), level 50, IV 31.
CONSTANTS = {'SET_ARCHIVE': 0xB8, 'RENTAL_LEVEL': 50, 'RENTAL_IV': 31,
             **{f'SET{i}': 208 + i for i in range(6)}}


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
            sys.exit(f'{va:#x}: unexpected function prologue {word(code, va):08x}')
    hook = assemble()
    if CAVE + len(hook) > CAVE_END or any(code[CAVE - BASE:CAVE - BASE + len(hook)]):
        sys.exit('hook does not fit in the zero padding')
    code[CAVE - BASE:CAVE - BASE + len(hook)] = hook
    site = [0xE1A00006,                               # mov r0, r6        (work)
            0xE1A01009,                               # mov r1, sb        (battle party)
            arm_branch(SITE + 8, CAVE, link=True),    # bl  rental_hook
            0xE594001C,                               # ldr r0, [r4, #0x1c] (count, as the tail expects)
            arm_branch(SITE + 16, RESUME)]            # b   0x1e3ddc
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
