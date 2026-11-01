#!/usr/bin/env bash
# Laboratory: tap the D-pad N times (one tile each) and print the player's tile from RAM.
# Usage: walk.sh DIR COUNT   (DIR: t up, g down, f left, h right)   or   walk.sh pos
set -euo pipefail
cd /home/rbenaven/projects/oras-exp-share
source scripts/env.sh
POS=${FARAWAY_POS_ADDR:-0x8187bf4}
pos() {
  faraway/gdbctl.sh halt >/dev/null 2>&1
  faraway/gdbctl.sh cmd "x/3fw $POS" | grep "^0x" | awk '{printf "tile x=%.2f y=%.2f height=%s\n", ($2-9)/18, ($4-9)/18, $3}'
  faraway/gdbctl.sh run
}
if [ "$1" = pos ]; then pos; exit; fi
for i in $(seq 1 "$2"); do
  python scripts/azahar_lab.py input keydown "$1" sleep "${HOLD:-0.06}" keyup "$1"; sleep 0.45
done
sleep 0.4
pos
