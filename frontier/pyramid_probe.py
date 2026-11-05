#!/usr/bin/env python3
"""Laboratory-only build for Pyramid experiment 0; not part of overlay.py.

Door -> 140 (Maison lobby), receptionist -> selection -> 141 (Mirage Cave 192).
The cave's four NPCs, west to east, run battle, same-map change, save, and return.
No reward or completed-floor logic. Do not use a personal save. Before invoking
the battle NPC after a map change/reload, inspect the facility work with GDB:
this experiment deliberately does not reconstruct a missing work/selection.

Build: python frontier/pyramid_probe.py --out work/frontier/pyramid/probe
See reports/frontier-pyramid.md for measurements and the execution checklist.
"""
import argparse
from pathlib import Path
from unittest.mock import patch as replace

import factory
import island_build
import overlay
import patch
import tower
from pawn import OP, Op, Program

LOBBY, FLOOR = 140, 141
ROUTE = patch.ROUTE['pyramid']
ACTIVE = patch.ACTIVE_WORK['pyramid']
ARRIVAL = (FLOOR, 19, 0, 18, 0)


def dispatch(p, events):
    """Keep the donor's main/public identity; redirect only its existing cases."""
    at = factory._index(p, f'L{p.script.main:x}')
    table = next(o for o in p.items[at:] if isinstance(o, Op) and o.op == OP['CASETBL'])
    cases = dict(zip(table.args[2::2], table.args[3::2]))
    for event, stub in cases.items():
        start = factory._index(p, stub)
        call = next(o for o in p.items[start:] if isinstance(o, Op) and o.op == OP['CALL'])
        call.args = [events.get(event, 'L1294')]  # donor's empty routine


def change_map(r, destination):
    # Shared 79 @724/@74c: zone, x, height, y, face, 0, 0, 1, final argument.
    r.sysreq('_MapChangeCore', *destination, 0, 0, 1, 0)


def program(retail, floor=False):
    p = Program.from_script(retail)
    if not floor:
        dispatch(p, {2: 'probe_select'})
        r = factory.Routine(p, 'probe_select', ['x'])
        r.call('L798', -1)
        factory.busy_check(r, 'pyramid', 'probe_done')
        r.sysreq('BattleInstWorkCreate')
        r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
        r.call(tower.MODE_APP, 0, factory.WORK_SELECT_RESULT,
               factory.WORK_SELECT_TYPE, factory.WORK_SELECT_X, 0, 0, 0, 0, 0)
        r.sysreq('WorkGet', factory.WORK_SELECT_RESULT)
        r.op('JZER', 'probe_cancel')
        r.sysreq('WorkGet', factory.WORK_SELECT_TYPE)
        r.op('JNZ', 'probe_cancel')
        r.sysreq('SetRank', 0)
        r.sysreq('WorkGet', factory.WORK_SELECT_X)
        r.store('x')
        r.call('L457c', 'x')
        r.op('JZER', 'probe_cancel')
        r.sysreq('WorkSet', patch.WORK_ROUTE, ROUTE)
        r.sysreq('WorkSet', ACTIVE, 1)
        change_map(r, ARRIVAL)
        r.op('JUMP', 'probe_done')
        p.label('probe_cancel')
        r.sysreq('BattleHouse_End')
        r.sysreq('BattleInstWorkDelete')
        p.label('probe_done')
        r.call('La9c')
        r.const(0)
        r.ret()
    else:
        dispatch(p, {2: 'probe_battle', 3: 'probe_same', 4: 'probe_save', 5: 'probe_return'})
        r = factory.Routine(p, 'probe_battle', [])
        r.call('L798', -1)
        r.sysreq('SetTrainer', 0)
        r.call('L4', 1)
        r.sysreq('StartBattle', 0, 1)
        r.call('L4', 1)
        r.sysreq('IsWin')  # read in GDB; no streak/PB mutation
        r.call('La9c')
        r.const(0)
        r.ret()
        for label, target in [('probe_same', ARRIVAL), ('probe_return', (LOBBY, 19, 0, 30, 0))]:
            r = factory.Routine(p, label, [])
            if label == 'probe_return':
                r.sysreq('WorkSet', ACTIVE, 0)
                r.sysreq('WorkSet', patch.WORK_ROUTE, 0)
            change_map(r, target)
            r.const(0)
            r.ret()
        r = factory.Routine(p, 'probe_save', [])
        r.call('L13d4')
        r.ret()
    return p


def plan_lines():
    # Cave 192 warp 0: x=y=351 world units, z=0 (ZoneEntities.Warp),
    # i.e. tile 19.5; provisional NPC positions require an Azahar walk check.
    lines = [f'zone.{FLOOR}.clearNpcs=1', f'zone.{FLOOR}.clearTriggers=1',
             f'zone.{FLOOR}.warp.0=0,{LOBBY},0', 'regdonor.300=101']  # zone 212 header +2
    for i in range(4):
        lines.append(f'zone.{FLOOR}.npc.{i}=300,300,{i + 2},0,{16 + i * 2},17,0,1')
    return '\n'.join(lines) + '\n'


def build(out, romfs=overlay.ROMFS):
    out = Path(out).resolve()
    if not out.is_relative_to(overlay.ROOT / 'work'):
        raise ValueError('probe output must be under work/')
    archives, _ = overlay.build(romfs)
    _, retail = overlay.maison_retail(overlay.source(romfs, 'a/0/1/3'))
    scripts = overlay.facility_scripts(romfs)
    for z in (LOBBY, FLOOR):
        scripts[z] = program(retail, floor=z == FLOOR).build_script(f'L{retail.main:x}').build()
    original_plan = island_build.plan
    def probe_plan(directory):
        return original_plan(directory) + plan_lines()
    with replace.multiple(island_build,
                          CLONES={**island_build.CLONES, LOBBY: 517, FLOOR: 192},
                          KEEP_TEXT=island_build.KEEP_TEXT | {LOBBY},
                          NATIVE_DONORS={**island_build.NATIVE_DONORS, FLOOR: 517},
                          DOORS={**island_build.DOORS, 'Pyramid': (LOBBY, 0)}, plan=probe_plan):
        archives, log = island_build.build(archives, lambda rel: overlay.source(romfs, rel),
                                          out.parent / (out.name + '-island'), scripts)
        code, _, _ = patch.build(island_build.native_donors())
    out.mkdir(parents=True, exist_ok=True)
    for rel, data in {**archives, **patch.battle_cro()}.items():
        path = out / 'romfs' / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (out / 'code.ips').write_bytes(patch.diff_ips(patch.CLEAN.read_bytes(), code))
    (out / 'build.log').write_text(log)
    print(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.out)
