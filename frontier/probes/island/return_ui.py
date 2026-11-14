#!/usr/bin/env python3
"""F11 diagnostic: from a fresh boot of terrain-saved.sav (119,45), move west without GDB.

A successful fresh menu save west of x=99 proves movement across the observed stall.
A stale save is a failure, even if its checksums are valid. Run in boot.sh's live shell.
"""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'frontier/probes/package'))
import circuit as c


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name',help='new evidence basename under work/f11/prototype')
    args=parser.parse_args()
    # Input only: no c.pos(), c.walk(), debugger or writes to live coordinates.
    c.keys('f',hold='1.5',pause=2)
    print(c.run('python','frontier/probes/island/checkpoint.py',args.name,'--ui-only'),flush=True)
    facts=json.loads((ROOT/'work/f11/prototype'/f'{args.name}.json').read_text())['place']
    assert int(facts['tile_x'])<99, facts
    print('CROSSED_WEST_WITHOUT_GDB',facts,flush=True)


if __name__=='__main__':
    main()
