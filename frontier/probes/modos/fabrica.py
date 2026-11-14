#!/usr/bin/env python3
"""Factory Open acceptance: separate checksummed lab fixtures and passive GDB probe.

seed SOURCE SHA256 OUTPUT; snapshot SOURCE OUTPUT; probe DIRECTORY
No source-save or inferior-memory writes. Run from the lane root.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / p) for p in ('scripts', 'faraway', 'frontier')]
import save_fixture as sf
import save_event as se
import factory
import factory_open as fo
import modes
import patch
from vertical import probe


def digest(data):
    return hashlib.sha256(data).hexdigest()


def output(source, destination, data, info):
    destination = destination.resolve()
    metadata = destination.with_suffix('.json')
    if not destination.is_relative_to(ROOT / 'work') or destination == source.resolve():
        raise ValueError('destination must be a separate work/ copy')
    if destination.exists() or metadata.exists():
        raise ValueError('destination already exists')
    blocks = sf.blocks(data)
    info.update(source=str(source), sha256=digest(data), valid_blocks=len(blocks),
                place=se.place(data), bp=struct.unpack_from('<H', data, 0x4230)[0],
                party_sha256=digest(data[sf.PARTY:sf.PARTY + 0x61c]),
                box_sha256=digest(data[0x33000:0x67ad0]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(data)
    with metadata.open('x') as stream:
        json.dump(info, stream, indent=2)
    return info


def seed(source, sha256, destination):
    raw = source.read_bytes()
    sf.blocks(raw)
    if digest(raw) != sha256 or se.place(raw)['zone'] != 329:
        raise ValueError('source hash or Tower zone mismatch')
    works = {v: 0 for v in patch.ACTIVE_WORK.values()}
    works.update({patch.WORK_ROUTE: 0, modes.CONFIG[1]: 0,
                  fo.WORK_DRAFT_RENTS: 0, fo.WORK_PENDING_RENT: 0})
    for mode in range(4):
        streak, record = modes.bank(1, mode)
        works.update({streak: 12 if mode == 0 else 0, record: 20 if mode == 0 else 6,
                      modes.FACTORY_RENTS[mode]: 22 + mode})
    data = se.edit(raw, works=works.items(), position=(213, 23, 2, 25))
    return output(source, destination, data, dict(source_sha256=sha256, works=works))


def snapshot(source, destination):
    data = source.read_bytes()
    works = {patch.WORK_ROUTE, patch.WORK_IV, fo.WORK_DRAFT_RENTS, fo.WORK_PENDING_RENT,
             factory.WORK_RNG, factory.WORK_STREAK, *patch.WORK_SETS, *patch.WORK_RIVAL,
             modes.CONFIG[1], 16729, 16730, *modes.FACTORY_RENTS}
    for mode in range(4):
        works.update(modes.bank(1, mode))
    return output(source, destination, data, dict(works={w: se.work(data, w) for w in sorted(works)}))


def script(directory):
    s = probe(str(directory)).replace('16573-0x4000', '16546-0x4000')
    return s + '''python
def factory_make():
    print('FACTORY MAKE L=%u IV=%u species=%u lr=%x cfg=%x' % (reg('r1'),reg('r2'),rd(reg('r0'),2),reg('lr'),level_config()))
def factory_load():
    print('FACTORY LOAD archive=%u set=%u lr=%x' % (reg('r1'),reg('r2'),reg('lr')))
Hook(0x1ef904,factory_make)
Hook(0x1efc18,factory_load)
end
'''


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == 'seed':
        print(json.dumps(seed(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])), indent=2))
    elif len(sys.argv) == 4 and sys.argv[1] == 'snapshot':
        print(json.dumps(snapshot(Path(sys.argv[2]), Path(sys.argv[3])), indent=2))
    elif len(sys.argv) == 3 and sys.argv[1] == 'probe':
        print(script(sys.argv[2]), end='')
    else:
        raise SystemExit(__doc__)
