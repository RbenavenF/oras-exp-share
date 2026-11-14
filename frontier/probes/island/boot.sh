#!/usr/bin/env bash
# Install only this lane's prototype and a COPY of a lab save, then boot its one emulator.
set -euo pipefail
cd "$(dirname "$0")/../../.."
source scripts/env.sh
SAVE=${1:-work/frontier/pkg02/s1_story.sav}
LAB=work/azahar-lab
python - <<'PYHASH'
import hashlib,json
from pathlib import Path
p=Path('work/f11/prototype')
expected=json.loads((p/'hashes.json').read_text())
actual={str(f.relative_to(p/'mod')):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in (p/'mod').rglob('*') if f.is_file()}
assert actual==expected, 'Prototype changed: regenerate its manifest before boot'
PYHASH
python scripts/azahar_lab.py reap
python scripts/azahar_lab.py prepare
GDB_ENABLED=${F11_GDB:-1}
if [[ $GDB_ENABLED == 1 ]]; then STUB=true; else STUB=false; fi
python - "$LAB/config/azahar-emu/qt-config.ini" "$STUB" <<'PYCFG'
from pathlib import Path
import sys
p=Path(sys.argv[1])
lines=p.read_text().splitlines()
lines=[('use_gdbstub='+sys.argv[2]) if line.startswith('use_gdbstub=') else
       ('use_gdbstub'+chr(92)+'default=false') if line.startswith('use_gdbstub'+chr(92)+'default=') else line for line in lines]
p.write_text('\n'.join(lines)+'\n')
PYCFG
MOD=$LAB/data/azahar-emu/load/mods/000400000011C400
rm -rf "$MOD"
cp -r work/f11/prototype/mod "$MOD"
python - "$MOD" <<'PYHASH'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); out=Path('work/f11/prototype')
actual={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest()
        for f in p.rglob('*') if f.is_file()}
assert actual==json.loads((out/'hashes.json').read_text()), 'Installed mod differs'
(out/'installed-hashes.json').write_text(json.dumps(actual,indent=2)+'\n')
PYHASH
SAVEDIR="$LAB/data/azahar-emu/sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/0011c400/data/00000001"
mkdir -p "$SAVEDIR"
cp "$SAVE" "$SAVEDIR/main"
python scripts/azahar_lab.py start
if [[ $GDB_ENABLED == 1 ]]; then
    PORT=$(cat work/lab-port)
    for i in $(seq 1 60); do ss -ltn | rg -q ":$PORT " && break; sleep 1; done
    faraway/gdbctl.sh start
fi
sleep 25
for i in 1 2 3 4 5 6; do python scripts/azahar_lab.py input keydown a sleep 0.08 keyup a; sleep 3; done
sleep 6
python scripts/azahar_lab.py screenshot
