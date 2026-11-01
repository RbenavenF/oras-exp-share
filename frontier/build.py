#!/usr/bin/env python3
"""Battle Factory build: the Battle Maison zone script (517) changes and the code.bin patch, as an overlay.

Current scope (F4, in progress): while the Factory is active (saved work patch.WORK_IV != 0), the Maison's
party selection routine (script 517 0x457c, BattleHouse_CallPartySelectApp) is skipped and answers
"accepted" (work 0x800C = 1), so the challenge goes straight to the battle loop with the rentals.

The zone archive a/0/1/3 is read from --zones (default: the Repolished baseline; the laboratory passes the
Faraway dev overlay's, which carries the Route 102 warp), checked by SHA-256 of its zone 517 entry, and only
zone 517's script (ZO file 2) is replaced. Output under work/: romfs/a/0/1/3 and code.ips.

Usage: python frontier/build.py --out work/frontier/build [--zones PATH]
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from formats import garc_entries, lz11_compress, lz11_decompress, rebuild_garc, zo_build, zo_files  # noqa: E402
from pawn import OP, Op, Program, Script  # noqa: E402
import patch  # noqa: E402

ZONES = ROOT / 'baseline/oras/repolished/romfs/a/0/1/3'
ZONE_MAISON = 517
# Zone 517's ZO container, decompressed: identical in ORAS 1.0, Repolished 1.7.6, v0.5 and the Faraway overlay.
ZONE_MAISON_SHA256 = 'bf788f5f6aec3d24c0d387b6a8bd93e08c5e84735f555bce9cf4042a33708a75'
PARTY_SELECT = 0x457C        # PROC: BattleHouse_CallPartySelectApp(arg, 0x800C), returns work 0x800C
WORK_SELECT_RESULT = 0x800C


def maison_script(script):
    """Zone 517 script with the Factory skip at the start of the party selection routine."""
    p = Program.from_script(script)
    entry = p.items.index(('label', f'L{PARTY_SELECT:x}'))
    if not (isinstance(p.items[entry + 1], Op) and p.items[entry + 1].op == OP['PROC']):
        raise ValueError('0x457c is not a routine start')
    body = Program(script)
    body.native_hashes = p.native_hashes   # share the native table
    body.sysreq('WorkGet', patch.WORK_IV)
    body.emit('JZER', 'factory_select_retail')
    body.sysreq('WorkSet', WORK_SELECT_RESULT, 1)
    body.emit('CONST_P_PRI', 1)
    body.emit('RETN', 0)
    body.label('factory_select_retail')
    p.items[entry + 2:entry + 2] = body.items
    return p.build_script(f'L{script.main:x}')


def build(zones=ZONES):
    data = Path(zones).read_bytes()
    _, _, offset, length = garc_entries(data)[ZONE_MAISON]
    container = lz11_decompress(data[offset:offset + length])
    digest = hashlib.sha256(container).hexdigest()
    if digest != ZONE_MAISON_SHA256:
        raise ValueError(f'zone {ZONE_MAISON} differs from Repolished 1.7.6 ({digest[:16]}…)')
    files = zo_files(container)
    retail = Script.parse(files[2])
    if retail.build() != files[2]:
        raise ValueError('zone 517 script does not round-trip')
    files[2] = maison_script(retail).build()
    entry = next((e, s) for e, s, o, n in garc_entries(data) if o == offset)
    return rebuild_garc(data, {entry: lz11_compress(zo_build(files))}), files[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--zones', type=Path, default=ZONES)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / 'work'):
        parser.error('--out must be under work/ (the output contains game data)')
    zones, script = build(args.zones)
    code, hook, _ = patch.build()
    if out.exists():
        shutil.rmtree(out)
    (out / 'romfs/a/0/1').mkdir(parents=True)
    (out / 'romfs/a/0/1/3').write_bytes(zones)
    clean = patch.CLEAN.read_bytes()
    (out / 'code.ips').write_bytes(patch.diff_ips(clean, code))
    print(f'zone {ZONE_MAISON} script {len(script)} bytes; hook {len(hook)} bytes; wrote {out}')


if __name__ == '__main__':
    main()
