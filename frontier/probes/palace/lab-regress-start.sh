#!/usr/bin/env bash
# regress-start.sh SAVE : (re)start the lab with c-build3 and a COPY of SAVE, passive probe, title -> game.
set -e
cd /home/rbenaven/projects/oras-exp-share; source scripts/env.sh >/dev/null 2>&1
G=faraway/gdbctl.sh
if [ -f work/azahar-lab/session.json ]; then $G stop || true; python scripts/azahar_lab.py stop; sleep 2; fi
cp "$1" work/frontier/palace/c/fixture-copy.sav
FIXTURE=work/frontier/palace/c/fixture-copy.sav timeout 120 work/frontier/palace/c-lab-start3.sh >/dev/null 2>&1
sleep 2; $G halt >/dev/null; $G cmd "source work/frontier/palace/c-probe2.gdb" >/dev/null; $G run >/dev/null
sleep 20; K=work/frontier/palace/k.sh; PAUSE=3 $K m a; sleep 6; PAUSE=1 $K a
faraway/walk.sh pos
