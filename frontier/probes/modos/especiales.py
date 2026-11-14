#!/usr/bin/env python3
"""F9 special facilities: new work/ copies and passive level observation.

seed dome|pike|pyramid SOURCE SHA256 OUTPUT
probe dome|pike|pyramid DIRECTORY
snapshot SOURCE OUTPUT
carry SOURCE SHA256 OUTPUT: separate paused Pike L73 fixture with reduced HP/status
Never changes a source save or writes inferior memory.
"""
from pathlib import Path
import hashlib
import contextlib
import io
import json
import runpy
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / p) for p in ('scripts', 'frontier', 'faraway')]
import modes
import patch
import save_event as se
import save_fixture as sf
import pyramid
import dome
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
             *dome.TEAM, *dome.RIVAL, *patch.DOME_FIGHT, *patch.DOME_FORCED,
             pyramid.WORK_BEATEN, pyramid.WORK_SUMMIT,
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


def carry(source, sha256, destination):
    """Isolate restoration after recalculation; HP/status are fixture inputs."""
    raw = source.read_bytes()
    sf.blocks(raw)
    if (hashlib.sha256(raw).hexdigest() != sha256
            or modes.unpack_config(6, se.work(raw, modes.CONFIG[6])) != (1, 73)
            or se.work(raw, patch.ACTIVE_WORK['pike']) != 1
            or se.work(raw, modes.bank(6, 1)[0]) != 1):
        raise ValueError('expected paused Pike Open L73 after one won room')
    works = dict(zip((*patch.PIKE_HP, *patch.PIKE_ST), (101, 77, 42, 1, 4, 5)))
    result = se.edit(raw, works=works.items())
    return output(source, destination, result, dict(source_sha256=sha256, works=works,
                  fixture='HP/status set offline; PP retained from actual first battle'))


def script(facility, directory):
    route = patch.ROUTE[facility]
    result = probe(directory).replace('16573-0x4000', f'{modes.CONFIG[route]}-0x4000')
    # Initial selector packet and native construction suffice here. Avoid a
    # persistent CRO packet breakpoint while playing the facilities.
    result = result.replace("            Hook(field_base+0x96b00,lambda: packet(rd(reg('r0')+4)))\n", '')
    if facility == 'dome':
        works = (*dome.TEAM, *patch.DOME_FIGHT, *dome.RIVAL, *patch.DOME_FORCED,
                 modes.CONFIG[route], *modes.bank(route, 0), *modes.bank(route, 1))
        result += f'''python
def dome_state():
    w = reg('r4')
    save = rd(rd(rd(w+0xb78)+0x1c))
    print('DOME STATE', {{k:rd(save+0x13144+2*(k-0x4000),2) for k in {works!r}}})
    print('DOME COUNT',rd(w+0x48))
Hook(0x1e33dc,dome_state)
Hook(0x1ef904,lambda: print('DOME SET species=%u level=%u'%(rd(reg('r0'),2),reg('r1'))))
end
'''
    if facility == 'pike':
        # Observe the existing HP/status/PP path as well. Room forcing, if wanted,
        # changes only the clock return; pk_want is empty by default.
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            runpy.run_path(str(Path(__file__).parents[1] / 'pike/lab_probe.py'))
        extra = capture.getvalue().replace(
            f"Hook({patch.battle_cro_runtime('arena_enter')},enter)\n", '').replace(
            'work(16477)', 'work(16745)').replace(
            "super().__init__('*%#x'%addr, temporary=temporary)",
            "super().__init__('*%#x'%addr, temporary=temporary, "
            "type=gdb.BP_HARDWARE_BREAKPOINT if addr >= 0x600000 else gdb.BP_BREAKPOINT)")
        _, symbols = patch.assemble()
        result += extra + f'''python
special_clock = clock
def clock():
    special_clock()
    if not pk_want:
        for point in gdb.breakpoints():
            if point.location == '*0x12fae4': point.enabled = False
def restore_value(kind):
    if {symbols['pike_build']} <= reg('lr') < {symbols['pike_iswin']}:
        print('PIKE RESTORE %s=%u core=%x'%(kind,reg('r1'),reg('r0')))
Hook(0x14f450,lambda: restore_value('hp'))
Hook(0x14f814,lambda: restore_value('status'))
end
'''
    return result


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == 'seed':
        print(json.dumps(seed(sys.argv[2], Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5])), indent=2))
    elif len(sys.argv) == 4 and sys.argv[1] == 'snapshot':
        print(json.dumps(snapshot(Path(sys.argv[2]), Path(sys.argv[3])), indent=2))
    elif len(sys.argv) == 5 and sys.argv[1] == 'carry':
        print(json.dumps(carry(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])), indent=2))
    elif len(sys.argv) == 4 and sys.argv[1] == 'probe':
        print(script(sys.argv[2], sys.argv[3]), end='')
    else:
        raise SystemExit(__doc__)
