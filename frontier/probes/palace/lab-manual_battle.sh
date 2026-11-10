#!/usr/bin/env bash
# Manual control: press A every 2.5 s (intro, Luchar, first move, texts) until the probe logs one more RESULT.
cd /home/rbenaven/projects/oras-exp-share; source scripts/env.sh >/dev/null 2>&1
LOG=work/faraway/gdb/out.log; n0=$(grep -c "PALACE RESULT" $LOG)
for i in $(seq 1 ${MAX:-60}); do
  [ "$(grep -c 'PALACE RESULT' $LOG)" -gt "$n0" ] && { grep "PALACE RESULT" $LOG | tail -1; exit 0; }
  python scripts/azahar_lab.py input keydown a sleep 0.08 keyup a; sleep 2.5
  [ "$i" = "${SHOT_AT:-8}" ] && { python scripts/azahar_lab.py screenshot >/dev/null; cp work/azahar-lab/screen.png work/frontier/palace/c/${NAME:-manual}-menu.png; }
done; echo "no result"; exit 1
