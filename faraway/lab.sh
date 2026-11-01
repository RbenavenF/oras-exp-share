#!/usr/bin/env bash
# Laboratory only: reset the Azahar lab mod to dist v0.5 + the Faraway overlay, install a save copy, boot.
# Usage: faraway/lab.sh SAVE_FILE [OVERLAY_DIR]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source scripts/env.sh
SAVE="$1"; OVERLAY="${2:-work/faraway/build/overlay}"
LAB=work/azahar-lab
MOD=$LAB/data/azahar-emu/load/mods/000400000011C400
SAVEDIR="$LAB/data/azahar-emu/sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/0011c400/data/00000001"
if [ -f "$LAB/session.json" ]; then
  python scripts/azahar_lab.py stop
fi
rm -rf "$MOD"
cp -r dist/held-exp-share-v0.5/mods/000400000011C400 "$MOD"
cp -r "$OVERLAY"/romfs/. "$MOD"/romfs/
cp "$SAVE" "$SAVEDIR/main"
python scripts/azahar_lab.py start
sleep 40
for i in 1 2 3 4 5 6; do python scripts/azahar_lab.py input key --delay 100 a; sleep 3; done
sleep 8
python scripts/azahar_lab.py screenshot
