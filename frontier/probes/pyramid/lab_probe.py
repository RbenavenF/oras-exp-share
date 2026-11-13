#!/usr/bin/env python3
"""Emit a lab-only GDB probe using current symbols; no change to the build/save.

pv_mode = 'normal' is passive. 'win' lowers rival HP to 1 and gives it Splash;
'loss' does that to our entrants. Both server and matching client copies are
changed, as measured in Arena B. Scripts/rewards/results remain unmodified.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import patch


def script():
    _, symbols = patch.assemble()
    return '''set pagination off
set language c
python
import gdb
pv_mode = 'normal'
pv_results = 0
pv_entries = []
pv_save = 0
def rd(a, n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a,n),'little')
def wr(a,v,n=2): gdb.selected_inferior().write_memory(a,v.to_bytes(n,'little'))
def reg(n): return int(gdb.parse_and_eval('$'+n))
def state(save):
    return {w:rd(save+0x13144+2*(w-0x4000),2) for w in (16438,16441,16442,16443,16481,16482,16483,16686)}
class Hook(gdb.Breakpoint):
    def __init__(self, addr, fn):
        super().__init__('*%#x'%addr); self.fn=fn
    def stop(self):
        self.fn(); return False
def start():
    global pv_save
    w=reg('r4'); save=rd(rd(rd(w+0xb78)+0x1c)); pv_save=save
    print('PYRAMID START flag=%x state=%s mode=%s'%(rd(w+0x6c8),state(save),pv_mode))
def weaken(mon):
    copies=[mon]; client=mon-0xd98
    if all(rd(client+k)==rd(mon+k) for k in (8,12)): copies.append(client)
    for c in copies:
        wr(c+0x10,1)
        for slot in range(4):
            for off in (0x116,0x11c):
                wr(c+off+slot*14,150);wr(c+off+slot*14+2,40,1)
    print('PYRAMID LAB weaken id=%u copies=%u'%(rd(mon+0x19,1),len(copies)))
def enter():
    mon=reg('r5'); ident=rd(mon+0x19,1)
    pv_entries.append((ident,mon))
    if (pv_mode=='win' and ident>=12) or (pv_mode=='loss' and ident<12): weaken(mon)
    print('PYRAMID ENTRY id=%u hp=%u'%(ident,rd(mon+0x10,2)))
def result():
    global pv_results
    pv_results+=1
    w=reg('r0');save=rd(rd(rd(w+0xb78)+0x1c))
    print('PYRAMID RESULT n=%u raw=%u state=%s'%(pv_results,rd(w+0x73c,1),state(save)))
'''+f"Hook({0x1e33dc},start)\nHook({patch.battle_cro_runtime('arena_enter')},enter)\nHook({symbols['pike_iswin']},result)\nend\n"


if __name__ == '__main__':
    print(script(), end='')
