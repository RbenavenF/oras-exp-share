#!/usr/bin/env python3
"""F6: read-only survey of the per-zone native groups (reports/frontier.md §19).

- code.bin 0x587d58: one u32 bit mask per zone; the zone-script loader 0x3ff5a4 hands it to 0x3fbc80, which
  registers one native table per bit. Prints the zones whose mask is not the default and the bit of the
  Maison group (patch.NATIVES_MAISON).
- DllField.cro's named native table, split into its contiguous runs (one per group), with the run that holds
  the Maison natives marked.
- With --amx DUMP (gdb `x/240wx` of a loaded AMX's native table, as in §19): names every entry by its GF hash
  and counts the unresolved ones (address 0) per run.

Usage: python frontier/zone_natives.py [--amx DUMP]
"""
import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
from cro import Cro  # noqa: E402
from pawn import gf_hash  # noqa: E402
import maison_map  # noqa: E402
import patch  # noqa: E402


def runs(table):
    """Contiguous runs of the native table's slots: [(first slot, [names])]."""
    out = []
    for slot, name in sorted((slot, name) for name, (slot, _) in table.items()):
        if out and slot - out[-1][2] == 8:
            out[-1][1].append(name)
            out[-1][2] = slot
        else:
            out.append([slot, [name], slot])
    return [(first, names) for first, names, _ in out]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--amx', type=Path, help='gdb x/wx dump of an AMX native table')
    args = parser.parse_args()
    code = patch.REPOLISHED.read_bytes()
    masks = struct.unpack_from(f'<{patch.ZONE_COUNT}I', code, patch.ZONE_NATIVES - patch.BASE)
    print(f'== zone native masks at {patch.ZONE_NATIVES:#x}: {len(masks)} zones, '
          f'{sum(m == patch.NATIVES_DEFAULT for m in masks)} with the default {patch.NATIVES_DEFAULT:#x}')
    for zone, mask in enumerate(masks):
        if mask != patch.NATIVES_DEFAULT:
            print(f'zone {zone:3d} {mask:#x}' + ('  Maison group' if mask & patch.NATIVES_MAISON else ''))
    cro = Cro((maison_map.GAME / 'romfs/DllField.cro').read_bytes())
    table = maison_map.native_table(cro)
    groups = runs(table)
    print(f'== DllField.cro native table: {len(table)} natives in {len(groups)} runs')
    for first, names in groups:
        mark = '  <- Maison' if any(n in maison_map.MAISON for n in names) else ''
        print(f'{first:#x} {len(names):3d} {names[0]} .. {names[-1]}{mark}')
    if args.amx:
        run_of = {name: k for k, (_, names) in enumerate(groups) for name in names}
        by_hash = {gf_hash(name) & 0xFFFFFFFF: name for name in table}
        words = [int(w, 16) for line in args.amx.read_text().splitlines() if ':' in line
                 for w in line.split(':', 1)[1].split()]
        missing = {}
        for i in range(0, len(words) - 1, 2):
            name = by_hash.get(words[i + 1], f'{words[i + 1]:#010x}')
            if not words[i]:
                missing.setdefault(run_of.get(name, -1), []).append(name)
        print(f'== AMX dump: {len(words) // 2} natives, {sum(map(len, missing.values()))} unresolved')
        for run, names in sorted(missing.items()):
            print(f'run {run}: {len(names)} unresolved: {", ".join(names)}')


if __name__ == '__main__':
    main()
