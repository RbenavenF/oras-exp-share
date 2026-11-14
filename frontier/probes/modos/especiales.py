#!/usr/bin/env python3
"""F9 special facilities: new work/ copies and passive level observation.

seed dome|pike|pyramid SOURCE SHA256 OUTPUT
probe dome|pike|pyramid DIRECTORY
snapshot SOURCE OUTPUT
Never changes a source save or writes inferior memory.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / p) for p in ('scripts', 'frontier', 'faraway')]
import modes
import patch
import save_event as se
import save_fixture as sf
from vertical import probe

FACILITIES = {'dome': 456, 'pike': 458, 'pyramid': 140}


def output(source, destination, data, info):
    destination = destination.resolve()
    metadata = destination.with_suffix('.json')
    if not destination.is_relative_to(ROOT / 'work') or destination == source.resolve():
        raise ValueError('destination must be a separate new work/ save')
    if destination.exists() or metadata.exists():
        raise ValueError('destination or metadata already exists')
    sf.blocks(data)
    info.update(source=str(source), sha256=hashlib.sha256(data).hexdigest(), place=se.place(data))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(data)
    with metadata.open('x') as stream:
        json.dump(info, stream, indent=2)
    return info


def seed(facility, source, sha256, destination):
    raw = source.read_bytes()
    sf.blocks(raw)
    if hashlib.sha256(raw).hexdigest() != sha256 or se.place(raw)['zone'] != 329:
        raise ValueError('source hash or Tower zone mismatch')
    route = patch.ROUTE[facility]
    old, old_record = modes.bank(route, 0)
    new, new_record = modes.bank(route, 1)
    works = {w: 0 for w in patch.ACTIVE_WORK.values()}
    works.update({patch.WORK_ROUTE: 0, modes.CONFIG[route]: 0,
                  old: 12, old_record: 20, new: 0, new_record: 6})
    result = se.edit(raw, works=works.items(), position=(FACILITIES[facility], 23, 2, 25))
    return output(source, destination, result, dict(source_sha256=sha256, works=works))


def snapshot(source, destination):
    data = source.read_bytes()
    blocks = sf.blocks(data)
    works = {patch.WORK_ROUTE, 16729, 16730, *patch.PYRAMID_SEL, patch.PYRAMID_COUNT,
             *patch.PIKE_HP, *patch.PIKE_ST, *(w for pair in patch.PIKE_PP for w in pair)}
    for name in FACILITIES:
        route = patch.ROUTE[name]
        works.update((modes.CONFIG[route], patch.ACTIVE_WORK[name]))
        for mode in (0, 1):
            works.update(modes.bank(route, mode))
    return output(source, destination, data, dict(
        valid_blocks=len(blocks), works={w: se.work(data, w) for w in sorted(works)},
        bp=struct.unpack_from('<H', data, 0x4230)[0],
        party_sha256=hashlib.sha256(data[sf.PARTY:sf.PARTY+0x61c]).hexdigest(),
        box_sha256=hashlib.sha256(data[0x33000:0x67ad0]).hexdigest()))


def script(facility, directory):
    route = patch.ROUTE[facility]
    return probe(directory).replace('16573-0x4000', f'{modes.CONFIG[route]}-0x4000')


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == 'seed':
        print(json.dumps(seed(sys.argv[2], Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5])), indent=2))
    elif len(sys.argv) == 4 and sys.argv[1] == 'snapshot':
        print(json.dumps(snapshot(Path(sys.argv[2]), Path(sys.argv[3])), indent=2))
    elif len(sys.argv) == 4 and sys.argv[1] == 'probe':
        print(script(sys.argv[2], sys.argv[3]), end='')
    else:
        raise SystemExit(__doc__)
