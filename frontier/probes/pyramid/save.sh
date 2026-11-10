#!/usr/bin/env bash
# Save through the game's UI, then copy only the disposable laboratory save.
set -euo pipefail
source scripts/env.sh
bash frontier/probes/pyramid/keys.sh z
python scripts/azahar_lab.py input mousemove 518 645 mousedown 1 sleep 0.15 mouseup 1
sleep 2.5
bash frontier/probes/pyramid/keys.sh a
sleep 6
bash frontier/probes/pyramid/keys.sh a
python scripts/azahar_lab.py screenshot >/dev/null
cp work/azahar-lab/screen.png "work/frontier/pyramid/v2/$1.png"
python frontier/probes/pyramid/snapshot.py "$1"
