#!/usr/bin/env bash
# F11: stage checked retail files and measure with exactly Plaza's loadBudget.
set -euo pipefail
cd "$(dirname "$0")/../../.."
source scripts/env.sh
mkdir -p work/f11
python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, 'faraway')
import build
build.stage(Path('work/f11/retail'))
PY
faraway/run.sh Probe work/f11/retail/game work/f11/retail/ws zones > work/f11/retail/zones.txt
for z in 210 211 212 14 16 18; do
    faraway/run.sh WorldTextures work/f11/retail/game work/f11/retail/ws "$z" > "work/f11/retail/zone$z.txt"
done
CP=work/faraway/classes:tools/CTRMap-F5/build/classes:tools/CTRMap-F5/lib/jogl-all.jar:tools/CTRMap-F5/lib/gluegen-rt.jar
javac --release 8 -cp "$CP" -d work/faraway/classes frontier/probes/island/Materials.java
java -Xmx4g -Djava.awt.headless=true -cp "$CP" faraway.Materials work/f11/retail/game work/f11/retail/ws > work/f11/retail/materials.tsv
python - <<'PY' > work/f11/space.json
import sys,json
sys.path.insert(0,'frontier')
import modes_audit
print(json.dumps(modes_audit.measure_space(),indent=2))
PY
