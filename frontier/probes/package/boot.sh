#!/usr/bin/env bash
# Lab only (F7-PAQUETE, reports/frontier.md §38): install the EXACT package folder (no loose builds) into this
# checkout's Azahar lab, check it against the package manifest, copy a lab save, boot with the GDB stub of the lane
# port and press A through the title. Usage: frontier/probes/package/boot.sh SAVE [PACKAGE_DIR]
set -euo pipefail
cd "$(dirname "$0")/../../.."; source scripts/env.sh >/dev/null 2>&1
SAVE=$1; PKG=${2:-dist/oras-frontier-alpha-v0.1}
LAB=work/azahar-lab; MOD=$LAB/data/azahar-emu/load/mods/000400000011C400
SAVEDIR="$LAB/data/azahar-emu/sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/0011c400/data/00000001"
faraway/gdbctl.sh stop >/dev/null 2>&1 || true   # stop() refuses lane PIDs (runtime path through a symlink): reap
python scripts/azahar_lab.py reap >/dev/null 2>&1 || true
python scripts/azahar_lab.py prepare
sed -i 's/^use_gdbstub=false/use_gdbstub=true/' $LAB/config/azahar-emu/qt-config.ini
rm -rf "$MOD"; cp -r "$PKG/luma/titles/000400000011C400" "$MOD"
python - "$PKG" "$MOD" <<'PY'
import hashlib, json, sys
from pathlib import Path
pkg, mod = Path(sys.argv[1]), Path(sys.argv[2])
files = {k.split('000400000011C400/', 1)[1]: v for k, v in json.loads((pkg / 'manifest.json').read_text())['files'].items()
         if k.startswith('luma/')}
got = {p.relative_to(mod).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in mod.rglob('*') if p.is_file()}
assert got == files, 'lab mod differs from the package manifest'
print(f'lab mod = package manifest ({len(files)} files)')
PY
mkdir -p "$SAVEDIR"; cp "$SAVE" "$SAVEDIR/main"; sha256sum "$SAVE"
python scripts/azahar_lab.py start
PORT=$(cat work/lab-port); for i in $(seq 1 60); do ss -ltn | grep -q ":$PORT " && break; sleep 1; done
faraway/gdbctl.sh start >/dev/null
sleep 25
for i in 1 2 3 4 5 6; do python scripts/azahar_lab.py input keydown a sleep 0.08 keyup a; sleep 3; done
sleep 6; python scripts/azahar_lab.py screenshot
