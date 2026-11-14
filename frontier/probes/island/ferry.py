#!/usr/bin/env python3
"""F11 disposable lab: re-enter harbor, save checkpoint via UI, take ferry, assert new arrival.

Run in the same shell as boot.sh, starting in Calagua harbor (317). An edited
Situation save needs an exit/re-entry to instantiate harbor actors.
"""
from pathlib import Path
import argparse
import hashlib
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'frontier/probes/package'))
import circuit as c
sys.path.insert(0,str(ROOT/'faraway'))
import save_event as se

OUT=ROOT/'work/f11/prototype'
c.SHOTS=OUT/'shots'
c.LOG=OUT/'ferry-steps.log'
c.SHOTS.mkdir(exist_ok=True)


def save_checkpoint():
    main=next((ROOT/'work/azahar-lab/data/azahar-emu/sdmc').glob('**/00000001/main'))
    before=hashlib.sha256(main.read_bytes()).hexdigest()
    c.keys('z',pause=1.5)
    c.run('python','scripts/azahar_lab.py','input','mousemove','518','645','mousedown','1','sleep','.15','mouseup','1')
    time.sleep(2.5)
    c.keys('a',pause=6)
    c.keys('a',pause=2)
    c.shot('harbor_saved')
    assert hashlib.sha256(main.read_bytes()).hexdigest()!=before,'UI did not save'
    assert se.place(main.read_bytes())['zone']==317
    shutil.copyfile(main,OUT/'harbor-checkpoint.sav')
    print('HARBOR SAVE',se.place(main.read_bytes()),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--at-clerk',action='store_true',help='use the real harbor-checkpoint.sav at (19,25)')
    args=parser.parse_args()
    c.log(f'boot harbor at {c.pos()}')
    if args.at_clerk:
        assert c.pos()==(19,25),'Expected real saved harbor checkpoint'
    else:
        c.walk((26,26),(26,29))
        c.keys('g',hold='.18',pause=8)
        c.log(f'city at {c.pos()}')
        c.keys('t',hold='.18',pause=8)
        c.log(f'harbor reentered at {c.pos()}')
        x,y=c.pos()
        c.walk((x,26),(19,26),(19,25))
        save_checkpoint()
    c.keys('f','a',pause=2.5)
    c.keys('a','a','a',pause=2.5)
    c.shot('menu')
    c.keys('g','g',hold='.06',pause=.8)
    c.keys('a','a',pause=2.5)
    c.shot('yesno')
    c.keys('a',pause=15)
    print(c.run('python','frontier/probes/package/to_field.py','--max','12'),flush=True)
    at=c.pos()
    c.log(f'FERRY ARRIVAL {at}')
    c.shot('arrival')
    assert at==(35,71),f'Not at new pier: {at}'


if __name__=='__main__':
    main()
