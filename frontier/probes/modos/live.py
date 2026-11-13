#!/usr/bin/env python3
"""Emit a passive GDB probe for F9's selector/selection/persistence measurements.

Run from the lane root. Optional argv[1] is the JSON from persistence.py seed.
Load the emitted file while GDB is halted, then continue. No RAM writes.
The first configuration resolves DllField from LR; later callbacks include cancel.
Only the unmodified alpha-v0.2 package is measured so far (reports/modos-base.md).
"""
import json
from pathlib import Path
import sys


def script(expected):
    return '''set pagination off
set language c
python
import gdb, json, struct
expected = EXPECTED
mode_work = mode_save = field_base = 0
def reg(n): return int(gdb.parse_and_eval('$'+n))
def rd(a, n=4): return int.from_bytes(gdb.selected_inferior().read_memory(a,n),'little')
def snapshot():
    values = {w:rd(mode_save+0x13144+2*(w-0x4000),2) for w in expected}
    wrong = {w:(v,expected[w]) for w,v in values.items() if v != expected[w]}
    print('MODES WORKS',json.dumps(values,sort_keys=True),'mismatch',wrong)
    return values
class Hook(gdb.Breakpoint):
    def __init__(self, a, fn):
        self.fn = fn
        super().__init__('*'+hex(a),internal=True)
    def stop(self):
        try: self.fn()
        except Exception as e: print('MODES PROBE ERROR',e)
        return False
def packet(app):
    print('MODES PACKET',bytes(gdb.selected_inferior().read_memory(app,20)).hex())
def configure():
    global mode_work, mode_save, field_base
    mode_work = reg('r0')
    mode_save = rd(rd(rd(mode_work+0xb78)+0x1c))
    print('MODES CONFIG w=%x r1=%u type=%u init=%u lr=%x' %
          (mode_work,reg('r1'),reg('r2'),reg('r3'),reg('lr')))
    # Only the selector's measured call site has a packet in r5.
    candidate = reg('lr')-0x96b50
    if rd(candidate+0x96b00) == 0xe92d41f0:
        packet(reg('r5'))
        if not field_base:
            field_base = candidate
            Hook(field_base+0x96b00,lambda: packet(rd(reg('r0')+4)))
            print('MODES FIELD_BASE',hex(field_base))
    snapshot()
def configured():
    print('MODES CONFIGURED rank=%u type=%u selector=%u count=%u' %
          (rd(mode_work+0x838,1),rd(mode_work+0x839,1),rd(mode_work+0x83a,1),rd(mode_work+0x48)))
def build_party():
    global mode_work, mode_save
    mode_work = reg('r0')
    mode_save = rd(rd(rd(mode_work+0xb78)+0x1c))
    selection = reg('r2'); count = rd(selection+0x1c)
    print('MODES BUILD w=%x box=%u count=%u indices=%s rank=%u type=%u' %
          (mode_work,rd(selection,1),count,[rd(selection+4+4*i) for i in range(min(count,6))],
           rd(mode_work+0x838,1),rd(mode_work+0x839,1)))
    print('MODES WORK_SELECTION count=%u indices=%s' %
          (rd(mode_work+0x48),[rd(mode_work+0x30+4*i) for i in range(4)]))
    snapshot()
def workset():
    if 0x800c <= reg('r1') <= 0x800e:
        print('MODES OUT',hex(reg('r1')),reg('r2'))
Hook(0x1e5684,configure)
Hook(0x1e56f8,configured)
Hook(0x1e3d2c,build_party)
Hook(0x3fe1c4,workset)
print('MODES PROBE READY')
end
'''.replace('EXPECTED', repr(expected))


if __name__ == '__main__':
    expected = ({int(k):v for k,v in json.loads(Path(sys.argv[1]).read_text())['expected'].items()}
                if len(sys.argv) > 1 else {})
    print(script(expected), end='')
