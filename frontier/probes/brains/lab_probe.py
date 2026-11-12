#!/usr/bin/env python3
"""Emit the Brains lab probe against current patch symbols.

Default passive. pv_mode='win'/'loss' assists only battle copies through the
existing Pyramid probe. It never writes results, works or the saved party.
COPY exports are captured before assistance, to check the actual rival PK6.
"""
from pathlib import Path
import argparse
import runpy


def script(directory='work/frontier/cerebros/base'):
    shared = runpy.run_path(str(Path(__file__).parents[1] / 'pyramid/lab_probe.py'))
    s = shared['script']().replace('PYRAMID', 'BRAINS')
    s = s.replace('16438,16441,16442,16443,16481,16482,16483,16686',
                  '16438,16437,16489,16485,16486,16487,16490,16433,16434,16435,16441,16442,16443,16461,16462,16465,16466,16473,16474,16477,16478,16481,16482,16729,16730')
    s = s.replace('client=mon-0xd98', 'client=mon-(0x910 if pv_save and state(pv_save).get(16438)==5 else 0xd98)')
    s = s.replace("state=%s mode=%s'%(rd(w+0x6c8),state(save),pv_mode)",
                  "trainer=%u state=%s mode=%s'%(rd(w+0x6c8),rd(w+4),state(save),pv_mode)")
    s += '''python
from pathlib import Path
brain_copy = False
brain_copies = 0
def copy_start():
    global brain_copy
    # code.bin callers are below 0x600000; our CRO is above it.
    brain_copy = reg('lr') > 0x600000
    if brain_copy:
        print('BRAINS COPY src=%x dst=%x lr=%x'%(reg('r1'),reg('r0'),reg('lr')))
def copy_export():
    global brain_copy, brain_copies
    if not brain_copy: return
    brain_copy = False
    brain_copies += 1
    buf = rd(0x3b246c)
    p = Path('work/frontier/cerebros/base') / ('rival-%02u.pk6'%brain_copies)
    p.write_bytes(bytes(gdb.selected_inferior().read_memory(buf,260)))
    print('BRAINS EXPORTED',p)
Hook(0x3b2444,copy_start)
Hook(0x3b245c,copy_export)
end
'''
    return s.replace("Path('work/frontier/cerebros/base')", f'Path({directory!r})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', default='work/frontier/cerebros/base')
    print(script(parser.parse_args().directory), end='')
