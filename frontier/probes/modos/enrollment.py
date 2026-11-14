#!/usr/bin/env python3
"""F9 effective enrollment evidence; passive GDB probe and guarded Battle Box fixture.

box PARTY SHA BOX_SOURCE SHA OUTPUT copies three boxed PK6 cores from a separate
save, leaving the real party untouched. All input files remain unchanged.
probe DIRECTORY captures retail source exports before mode_cap, plus the native
PokeMemorySet arguments. It does not call game functions or write inferior RAM.
"""
import binascii
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / p) for p in ('scripts', 'frontier')]
import save_fixture as sf  # noqa: E402
from vertical import probe  # noqa: E402

BOX, BOX_SIZE, STORED = 0x4A00, 0x574, 0xE8
# PKHeX SaveBlockAccessor6AO / BattleBox6: block 13, six stored PK6,
# followed by lock flags. The save's own metadata/checksums must agree.


def checked(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('source hash mismatch')
    layout = sf.blocks(raw)
    if layout[13][:2] != (BOX, BOX_SIZE):
        raise ValueError('unexpected Battle Box block')
    return raw, layout


def box_fixture(party, party_sha, source, source_sha, destination):
    raw, layout = checked(party, party_sha)
    other, _ = checked(source, source_sha)
    destination = destination.resolve()
    if (not destination.is_relative_to(ROOT / 'work') or
            destination in (party.resolve(), source.resolve())):
        raise ValueError('destination must be a separate work/ save')
    metadata = destination.with_suffix('.json')
    if destination.exists() or metadata.exists():
        raise ValueError('destination already exists')
    if other[sf.PARTY + 6 * sf.PKSIZE] < 3:
        raise ValueError('three party members required in box source')
    out = bytearray(raw)
    members = []
    for slot in range(6):
        start = sf.PARTY + slot * sf.PKSIZE
        pk = sf.decode_pk(other[start:start + sf.PKSIZE]) if slot < 3 else bytes(sf.PKSIZE)
        if slot < 3:
            if not sf.u16(pk, 8):
                raise ValueError('empty box entrant')
            members.append({'slot': slot, 'species': sf.u16(pk, 8), 'level': pk[0xEC]})
        out[BOX + STORED * slot:BOX + STORED * (slot + 1)] = sf.encode_pk(pk)[:STORED]
    out[BOX + 6 * STORED:BOX + BOX_SIZE] = bytes(BOX_SIZE - 6 * STORED)
    for start, length, checksum in layout:
        struct.pack_into('<H', out, checksum, binascii.crc_hqx(out[start:start + length], 0xFFFF))
    sf.blocks(out)
    assert out[sf.PARTY:sf.PARTY + 0x61C] == raw[sf.PARTY:sf.PARTY + 0x61C]
    info = dict(party=str(party), party_sha256=party_sha, box_source=str(source),
                box_source_sha256=source_sha, sha256=hashlib.sha256(out).hexdigest(),
                members=members, party_unchanged=True,
                references=['https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/Saves/Access/SaveBlockAccessor6AO.cs',
                            'https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/Saves/Substructures/Gen6/BattleBox6.cs'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as f:
        f.write(out)
    with metadata.open('x') as f:
        json.dump(info, f, indent=2)
    return info


def script(directory):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT / 'work'):
        raise ValueError('exports must be under work/')
    extra = '''python
enrollment_dir = Path(DIRECTORY)
enrollment_copy = None
enrollment_count = 0
def selection_hooks(base):
    def memory_set():
        args = reg('r1')
        print('ENROLL MEMORY args=%s' % [rd(args+4+4*i) for i in range(3)])
    Hook(base+0x4cab4, memory_set)
    print('ENROLL MEMORY_HOOK',hex(base+0x4cab4))
def enrollment_accepted():
    w = reg('r0')
    count = rd(w+0x48)
    print('ENROLL ACCEPTED work=%x box=%u count=%u indices=%s' %
          (w,rd(w+0x2c,1),count,[rd(w+0x30+4*i) for i in range(min(count,6))]))
def enrollment_in():
    global enrollment_copy
    enrollment_copy = None
    if not mode_work: return
    party = rd(rd(rd(mode_work+0xb78)+0x1c)+0x14)
    box = rd(mode_work+0xb84)
    src = reg('r1')
    for name, owner in (('party',party),('box',box)):
        if not owner: continue
        for slot in range(6):
            if rd(owner+4*slot) == src:
                enrollment_copy = dict(source=name,slot=slot,param=src,caller=reg('lr'))
                return
def enrollment_out():
    global enrollment_count, enrollment_copy
    if enrollment_copy is None: return
    enrollment_count += 1
    p = enrollment_dir / ('source-%03u.pk6' % enrollment_count)
    p.write_bytes(bytes(gdb.selected_inferior().read_memory(rd(0x3b246c),260)))
    enrollment_copy['file'] = str(p)
    print('ENROLL EXPORT',json.dumps(enrollment_copy,sort_keys=True))
    enrollment_copy = None
Hook(0x3b2444,enrollment_in)
Hook(0x3b245c,enrollment_out)
Hook(0x1d8968,enrollment_accepted)
print('ENROLL PROBE READY')
end
'''.replace('DIRECTORY', repr(str(directory)))
    result = probe(str(directory))
    result = result.replace("print('MODES FIELD_BASE',hex(field_base))",
                            "print('MODES FIELD_BASE',hex(field_base))\n            selection_hooks(field_base)")
    return result + extra


if __name__ == '__main__':
    if len(sys.argv) == 7 and sys.argv[1] == 'box':
        print(json.dumps(box_fixture(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]),
                                     sys.argv[5], Path(sys.argv[6])), indent=2))
    elif len(sys.argv) == 3 and sys.argv[1] == 'probe':
        print(script(sys.argv[2]), end='')
    else:
        raise SystemExit(__doc__)
