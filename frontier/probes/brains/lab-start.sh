#!/usr/bin/env bash
# Brains lab (this lane only): installs v0.5 + BUILD, copies FIXTURE as the save, starts Azahar with the GDB stub on
# this lane's port (work/lab-port) and attaches gdb (faraway/gdbctl.sh) with the probe. Run from the lane root.
set -euo pipefail
source scripts/env.sh >/dev/null 2>&1
LAB=work/azahar-lab
BUILD=${BUILD:-work/frontier/brains/build}
MOD=$LAB/data/azahar-emu/load/mods/000400000011C400
SAVEDIR="$LAB/data/azahar-emu/sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/0011c400/data/00000001"
test ! -f "$LAB/session.json"
sed -i 's/^use_gdbstub=false/use_gdbstub=true/; s/^use_gdbstub\\default=true/use_gdbstub\\default=false/' "$LAB/config/azahar-emu/qt-config.ini"
rm -rf "$MOD"
cp -r dist/held-exp-share-v0.5/mods/000400000011C400 "$MOD"
cp -r "$BUILD/romfs/." "$MOD/romfs/"
cp "$BUILD/code.ips" "$MOD/code.ips"
mkdir -p "$SAVEDIR"
cp "${FIXTURE:?}" "$SAVEDIR/main"
python scripts/azahar_lab.py start
for i in $(seq 1 60); do ss -ltn | grep -q ":${ORAS_GDB_PORT:-$(cat work/lab-port)} " && break; sleep 1; done
faraway/gdbctl.sh start
faraway/gdbctl.sh halt
faraway/gdbctl.sh cmd "source ${PROBE:-frontier/probes/brains/probe.gdb}"
faraway/gdbctl.sh run
