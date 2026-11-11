#!/usr/bin/env bash
# Lab driver (lane-relative): presses A only (a) outside battle or (b) when client 0 runs the UI proc of command 1
# (intro text, CRO+0x73ec) or 12 (end text, CRO+0x10bec). Never during decisions. Logs every press to $PRESSLOG.
# Stops when the probe has logged RESULTS «PALACE MOVE»-free battle ends (ISWIN lines after a START) in total.
source scripts/env.sh >/dev/null 2>&1
LOG=work/faraway/gdb/out.log; G=faraway/gdbctl.sh; P=${PRESSLOG:-work/frontier/palace/c/presses.log}
for i in $(seq 1 ${MAX:-400}); do
  starts=$(grep -c "PALACE START" $LOG); ends=$(grep -c "PALACE ISWIN raw=1\|PALACE ISWIN raw=0\|PALACE ISWIN raw=2" $LOG)
  [ -n "${UNTIL:-}" ] && grep -q "$UNTIL" $LOG && { echo "until matched"; exit 0; }
  [ -n "${RESULTS:-}" ] && [ "$(grep -c "PALACE ISWIN" $LOG)" -ge "$RESULTS" ] && { echo "results reached"; exit 0; }
  out=$($G halt >/dev/null 2>&1; $G cmd "python print('PROC=%x BASE=%x' % (rd(CL[0]+0x1e0) if 0 in CL else 0, CUR.get('base', 0)))")
  $G run >/dev/null 2>&1
  proc=$(echo "$out" | grep -o "PROC=[0-9a-f]*" | tail -1 | cut -d= -f2)
  base=$((16#$(echo "$out" | grep -o "BASE=[0-9a-f]*" | tail -1 | cut -d= -f2)))
  last=$(grep -E "PALACE (START|ISWIN)" $LOG | tail -1 | cut -c1-12)
  reason=""
  if [ "$starts" = 0 ] || [ "$last" = "PALACE ISWIN" ]; then reason=menu
  elif [ "$proc" = "$(printf %x $((base+0x73ec)))" ]; then reason=intro-text
  elif [ "$proc" = "$(printf %x $((base+0x10bec)))" ]; then reason=end-text
  fi
  if [ -n "$reason" ]; then
    echo "$(date +%T) starts=$starts proc=$proc press A ($reason)" >> $P
    python scripts/azahar_lab.py input keydown a sleep 0.08 keyup a
  fi
  sleep ${STEP:-3}
done
echo "max reached"; exit 1
