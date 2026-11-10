#!/usr/bin/env bash
# Lab driver: presses A only (a) outside battle (menus/texts) or (b) in battle when client 0 runs the UI proc of
# command 1 (intro text, CRO+0x73ec) or 12 (end text, CRO+0x10bec). Never during decisions. Every press is logged
# to $PRESSLOG with the reason. Stops when the probe has logged RESULTS results in total.
cd /home/rbenaven/projects/oras-exp-share; source scripts/env.sh >/dev/null 2>&1
LOG=work/faraway/gdb/out.log; G=faraway/gdbctl.sh; P=${PRESSLOG:-work/frontier/palace/c/presses.log}
CRO=$((0x6f3000))
for i in $(seq 1 ${MAX:-400}); do
  starts=$(grep -c "PALACE START" $LOG); results=$(grep -c "PALACE RESULT" $LOG)
  [ "$results" -ge "${RESULTS:?}" ] && { echo "results=$results"; exit 0; }
  $G halt >/dev/null 2>&1
  proc=$($G cmd "python print('PROC=%x' % (rd(CL[0]+0x1e0) if 0 in CL else 0))" | grep -o "PROC=[0-9a-f]*" | tail -1 | cut -d= -f2)
  $G run >/dev/null 2>&1
  inb=$([ $(grep -c "PALACE START" $LOG) -gt $results ] && [ "$(grep 'PALACE' $LOG | tail -1 | cut -c1-13)" != "PALACE RESULT" ] && echo 1 || echo 0)
  reason=""
  if [ "$inb" = 0 ]; then reason=menu
  elif [ "$proc" = "$(printf %x $((CRO+0x73ec)))" ]; then reason=intro-text
  elif [ "$proc" = "$(printf %x $((CRO+0x10bec)))" ]; then reason=end-text
  fi
  if [ -n "$reason" ]; then
    echo "$(date +%T) starts=$starts results=$results proc=$proc press A ($reason)" >> $P
    python scripts/azahar_lab.py input keydown a sleep 0.08 keyup a
  fi
  sleep ${STEP:-3}
done
echo "max reached"; exit 1
