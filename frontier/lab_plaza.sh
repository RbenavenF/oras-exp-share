#!/usr/bin/env bash
# Laboratory only (reports/frontier.md §21): frontier/lab_plaza.sh NAME PLAN|-
# Paints PLAN (plaza.* keys, faraway/java/faraway/Plaza.java; - paints nothing) on a copy of the base from
# frontier/lab_plaza_base.py, boots Azahar with it and work/frontier/lab/f6f_saved_pier.sav (a save on the island
# pier) and prints the top screen's brightness: 0 is the black screen of a hang. Needs work/frontier/build and the
# dev overlay (faraway/dev_overlay.sh).
set -uo pipefail
cd "$(dirname "$0")/..";  source scripts/env.sh >/dev/null 2>&1
N=$1; P=$2; X=work/frontier/plaza-exp/$N
rm -rf $X; mkdir -p $X; cp -r work/frontier/plaza-exp/base-game $X/game
if [ "$P" != "-" ]; then faraway/run.sh Plaza $X/game $X/ws $P > $X/java.log 2>&1 || { echo "Plaza failed"; tail -5 $X/java.log; exit 1; }; grep -o "Painted map applied[^|]*" $X/java.log; fi
rm -rf work/frontier/labroot && mkdir -p work/frontier/labroot && cp -r work/faraway/dev/overlay/romfs work/frontier/labroot/ && cp -r work/frontier/build/romfs/. work/frontier/labroot/romfs/
for f in a/0/1/3 a/0/1/4 a/0/3/9 a/0/4/0 a/1/3/7; do cp $X/game/$f work/frontier/labroot/romfs/$f; done
python scripts/azahar_lab.py stop >/dev/null 2>&1; ps -eo pid,args | grep "[A]ppRun.wrapped" | awk '{print $1}' | xargs -r kill -9
CODE_IPS=work/frontier/build/code.ips faraway/lab.sh work/frontier/lab/f6f_saved_pier.sav work/frontier/labroot > $X/lab.log 2>&1
sleep 5; python scripts/azahar_lab.py screenshot >/dev/null; cp work/azahar-lab/screen.png work/frontier/lab/f6g_$N.png
python - "$N" <<'PY'
import sys; sys.path.insert(0, 'frontier')
from lab_factory import Png
img = Png(f'work/frontier/lab/f6g_{sys.argv[1]}.png'); tot = n = 0
for y in range(240, 460, 20):
    r = img.row(y)
    for x in range(410, 790, 20):
        tot += sum(r[x*img.bpp:x*img.bpp+3]); n += 3
print(sys.argv[1], 'top-screen brightness', round(tot / n, 1))
PY
