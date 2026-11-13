#!/usr/bin/env python3
"""What Luma3DS writes into our code.bin on a console, to test the Frontier patch against it (F7-CUEVA-LUMA).

Measured on the user's 3DS with Luma's GDB stub (2026-11-13, work/frontier/consola/: console-text.bin is the
running .text 0x100000-0x57a000, console-cave.bin our cave 0x579604-0x57a000): with a LayeredFS mod, Luma's loader
(Luma3DS sysmodules/loader/source/patcher.c, patchLayeredFs / findLayeredFsPayloadOffset, checked at 1441535d)
copies its 276-byte redirection payload (romfsredir.s, romfsRedirPatchSize = 0x114) to the end of the exheader's
.text, 0x579604, because the padding after it (2556 bytes) is large enough, and replaces two FS calls with branches
to it: fsOpenFileDirectly 0x1325a4 -> payload, fsTryOpenFile 0x123e80 -> payload + 12. Its "lf:<path>" string goes
in the .rodata padding (PATH, at most 39 bytes). Azahar applies LayeredFS itself and writes none of this, which is
why the Frontier worked in Azahar and hung every Maison-type battle on the console: rental_hook was at 0x579604.

PAYLOAD is the console's copy (Luma3DS is GPLv3; these bytes are its romfsredir.s with the loader's relocated
branches and constants for this title). The words that are not relocations equal arm-none-eabi-as of
romfsredir.s at 1441535d (tests/test_frontier_luma.py checks the two substituted opcodes against code.bin).

Usage (laboratory only, never for a release): python frontier/luma.py --code <code.bin> --out <dir under work/>
writes code.bin and code.ips (diff from the clean code.bin) with Luma's payload applied, so Azahar runs what the
console runs.
"""
import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'frontier'))
sys.path.insert(0, str(ROOT / 'scripts'))

import patch  # noqa: E402

PAYLOAD = bytes.fromhex(
    '040000eaff5f2de9e5e3eeea120000eaf0412de919aaeeea030053e3f8ffff1a1f402de9d4008fe29c55eeeb04d04de2cc109fe5'
    '0d00a0e184f5f1eb0030a0e30020a0e300109de5b0008fe27ce3eeeb04d08de21f40bde8e9ffffeaff5f2de9a0308fe21c0000eb'
    '9c308f121a00001b1500001a01db4de20f002de910008de288309fe50120d3e4000052e3b220c010fbffff1ab220d1e03a0052e3'
    'fcffff1ab230d1e12f0053e3b220d1e0b220c010000052e3fbffff1a0f00bde80d10a0e1d2ffffeb01db8de2000050e3ff5fbde8'
    '0000a0031eff2f01ccffffea0190a0e104a083e201c0d3e402b0d9e40c005be11eff2f1103005ae1f9ffff1a1eff2fe16c663a00'
    '09000000726f6d3a726f6d3a14ba5e00')
AT = patch.CAVE                                   # end of the exheader .text
OPEN_DIRECTLY, TRY_OPEN = 0x1325A4, 0x123E80     # Luma's two hooks (console-text.bin)
HOOKS = {OPEN_DIRECTLY: AT, TRY_OPEN: AT + 12}
SUBSTITUTED = {OPEN_DIRECTLY: 4, TRY_OPEN: 0x10}  # payload offsets of the original instructions
PATH, PATH_MAX = 0x5EBA14, 39                     # romfsRedirPatchCustomPath (payload +0x110); not in .text
assert len(PAYLOAD) == patch.LUMA_PAYLOAD and struct.unpack_from('<I', PAYLOAD, 0x110)[0] == PATH


def overlay(code):
    """code.bin bytes as Luma leaves them in memory (payload and the two branches; .text only)."""
    out = bytearray(code)
    for site, offset in SUBSTITUTED.items():
        if struct.unpack_from('<I', out, site - patch.BASE)[0] != struct.unpack_from('<I', PAYLOAD, offset)[0]:
            raise ValueError(f'{site:#x}: not the instruction Luma substituted on the console')
    out[AT - patch.BASE:AT - patch.BASE + len(PAYLOAD)] = PAYLOAD
    for site, target in HOOKS.items():
        struct.pack_into('<I', out, site - patch.BASE, patch.arm_branch(site, target))
    return bytes(out)


def main():
    from build_patch import diff_ips
    from formats import apply_ips, read_ips
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--code', type=Path, required=True, help='our built code.bin (frontier/patch.py)')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / 'work'):
        parser.error('--out must be under work/ (the output contains game code)')
    code = overlay(args.code.read_bytes())
    clean = patch.CLEAN.read_bytes()
    ips = diff_ips(clean, code)
    if apply_ips(clean, read_ips(ips)) != code:
        sys.exit('IPS round trip failed')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'code.bin').write_bytes(code)
    (out / 'code.ips').write_bytes(ips)
    print(f'Luma payload {AT:#x}-{AT + len(PAYLOAD):#x}, branches at {OPEN_DIRECTLY:#x} and {TRY_OPEN:#x}; '
          f'wrote {out}/code.bin and code.ips ({len(ips)} bytes)')


if __name__ == '__main__':
    main()
