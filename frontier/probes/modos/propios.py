#!/usr/bin/env python3
"""Passive F9 own-team probe. Emits GDB commands, never writes inferior memory.

Usage: propios.py palace|arena DIRECTORY
       propios.py seed palace|arena SOURCE SHA256 OUTPUT
       propios.py snapshot SOURCE OUTPUT
Use before opening the selector. Palace observes code.bin imports. In Arena,
wait for the battle UI, halt, and run `python arena_loaded(0x6f3000)`. This
verifies loaded code before planting its hardware hook; remove it with
`python arena_unload()` before leaving battle (CRO reload invalidates hooks).
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / p) for p in ('scripts', 'frontier', 'faraway')]
import modes  # noqa: E402
import patch  # noqa: E402
from vertical import probe  # noqa: E402
import save_fixture as sf  # noqa: E402
import save_event as se  # noqa: E402


def seed(facility, source, sha256, destination):
    """Prepare only a separate work/ copy; retain the source party and Boxes."""
    if facility not in ('palace', 'arena'):
        raise ValueError('Palace or Arena required')
    raw = source.read_bytes()
    sf.blocks(raw)
    if hashlib.sha256(raw).hexdigest() != sha256 or se.place(raw)['zone'] != 329:
        raise ValueError('source hash or Tower zone mismatch')
    destination = destination.resolve()
    metadata = destination.with_suffix('.json')
    if not destination.is_relative_to(ROOT / 'work') or destination == source.resolve():
        raise ValueError('destination must be a separate new work/ save')
    if destination.exists() or metadata.exists():
        raise ValueError('destination or metadata already exists')
    route = patch.ROUTE[facility]
    old, record = modes.bank(route, 0)
    new, new_record = modes.bank(route, 1)
    paused = facility == 'palace'
    works = {w: 0 for w in patch.ACTIVE_WORK.values()}
    works.update({patch.WORK_ROUTE: 0, patch.ACTIVE_WORK[facility]: int(paused),
                  modes.CONFIG[route]: 0x149 if paused else 0,
                  old: 12, record: 20, new: 6 if paused else 0, new_record: 6})
    result = se.edit(raw, works=works.items(), position=(340 if paused else 457, 23, 2, 25))
    info = dict(source=str(source), source_sha256=sha256,
                sha256=hashlib.sha256(result).hexdigest(), works=works, place=se.place(result))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(result)
    with metadata.open('x') as stream:
        json.dump(info, stream, indent=2)
    return info


def snapshot(source, destination):
    """Export a checksummed lab save and measured banks/BP; no source writes."""
    data = source.read_bytes()
    blocks = sf.blocks(data)
    destination = destination.resolve()
    metadata = destination.with_suffix('.json')
    if not destination.is_relative_to(ROOT / 'work') or destination == source.resolve():
        raise ValueError('destination must be a separate new work/ save')
    if destination.exists() or metadata.exists():
        raise ValueError('destination or metadata already exists')
    works = {patch.WORK_ROUTE, 16729, 16730}
    for name in ('tower', 'palace', 'arena'):
        route = patch.ROUTE[name]
        works.update((modes.CONFIG[route], patch.ACTIVE_WORK[name]))
        for mode in (0, 1):
            works.update(modes.bank(route, mode))
    info = dict(source=str(source), sha256=hashlib.sha256(data).hexdigest(),
                valid_blocks=len(blocks), place=se.place(data),
                works={w: se.work(data, w) for w in sorted(works)},
                bp=struct.unpack_from('<H', data, 0x4230)[0],
                party_sha256=hashlib.sha256(data[sf.PARTY:sf.PARTY+0x61c]).hexdigest(),
                box_sha256=hashlib.sha256(data[0x33000:0x67ad0]).hexdigest())
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(data)
    with metadata.open('x') as stream:
        json.dump(info, stream, indent=2)
    return info


def script(facility, directory):
    route = patch.ROUTE[facility]
    if facility not in ('palace', 'arena'):
        raise ValueError('Palace or Arena required')
    s = probe(directory).replace('16573-0x4000', f'{modes.CONFIG[route]}-0x4000')
    return (s + '''python
f9_nature = None
def nature_in():
    global f9_nature
    lr = reg('lr')
    # palace_moves immediately compares the returned nature with NATURES=25.
    if lr > 0x600000 and rd(lr) == 0xe3500019:
        mon, client = reg('r5'), reg('r4')
        setup = rd(rd(client)+0x10)
        f9_nature = dict(mon=mon, client=rd(client+0x90,1), thinker=rd(client+0x91,1),
                         flag=rd(setup+0xa8), hp=rd(mon+0x10,2), maximum=rd(mon+0xe,2),
                         pct=reg('r8'), lr=lr)
    else: f9_nature = None
def nature_out():
    global f9_nature
    if f9_nature is not None:
        f9_nature['nature'] = reg('r0')
        print('F9 PALACE FILTER',json.dumps(f9_nature,sort_keys=True))
        f9_nature = None
def judge_div():
    lr = reg('lr')
    # arena_judge calls the absolute code.bin divider through ip; two calls,
    # followed by mov r6,r0 (first) or cmp r6,r0 (second).
    if (lr > 0x600000 and reg('r7') == 100 and rd(lr-4) == 0xe12fff3c
            and rd(lr) in (0xe1a06000,0xe1560000)):
        a,b = reg('r8'),reg('r9')
        print('F9 ARENA JUDGE num=%u entry=%u lr=%x ages=%u/%u hp=%u/%u snapshots=%u/%u' %
              (reg('r0'),reg('r1'),lr,rd(a+0x158,2),rd(b+0x158,2),
               rd(a+0x10,2),rd(b+0x10,2),
               rd(pv_save+0x13144+2*(16693-0x4000),2),
               rd(pv_save+0x13144+2*(16694-0x4000),2)))
f9_live_arena = []
def judge_entry():
    a,b = reg('r8'),reg('r9')
    print('F9 ARENA JUDGE ENTRY current-entry=%u/%u,%u/%u ages=%u/%u' %
          (reg('r0'),reg('r1'),reg('r2'),reg('r3'),rd(a+0x158,2),rd(b+0x158,2)))
def arena_loaded(base):
    addr = base + ARENA_JUDGE_OFFSET
    if rd(addr) != 0xe92d40f8: raise ValueError('arena_judge is not loaded at this base')
    if f9_live_arena: raise ValueError('remove the previous loaded hook first')
    f9_live_arena.append(Hook(addr,judge_entry))
    print('F9 ARENA LOADED',hex(addr))
def arena_unload():
    for hook in f9_live_arena: hook.delete()
    f9_live_arena.clear()
f9_rule_hooks = []
def rules_start():
    if f9_rule_hooks: return
    for addr, fn in RULE_HOOKS:
        f9_rule_hooks.append(Hook(addr, fn))
Hook(0x1e33dc,rules_start)
print('F9 OWN-TEAM PASSIVE READY')
end
''').replace('RULE_HOOKS', '[(0x152f08,nature_in),(0x152f30,nature_out)]' if facility == 'palace' else '[]').replace('ARENA_JUDGE_OFFSET', hex(patch.battle_cro_code()[1]['arena_judge']))


if __name__ == '__main__':
    if len(sys.argv) == 6 and sys.argv[1] == 'seed':
        print(json.dumps(seed(sys.argv[2], Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5])), indent=2))
    elif len(sys.argv) == 4 and sys.argv[1] == 'snapshot':
        print(json.dumps(snapshot(Path(sys.argv[2]), Path(sys.argv[3])), indent=2))
    elif len(sys.argv) == 3:
        print(script(sys.argv[1], sys.argv[2]), end='')
    else:
        raise SystemExit(__doc__)
