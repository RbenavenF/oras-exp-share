#!/usr/bin/env bash
# Lab only; call inside the same persistent shell/PID namespace as Azahar.
# Press A until the GDB probe observes another IsWin, then close the field transition.
set -euo pipefail
source scripts/env.sh
log=work/faraway/gdb/out.log
initial=$(grep -c 'PYRAMID RESULT' "$log" || true)
for i in $(seq 1 110); do
  python scripts/azahar_lab.py input keydown a sleep 0.06 keyup a
  sleep 1
  if [ "$(grep -c 'PYRAMID RESULT' "$log" || true)" -gt "$initial" ]; then
    sleep 3
    python scripts/azahar_lab.py screenshot >/dev/null
    grep 'PYRAMID RESULT' "$log" | tail -1
    exit 0
  fi
done
python scripts/azahar_lab.py screenshot >/dev/null
echo 'No new IsWin in 110 presses' >&2
exit 1
