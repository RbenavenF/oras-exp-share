#!/usr/bin/env python3
"""Lab only, passive (breakpoints that print and continue; no memory writes): GDB probe for the package test.
FRONT START at StartBattle (0x1e33dc), FRONT ENTRY per Pokémon entering (arena_enter), FRONT RESULT at IsWin
(pike_iswin) with the route work 16438 and each facility's streak/active works. Derived from
frontier/probes/pyramid/lab_probe.py without its RAM-writing modes. Usage: probe.py > work/frontier/pkg/probe.gdb"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import patch  # noqa: E402

WORKS = (16438, 16437, 16489, 16441, 16442, 16461, 16462, 16465, 16466, 16473, 16474, 16477, 16478, 16481, 16482)


def script():
    _, symbols = patch.assemble()
    return f'''set pagination off
set language c
python
import gdb
def rd(a, n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a,n),'little')
def reg(n): return int(gdb.parse_and_eval('$'+n))
def state(save):
    return ' '.join('%u=%u'%(w,rd(save+0x13144+2*(w-0x4000),2)) for w in {WORKS})
class Hook(gdb.Breakpoint):
    def __init__(self, addr, fn):
        super().__init__('*%#x'%addr); self.fn=fn
    def stop(self):
        try: self.fn()
        except Exception as e: print('FRONT PROBE ERROR', e)
        return False
def start():
    w=reg('r4'); save=rd(rd(rd(w+0xb78)+0x1c))
    print('FRONT START %s'%state(save))
def enter():
    mon=reg('r5'); print('FRONT ENTRY id=%u hp=%u'%(rd(mon+0x19,1),rd(mon+0x10,2)))
def result():
    w=reg('r0'); save=rd(rd(rd(w+0xb78)+0x1c))
    print('FRONT RESULT raw=%u %s'%(rd(w+0x73c,1),state(save)))
Hook({0x1e33dc:#x},start)
Hook({symbols['arena_enter']:#x},enter)
Hook({symbols['pike_iswin']:#x},result)
end
'''


if __name__ == '__main__':
    print(script(), end='')
