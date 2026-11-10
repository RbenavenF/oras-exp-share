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
pk_wild=False
pk_rule=0
pk_setup=None
pk_pending=None
pk_results=0
def rd(a,n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a,n),'little')
def wr(a,v,n=2): gdb.selected_inferior().write_memory(a,v.to_bytes(n,'little'))
def reg(n): return int(gdb.parse_and_eval('$'+n))
class Hook(gdb.Breakpoint):
    def __init__(self, addr, fn, temporary=False):
        super().__init__('*%#x'%addr, temporary=temporary); self.fn=fn
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
    print('PIKE ENTRY id=%u hp=%u pp=%s mode=%s'%(ident,rd(mon+0x10,2),
          [rd(mon+0x118+14*k,1) for k in range(4)],pk_mode))
    if pk_mode=='win' and ident>=12:
        copies=[mon];client=mon-0xd98
        if all(rd(client+k)==rd(mon+k) for k in (8,12)): copies.append(client)
        for c in copies:
            wr(c+0x10,1)
            for slot in range(4):
                for off in (0x116,0x11c):
                    wr(c+off+slot*14,150);wr(c+off+slot*14+2,40,1)
        print('PIKE LAB rival HP1/Splash copies=%u'%len(copies))
def param():
    global pk_pending
    if 256<=reg('r6')<=258:
        pk_pending=(reg('r6'),reg('r7'))
        print('PIKE QUERY slot=%u selector=%u'%pk_pending)
def getter(selector):
    global pk_pending
    if pk_pending and pk_pending[1]==selector:
        pending=pk_pending;pk_pending=None
        Hook(reg('lr'),lambda: print('PIKE TRAIT slot=%u selector=%u value=%u'%(*pending,reg('r0'))),True)
def setup():
    global pk_setup
    w=reg('r4');b=w+0x620;pk_setup=b
    print('PIKE SETUP competitor=%u rule=%#x noexp=%u count=%u enemy=%u'%(
      rd(b,1),rd(b+0xa8),rd(b+0xb3,1),rd(rd(b+0x4c)+0x18,1),rd(rd(b+0x50)+0x18,1)))
    if pk_wild:
        wr(b,0,1);wr(b+0xb3,1,1);wr(rd(b+0x50)+0x18,1,1);wr(b+0xa8,pk_rule,4)
        print('PIKE LAB experimental wild: competitor0, noexp1, enemy count1, rule=%#x'%pk_rule)
''')
print(f"Hook({symbols['pike_pp']+32},pp)")
print(f"Hook({symbols['pike_iswin']},result)")
print(f"Hook({symbols['arena_enter']},enter)\nend")
print('python')
print(f"Hook({symbols['pike_param']},param)")
print('Hook(0x3b3b48,lambda: getter(6))\nHook(0x4d3204,lambda: getter(7))\nHook(0x4d1730,lambda: getter(22))')
print('Hook(0x1e33d8,setup)\nend')
