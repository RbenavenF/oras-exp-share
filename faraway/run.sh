#!/usr/bin/env bash
# Compile the Faraway Island tools against a local CTRMap-F5 build and run one class.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CTRMAP="$ROOT/tools/CTRMap-F5"
CP="$CTRMAP/build/classes:$CTRMAP/lib/jogl-all.jar:$CTRMAP/lib/gluegen-rt.jar"
OUT="$ROOT/work/faraway/classes"
mkdir -p "$OUT"
javac --release 8 -nowarn -encoding UTF-8 -cp "$CP" -d "$OUT" $(find "$ROOT/faraway/java" -name '*.java')
main="$1"; shift
exec java -Xmx4g -Djava.awt.headless=true -cp "$OUT:$CP" "faraway.$main" "$@"
