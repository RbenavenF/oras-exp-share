#!/usr/bin/env python3
"""Lab-only Dome probe. Generate against the SAME checkout as the installed build.

The Dome has two entrants, so its client/server arrays are 2 * 0x488 apart.
Optional GDB command `python watergun()` changes move 1 of our first entrant
in battle RAM only (useful with the low-level fixture against Ghost/Flash Fire).
Neither helper writes the party in the save, results, streaks or BP.
"""
from pathlib import Path
import runpy


def script():
    shared = runpy.run_path(str(Path(__file__).parents[1] / 'pyramid/lab_probe.py'))
    probe = shared['script']().replace('PYRAMID', 'DOME ROOM')
    probe = probe.replace('client=mon-0xd98', 'client=mon-0x910')
    probe = probe.replace('16481,16482,16483,16686', '16473,16474,16475,16649,16650')
    return probe.replace('class Hook', '''def watergun():
    mon = [p for i,p in pv_entries if i == 0][-1]
    client = mon - 0x910
    assert all(rd(client+k) == rd(mon+k) for k in (8,12))
    for c in (mon,client):
        for off in (0x116,0x11c):
            wr(c+off,55); wr(c+off+2,25,1)
    print('DOME ROOM LAB Water Gun only battle copies', hex(mon))
class Hook''')


if __name__ == '__main__':
    print(script(), end='')
