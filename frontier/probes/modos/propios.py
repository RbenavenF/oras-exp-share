#!/usr/bin/env python3
"""Passive F9 own-team probe. Emits GDB commands, never writes inferior memory.

Usage: propios.py palace|arena DIRECTORY
Use before opening the selector. CODE_NATURE and UDIV are code.bin imports,
so observation does not depend on Azahar keeping breakpoints in reloaded CROs.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / p) for p in ('scripts', 'frontier')]
import modes  # noqa: E402
import patch  # noqa: E402
from vertical import probe  # noqa: E402


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
    if lr > 0x600000 and rd(lr) in (0xe1a06000,0xe1560000):
        a,b = reg('r8'),reg('r9')
        print('F9 ARENA JUDGE num=%u entry=%u lr=%x ages=%u/%u hp=%u/%u snapshots=%u/%u' %
              (reg('r0'),reg('r1'),lr,rd(a+0x158,2),rd(b+0x158,2),
               rd(a+0x10,2),rd(b+0x10,2),
               rd(pv_save+0x13144+2*(16693-0x4000),2),
               rd(pv_save+0x13144+2*(16694-0x4000),2)))
f9_rule_hooks = []
def rules_start():
    if f9_rule_hooks: return
    for addr, fn in RULE_HOOKS:
        f9_rule_hooks.append(Hook(addr, fn))
Hook(0x1e33dc,rules_start)
print('F9 OWN-TEAM PASSIVE READY')
end
''').replace('RULE_HOOKS', '[(0x152f08,nature_in),(0x152f30,nature_out)]' if facility == 'palace' else '[(0x15ec10,judge_div)]')


if __name__ == '__main__':
    print(script(sys.argv[1], sys.argv[2]), end='')
