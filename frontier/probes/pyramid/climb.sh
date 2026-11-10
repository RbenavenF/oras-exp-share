#!/usr/bin/env bash
# Lab-only deterministic walk from FLOOR_ARRIVAL through each remaining floor.
# Use after loading lab_probe.py with pv_mode='win'. FIRST defaults to 1.
# SKIP0=1 starts at trainer 0 after verifying its saved defeated bit on floor 1.
set -euo pipefail
source scripts/env.sh
walk="python frontier/probes/pyramid/walk_to.py"
keys='bash frontier/probes/pyramid/keys.sh'
out=work/frontier/pyramid/v2
for floor in $(seq "${FIRST:-1}" 7); do
  echo "$(date +%T) FLOOR $floor"
  if [ "$floor" != 1 ] || [ "${SKIP0:-0}" = 0 ]; then
    $walk 12 11; $walk 8 11
    $keys t a
    bash frontier/probes/pyramid/fight.sh
  fi
  $walk 12 11; $keys t a
  bash frontier/probes/pyramid/fight.sh
  $walk 16 11; $keys t a
  bash frontier/probes/pyramid/fight.sh
  # Avoid the trainer at (12,10) while walking to the attendant at (12,6).
  $walk 14 11; $walk 14 7; $walk 12 7; $keys t a a a a
  sleep 3
  python scripts/azahar_lab.py screenshot >/dev/null
  cp work/azahar-lab/screen.png "$out/after-floor$floor.png"
  faraway/walk.sh pos
  faraway/gdbctl.sh halt >/dev/null
  faraway/gdbctl.sh cmd "python print('PYRAMID CLEARED $floor',state(pv_save))"
  faraway/gdbctl.sh run >/dev/null
 done
