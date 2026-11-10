#!/usr/bin/env bash
set -euo pipefail
source scripts/env.sh
LAB=work/azahar-lab
MOD=$LAB/data/azahar-emu/load/mods/000400000011C400
SAVEDIR="$LAB/data/azahar-emu/sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/0011c400/data/00000001"
test ! -f "$LAB/session.json"
sed -i 's/^use_gdbstub=false/use_gdbstub=true/; s/^use_gdbstub\\default=true/use_gdbstub\\default=false/' "$LAB/config/azahar-emu/qt-config.ini"
rm -rf "$MOD"
cp -r dist/held-exp-share-v0.5/mods/000400000011C400 "$MOD"
cp -r work/frontier/palace/c-build3/romfs/. "$MOD/romfs/"
cp work/frontier/palace/c-build3/code.ips "$MOD/code.ips"
cp "${FIXTURE:?}" "$SAVEDIR/main"
python scripts/azahar_lab.py start
for i in $(seq 1 60); do
 if ss -ltn | grep -q 24689; then break; fi
 sleep 1
done
faraway/gdbctl.sh start
