#!/usr/bin/env bash
# One persistent shell for boot, GDB, input and stop. Only a disposable laboratory save is copied.
set -euo pipefail
source scripts/env.sh
lab=work/azahar-lab
mod=$lab/data/azahar-emu/load/mods/000400000011C400
savedir=$lab/data/azahar-emu/sdmc/Nintendo\ 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/0011c400/data/00000001
if [ -f "$lab/session.json" ]; then
  # This verifies namespace ownership before any attempt to signal a process.
  python scripts/azahar_lab.py stop
  faraway/gdbctl.sh stop >/dev/null 2>&1 || true
fi
sed -i 's/^use_gdbstub=false/use_gdbstub=true/; s/^use_gdbstub\\default=true/use_gdbstub\\default=false/' "$lab/config/azahar-emu/qt-config.ini"
rm -rf "$mod"
cp -r dist/held-exp-share-v0.5/mods/000400000011C400 "$mod"
cp -r work/frontier/pyramid/v2/build/romfs/. "$mod/romfs/"
cp work/frontier/pyramid/v2/build/code.ips "$mod/code.ips"
cp "$1" "$savedir/main"
LP_NUM_THREADS=1 python scripts/azahar_lab.py start
for i in $(seq 1 60); do
  if ss -ltn | rg -q 24689; then break; fi
  sleep 1
done
faraway/gdbctl.sh start
python frontier/probes/pyramid/lab_probe.py > work/frontier/pyramid/v2/probe.gdb
faraway/gdbctl.sh halt >/dev/null
faraway/gdbctl.sh cmd 'source work/frontier/pyramid/v2/probe.gdb'
faraway/gdbctl.sh run >/dev/null
sleep 10
for i in $(seq 1 6); do
  python scripts/azahar_lab.py input keydown a sleep 0.06 keyup a
  sleep 2
done
python scripts/azahar_lab.py screenshot
