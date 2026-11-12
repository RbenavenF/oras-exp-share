#!/usr/bin/env bash
# F10-PERSONALIDAD-DISENO (reports/diseno/personalidad.md): static survey of interior donors, no emulator.
# Floor map of every zone, then entities and load budget (faraway WorldTextures) of the candidates.
# Usage: frontier/probes/personalidad/survey.sh [GAME]   (default: the package's island build)
# Output: work/frontier/personalidad/{floors/floorN.txt,entities.txt,budgets.txt,floor_fit.txt}
set -uo pipefail
cd "$(dirname "$0")/../../.."; source scripts/env.sh >/dev/null 2>&1
GAME=$(realpath "${1:-work/frontier/package/build-island/game}")
D=$PWD/work/frontier/personalidad; mkdir -p $D/floors $D/ws
CANDIDATES="517 365 139 286 287 88 86 89 289 442 358 312 313 273 337 354 355 165 164 132 526 514 77 146 170 173 93 450"
faraway/run.sh Probe "$GAME" $D/ws zones > /dev/null 2>&1      # compiles the tools once
seq 0 535 | xargs -P6 -I{} sh -c "[ -s $D/floors/floor{}.txt ] || java -Xmx2g -Djava.awt.headless=true \
  -cp work/faraway/classes:tools/CTRMap-F5/build/classes:tools/CTRMap-F5/lib/jogl-all.jar:tools/CTRMap-F5/lib/gluegen-rt.jar \
  faraway.Probe '$GAME' $D/ws{} floor {} > $D/floors/floor{}.txt 2>/dev/null; rm -rf $D/ws{}"
faraway/run.sh Probe "$GAME" $D/ws entities $CANDIDATES > $D/entities.txt 2>/dev/null
: > $D/budgets.txt
for z in $CANDIDATES; do
  echo "== $z $(faraway/run.sh WorldTextures "$GAME" $D/ws $z 2>/dev/null | tr '\n' ' ')" >> $D/budgets.txt
done
python frontier/probes/personalidad/floor_fit.py $D/floors > $D/floor_fit.txt
rm -rf $D/ws
