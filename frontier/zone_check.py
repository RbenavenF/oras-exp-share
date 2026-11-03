#!/usr/bin/env python3
"""Static check of a candidate interior zone, as reports/frontier.md §18 did for 209 and 213. Read-only.

For each zone number N given:
- every retail script (shared, zone and entity scripts) whose listing has N as a numeric operand, with the
  listing line and the next map change (`MapChange`-like natives within 12 lines), so a hit can be told apart
  from a frame count or a flag offset;
- warps in any zone's entity data that lead to N (the CTRMap-F5 scanner checks these too);
- aligned 32-bit words equal to N in code.bin, static.crs and the CROs (a zone table or a literal pool entry;
  small numbers also appear as plain data, so the count is compared with the verified zones 209 and 213).
- its native group mask in code.bin (patch.ZONE_NATIVES; must be the default 0x243 before cloning).

Usage: python frontier/zone_check.py 329 [340 ...]
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'faraway'), str(ROOT / 'frontier')]
from pawn import listing, native_names  # noqa: E402
import ids  # noqa: E402
import patch  # noqa: E402

GAME = ids.GAME
NUMBER = re.compile(r'(?<![@\w])-?\d+\b')
MAP_CHANGE = re.compile(r'MapChange|Warp|MapJump|ChangeMap|Jump', re.I)
VERIFIED = (209, 213)
NAMES = native_names(ROOT / 'tools/CTRMap-F5/src/ctrmap/resources/oras_natives.tsv')


def warps_to(entities, zone):
    c = entities[4:9]
    start = 12 + c[0] * 0x14 + c[1] * 0x30
    return [k for k in range(c[2]) if struct.unpack_from('<H', entities, start + 0x18 * k)[0] == zone]


def script_hits(zones):
    hits = {z: [] for z in zones}
    warps = {z: [] for z in zones}
    for name, script, head in ids.scripts(GAME / 'romfs'):
        lines = listing(script, NAMES).splitlines()
        for i, line in enumerate(lines):
            parts = line.split(None, 1)   # drop the address column
            values = {int(t) for t in NUMBER.findall(parts[1] if len(parts) > 1 else '')}
            for z in zones:
                if z in values:
                    after = next((ln.strip() for ln in lines[i + 1:i + 13] if MAP_CHANGE.search(ln)), '')
                    hits[z].append((name, line.strip(), after))
        if head and name.endswith('entities'):
            for z in zones:
                for k in warps_to(head, z):
                    warps[z].append(f'{name} warp {k}')
    return hits, warps


def code_words(zones):
    romfs = GAME / 'romfs'
    out = {z: {} for z in zones}
    for path in [GAME / 'exefs/code.bin', romfs / 'static.crs', *sorted(romfs.glob('*.cro'))]:
        data = path.read_bytes()
        words = struct.unpack_from(f'<{len(data) // 4}I', data)
        for z in zones:
            n = words.count(z)
            if n:
                out[z][path.name] = n
    return out


def main():
    zones = [int(a) for a in sys.argv[1:]]
    if not zones:
        sys.exit(__doc__)
    every = sorted(set(zones) | set(VERIFIED))
    hits, warps = script_hits(every)
    words = code_words(every)
    code = (GAME / 'exefs/code.bin').read_bytes()
    masks = struct.unpack_from(f'<{patch.ZONE_COUNT}I', code, patch.ZONE_NATIVES - patch.BASE)
    for z in every:
        tag = ' (verified, for comparison)' if z in VERIFIED and z not in zones else ''
        print(f'zone {z}{tag}: native mask {masks[z]:#x}; warps leading here: {warps[z] or "none"}')
        print(f'  script operands = {z}: {len(hits[z])}')
        for name, line, after in hits[z]:
            print(f'    {name}: {line}' + (f'   -> next map change: {after}' if after else ''))
        total = sum(words[z].values())
        print(f'  aligned u32 = {z} in code: {total} ' + str(dict(sorted(words[z].items(), key=lambda kv: -kv[1])[:6])))


if __name__ == '__main__':
    main()
