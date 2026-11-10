#!/usr/bin/env bash
# From c1-door.sav loaded at the title: into the game, through the Palace door, to the receptionist's menu.
cd /home/rbenaven/projects/oras-exp-share; source scripts/env.sh >/dev/null 2>&1
K=work/frontier/palace/k.sh
PAUSE=3 $K m a; sleep 6; PAUSE=1 $K a
HOLD=0.3 PAUSE=4 $K t
faraway/walk.sh pos
HOLD=0.04 faraway/walk.sh t 6; HOLD=0.04 faraway/walk.sh h 3
python scripts/azahar_lab.py input keydown t sleep 0.04 keyup t; sleep 0.5
python - <<'PY'
import sys,time; sys.path.insert(0,'frontier')
import lab_factory as lf
for attempt in range(20):
    img=lf.shot()
    if lf.menu_open(img): break
    lf.key('a'); time.sleep(2.5)
print('menu after',attempt)
PY
