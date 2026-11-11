#!/usr/bin/env python3
"""Check pre-assistance PK6 exports from lab_probe against the designed Tower team.

Usage: check_team.py DIRECTORY [--variant silver|gold]. Commercial data stays in work/.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'frontier')]
import brains
from save_fixture import decode_pk, u16, u32


def inspect(directory, variant):
    iv, team = brains.TEAMS['tower', variant]
    rows = []
    for k, (species, item, nature, evs, moves) in enumerate(team, 1):
        path = directory / f'rival-{k:02d}.pk6'
        pk = decode_pk(path.read_bytes())
        actual = dict(species=u16(pk, 8), item=u16(pk, 0xA), nature=pk[0x1C],
                      ev=list(pk[0x1E:0x24]), iv=[(u32(pk, 0x74) >> (5 * j)) & 31 for j in range(6)],
                      moves=list(struct.unpack_from('<4H', pk, 0x5A)), friendship=pk[0xCA], level=pk[0xEC])
        expected = dict(species=brains.SPECIES[species], item=brains.ITEMS[item], nature=brains.NATURES[nature],
                        ev=list(evs), iv=[iv] * 6, moves=[brains.MOVES[m] for m in moves], friendship=255, level=50)
        assert actual == expected, (path, actual, expected)
        assert u16(pk, 0xF0) == u16(pk, 0xF2) > 0, (path, 'not full HP')
        rows.append(dict(file=str(path), **actual, hp=u16(pk, 0xF0)))
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--variant', choices=['silver', 'gold'], default='silver')
    a = p.parse_args()
    print(json.dumps(inspect(a.directory, {'silver': brains.SILVER, 'gold': brains.GOLD}[a.variant]), indent=2))
