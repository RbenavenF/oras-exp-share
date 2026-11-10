#!/usr/bin/env bash
# Press A every 2.5 s (menus, texts) until the probe logs a new PALACE START, then stop pressing (battle runs alone).
cd /home/rbenaven/projects/oras-exp-share; source scripts/env.sh >/dev/null 2>&1
LOG=work/faraway/gdb/out.log
n0=$(grep -c "PALACE START" $LOG)
for i in $(seq 1 ${MAX:-30}); do
  [ "$(grep -c 'PALACE START' $LOG)" -gt "$n0" ] && { echo "battle started after $i presses"; grep "PALACE START" $LOG | tail -1; exit 0; }
  python scripts/azahar_lab.py input keydown a sleep 0.08 keyup a; sleep 2.5
done
echo "no battle start"; exit 1
