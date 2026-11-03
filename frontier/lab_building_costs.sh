#!/usr/bin/env bash
# Laboratory (reports/frontier.md §24): the island plaza's load budget with each catalogue building alone (with its
# door prop) at anchor (16,13), and with path only. No emulator: paints a copy of the base from
# frontier/lab_plaza_base.py with faraway/java/faraway/Plaza.java and keeps its "load budget" line.
# Output: work/frontier/survey/building_costs.txt, one line per building, then DONE.
set -uo pipefail
cd "$(dirname "$0")/.."; source scripts/env.sh >/dev/null 2>&1
OUT=work/frontier/survey/building_costs.txt; mkdir -p work/frontier/survey; : > $OUT
X=work/frontier/plaza-exp/cost
{ echo "-path only-"; grep -v '^#' tools/CTRMap-F5/src/ctrmap/resources/oras_buildings.tsv \
  | awk -F'\t' '$1=="HOUSE"||$1=="GYM"||$1=="OTHER"||$1=="POKECENTER"||$1=="MART"{print $2}'; } > $X.names
while IFS= read -r name; do
  rm -rf $X; mkdir -p $X; cp -r work/frontier/plaza-exp/base-game $X/game
  printf 'plaza.zone=209\nplaza.rect=1,0,39,38\nplaza.heightof=0\n' > $X/plan
  [ "$name" != "-path only-" ] && printf 'plaza.building.0=%s|16|13\n' "$name" >> $X/plan
  faraway/run.sh Plaza $X/game $X/ws $X/plan > $X/log 2>&1
  b=$(grep -o '^load budget [0-9]* bytes: world pack [0-9]*, prop pack [0-9]*, models [0-9]*' $X/log | tail -1)
  err=$(grep -m1 -o 'Exception[^|]*' $X/log | cut -c1-120)
  echo "$name | ${b:-FAILED $err}" >> $OUT
done < $X.names
echo DONE >> $OUT
