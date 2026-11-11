#!/usr/bin/env bash
# Lab only: press KEY (default a) every STEP s (default 2.5) until the GDB log gains one more line matching PATTERN
# (e.g. "FRONT START", "FRONT RESULT"); prints that line. MAX presses (default 60). Screenshot at the end.
cd "$(dirname "$0")/../../.."; source scripts/env.sh >/dev/null 2>&1
PAT=$1; LOG=work/faraway/gdb/out.log; n0=$(grep -c "$PAT" $LOG)
for i in $(seq 1 ${MAX:-60}); do
  if [ "$(grep -c "$PAT" $LOG)" -gt "$n0" ]; then echo "after $i presses: $(grep "$PAT" $LOG | tail -1)"; ok=1; break; fi
  python scripts/azahar_lab.py input keydown ${KEY:-a} sleep 0.08 keyup ${KEY:-a}; sleep ${STEP:-2.5}
done
python scripts/azahar_lab.py screenshot >/dev/null; mkdir -p work/frontier/pkg/shots
[ -n "${NAME:-}" ] && cp work/azahar-lab/screen.png work/frontier/pkg/shots/$NAME.png
[ -n "${ok:-}" ] || { echo "no match after ${MAX:-60} presses"; exit 1; }
