#!/usr/bin/env bash
# Save through the game's UI from the field with all dialogues closed.
# Inspect the screenshot and snapshot: a dialogue can otherwise swallow X.
set -euo pipefail
source scripts/env.sh
main=(work/azahar-lab/data/azahar-emu/sdmc/*/*/*/title/00040000/0011c400/data/00000001/main)
before=$(sha256sum "${main[0]}")
bash frontier/probes/pyramid/keys.sh z
python scripts/azahar_lab.py input mousemove 518 645 mousedown 1 sleep 0.15 mouseup 1
sleep 2.5
bash frontier/probes/pyramid/keys.sh a
sleep 6
bash frontier/probes/pyramid/keys.sh a
python scripts/azahar_lab.py screenshot >/dev/null
cp work/azahar-lab/screen.png "work/frontier/pyramid/v2/$1.png"
if [ "$before" = "$(sha256sum "${main[0]}")" ]; then
  echo 'Laboratory save unchanged: inspect dialogue/menu before accepting evidence' >&2
  exit 1
fi
python frontier/probes/pyramid/snapshot.py "$1"
