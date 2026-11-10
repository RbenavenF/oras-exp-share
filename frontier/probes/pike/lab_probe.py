#!/usr/bin/env python3
"""Emit a Pike PP GDB probe. pk_mode='win' weakens rival copies only; 'normal' observes."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import patch

_, symbols = patch.assemble()
print('''set pagination off
set language c
python
import gdb
pk_mode='normal'
pk_results=0
def rd(a,n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a,n),'little')
def wr(a,v,n=2): gdb.selected_inferior().write_memory(a,v.to_bytes(n,'little'))
def reg(n): return int(gdb.parse_and_eval('$'+n))
class Hook(gdb.Breakpoint):
    def __init__(self, addr, fn):
        super().__init__('*%#x'%addr); self.fn=fn
    def stop(self):
        self.fn(); return False
def pp():
    print('PIKE PP mode=%u slot=%u current=%u saved=%s'%(reg('r6'),reg('r7'),reg('r0'),
       [rd(reg('r5')+off,1) for off in (0,1,8,9)]))
def result():
    global pk_results
    pk_results+=1
    w=reg('r0');s=rd(rd(rd(w+0xb78)+0x1c))
    print('PIKE RESULT n=%u raw=%u works=%s'%(pk_results,rd(w+0x73c,1),
       {i:rd(s+0x13144+2*(i-0x4000),2) for i in (16438,16477,16478,16479,16721,16722,16723,16725,16726,16727)}))
def enter():
    mon=reg('r5');ident=rd(mon+0x19,1)
    print('PIKE ENTRY id=%u hp=%u mode=%s'%(ident,rd(mon+0x10,2),pk_mode))
    if pk_mode=='win' and ident>=12:
        copies=[mon];client=mon-0xd98
        if all(rd(client+k)==rd(mon+k) for k in (8,12)): copies.append(client)
        for c in copies:
            wr(c+0x10,1)
            for slot in range(4):
                for off in (0x116,0x11c):
                    wr(c+off+slot*14,150);wr(c+off+slot*14+2,40,1)
        print('PIKE LAB rival HP1/Splash copies=%u'%len(copies))
''')
print(f"Hook({symbols['pike_pp']+32},pp)")
print(f"Hook({symbols['pike_iswin']},result)")
print(f"Hook({symbols['arena_enter']},enter)\nend")
