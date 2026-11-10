#!/usr/bin/env bash
# Two Azahar labs at once, one per frontier-orch lane: boot both, attach GDB to each port, read a register from
# each, then check that `reap` in one lane leaves the other running. Run from the main checkout with the lanes set
# up (frontier-orch lanes setup) and nothing else using the labs.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT/scripts/env.sh" >/dev/null 2>&1
LANES=("$ROOT/work/orch/lanes/claude" "$ROOT/work/orch/lanes/codex")
for lane in "${LANES[@]}"; do
  test -f "$lane/work/lab-port" || { echo "no lane at $lane: run frontier-orch lanes setup"; exit 1; }
  test ! -f "$lane/work/azahar-lab/session.json" || { echo "$lane has a lab session; stop it first"; exit 1; }
done
for lane in "${LANES[@]}"; do
  port=$(cat "$lane/work/lab-port")
  sed -i 's/^use_gdbstub=false/use_gdbstub=true/; s/^use_gdbstub\\default=true/use_gdbstub\\default=false/' \
    "$lane/work/azahar-lab/config/azahar-emu/qt-config.ini"
  (cd "$lane" && python scripts/azahar_lab.py start >/dev/null)
  for i in $(seq 1 90); do ss -ltn | grep -q ":$port " && break; sleep 1; done
  ss -ltn | grep -q ":$port " || { echo "FAIL: lab of $lane does not listen on $port"; exit 1; }
  echo "lab $(basename "$lane") listening on $port"
done
for lane in "${LANES[@]}"; do
  (cd "$lane" && faraway/gdbctl.sh start >/dev/null && faraway/gdbctl.sh halt >/dev/null &&
   echo "$(basename "$lane") pc: $(faraway/gdbctl.sh cmd 'p/x $pc' | grep -o '0x[0-9a-f]*' | tail -1)" &&
   faraway/gdbctl.sh run)
done
(cd "${LANES[0]}" && python scripts/azahar_lab.py reap)
sleep 2
other=$(cat "${LANES[1]}/work/lab-port")
if ss -ltn | grep -q ":$other "; then echo "OK: reap of $(basename "${LANES[0]}") left the other lab running"
else echo "FAIL: the other lab died with the first one's reap"; fi
(cd "${LANES[1]}" && python scripts/azahar_lab.py reap)
sleep 1
ps -eo pid,args | grep -E '[o]rch/lanes/.*(AppRun|Xvfb|azahar-lab)' && echo "FAIL: lane processes left" || echo "OK: both labs gone"
