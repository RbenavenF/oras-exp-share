#!/usr/bin/env python3
"""Save this lane's game via its UI; copy and validate the resulting save under work/f11.

Usage: checkpoint.py NAME [ZONE=209]. No source save or RAM is written.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'frontier/probes/package'),str(ROOT/'faraway'),str(ROOT/'scripts')]
import circuit as c
import save_event as se
import save_fixture as sf


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name')
    parser.add_argument('zone', type=int, nargs='?', default=209)
    parser.add_argument('--ui-only', action='store_true', help='do not connect to GDB; validate a fresh UI save only')
    args=parser.parse_args()
    name=args.name
    if not name.replace('-','').replace('_','').isalnum():
        raise ValueError('simple checkpoint name required')
    zone=args.zone
    out=ROOT/'work/f11/prototype'/f'{name}.sav'
    if out.exists():
        raise FileExistsError(out)
    source=next((ROOT/'work/azahar-lab/data/azahar-emu/sdmc').glob('**/00000001/main'))
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    live=None if args.ui_only else c.pos()
    c.keys('z',pause=1.5)
    c.run('python','scripts/azahar_lab.py','input','mousemove','518','645','mousedown','1','sleep','.15','mouseup','1')
    time.sleep(2.5)
    c.keys('a',pause=6)
    c.keys('a',pause=2)
    c.run('python','scripts/azahar_lab.py','screenshot')
    data=source.read_bytes()
    assert hashlib.sha256(data).hexdigest()!=before,'UI did not save'
    facts=se.place(data)
    assert facts['zone']==zone,facts
    # Save stores the center coordinate (n+.5); c.pos reports n.
    if live is not None:
        assert (int(facts['tile_x']),int(facts['tile_y']))==live,(facts,live)
    sf.blocks(data)
    shutil.copyfile(source,out)
    shutil.copyfile(ROOT/'work/azahar-lab/screen.png',out.with_suffix('.png'))
    evidence=dict(file=str(out.relative_to(ROOT)),sha256=hashlib.sha256(data).hexdigest(),
                  live=list(live) if live is not None else None,place=facts,valid_blocks=len(sf.blocks(data)))
    out.with_suffix('.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence),flush=True)


if __name__=='__main__':
    main()
