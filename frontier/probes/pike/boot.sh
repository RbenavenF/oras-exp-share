#!/usr/bin/env bash
# Run in one persistent shell, including shutdown. Copies only a disposable lab save.
set -euo pipefail
source scripts/env.sh
build=${PIKE_BUILD:-work/frontier/pike/v2/build-immune}
python - "$build/code.ips" <<'PY'
import sys
from pathlib import Path
sys.path[:0] = ['frontier', 'scripts']
import patch
from formats import apply_ips, read_ips
from island_build import native_donors
installed = apply_ips(patch.CLEAN.read_bytes(), read_ips(Path(sys.argv[1]).read_bytes()))
assert installed == patch.build(native_donors())[0], 'Rebuild first: probe symbols do not match installed code'
PY
lab=work/azahar-lab
mod=$lab/data/azahar-emu/load/mods/000400000011C400
savedir="$lab/data/azahar-emu/sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/0011c400/data/00000001"
if [ -f "$lab/session.json" ]; then
  python scripts/azahar_lab.py stop
  faraway/gdbctl.sh stop >/dev/null 2>&1 || true
fi
sed -i 's/^use_gdbstub=false/use_gdbstub=true/; s/^use_gdbstub\\default=true/use_gdbstub\\default=false/' "$lab/config/azahar-emu/qt-config.ini"
rm -rf "$mod"
cp -r dist/held-exp-share-v0.5/mods/000400000011C400 "$mod"
cp -r "$build/romfs/." "$mod/romfs/"
cp "$build/code.ips" "$mod/code.ips"
cp "$1" "$savedir/main"
LP_NUM_THREADS=1 python scripts/azahar_lab.py start
for i in $(seq 1 60); do
  if ss -ltn | rg -q 24689; then break; fi
  sleep 1
done
faraway/gdbctl.sh start
python frontier/probes/pike/lab_probe.py > work/frontier/pike/v2/probe.gdb
faraway/gdbctl.sh halt >/dev/null
faraway/gdbctl.sh cmd 'source work/frontier/pike/v2/probe.gdb'
faraway/gdbctl.sh run >/dev/null
sleep 10
for i in $(seq 1 6); do
  python scripts/azahar_lab.py input keydown a sleep 0.06 keyup a
  sleep 2
done
python scripts/azahar_lab.py screenshot
