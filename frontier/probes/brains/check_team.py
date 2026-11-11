#!/usr/bin/env python3
"""Check pre-assistance PK6 exports from lab_probe against the designed Tower or seeded Factory team.

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
import data as fd
import factory_brain
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


def inspect_factory(directory, fixture, variant):
    """Check the generated Noland trio against the seed/range before assistance."""
    import patch
    info = json.loads(fixture.read_text())
    works = {int(k): v for k, v in info['works'].items()}
    sets = fd.check_tiers(fd.load())
    offers, rival = factory_brain.team(sets, works[16490], works[patch.WORK_FSTREAK])
    assert offers == info['offers'] and rival == info['rival']
    rows = []
    for k, value in enumerate(rival, 1):
        path = directory / f'rival-{k:02d}.pk6'
        pk = decode_pk(path.read_bytes())
        s = sets['S' if value & patch.SUPER else 'N'][value & 1023]
        mask = s['evs']
        evs = [min(252, 510 // mask.bit_count()) if mask & (1 << j) else 0 for j in range(6)]
        actual = dict(species=u16(pk, 8), item=u16(pk, 0xA), nature=pk[0x1C],
                      ev=list(pk[0x1E:0x24]), iv=[(u32(pk, 0x74) >> (5 * j)) & 31 for j in range(6)],
                      moves=list(struct.unpack_from('<4H', pk, 0x5A)), friendship=pk[0xCA], level=pk[0xEC])
        expected = dict(species=s['species'], item=s['item'], nature=s['nature'], ev=evs,
                        iv=[15 if variant == brains.SILVER else 31] * 6,
                        moves=[218 if m == 216 else m for m in s['moves']], friendship=0, level=50)
        assert actual == expected, (path, actual, expected)
        assert u16(pk, 0xF0) == u16(pk, 0xF2) > 0, (path, 'not full HP')
        rows.append(dict(file=str(path), encoded_set=value, **actual, hp=u16(pk, 0xF0)))
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--variant', choices=['silver', 'gold'], default='silver')
    p.add_argument('--factory-fixture', type=Path)
    a = p.parse_args()
    variant = {'silver': brains.SILVER, 'gold': brains.GOLD}[a.variant]
    rows = inspect_factory(a.directory, a.factory_fixture, variant) if a.factory_fixture else inspect(a.directory, variant)
    print(json.dumps(rows, indent=2))
