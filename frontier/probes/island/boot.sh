#!/usr/bin/env bash
# Install only this lane's prototype and a COPY of a lab save, then boot its one emulator.
set -euo pipefail
cd "$(dirname "$0")/../../.."
source scripts/env.sh
SAVE=${1:-work/frontier/pkg02/s1_story.sav}
LAB=work/azahar-lab
python scripts/azahar_lab.py reap
python scripts/azahar_lab.py prepare
sed -i 's/^use_gdbstub=false/use_gdbstub=true/' "$LAB/config/azahar-emu/qt-config.ini"
MOD=$LAB/data/azahar-emu/load/mods/000400000011C400
rm -rf "$MOD"
cp -r work/f11/prototype/mod "$MOD"
SAVEDIR="$LAB/data/azahar-emu/sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/0011c400/data/00000001"
mkdir -p "$SAVEDIR"
cp "$SAVE" "$SAVEDIR/main"
python scripts/azahar_lab.py start
PORT=$(cat work/lab-port)
for i in $(seq 1 60); do ss -ltn | rg -q ":$PORT " && break; sleep 1; done
faraway/gdbctl.sh start
sleep 25
for i in 1 2 3 4 5 6; do python scripts/azahar_lab.py input keydown a sleep 0.08 keyup a; sleep 3; done
sleep 6
python scripts/azahar_lab.py screenshot
