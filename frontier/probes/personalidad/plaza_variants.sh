#!/usr/bin/env bash
# F10-PERSONALIDAD-DISENO (reports/diseno/personalidad.md §3): the island plaza's load budget for exterior variants,
# no emulator. Paints copies of the plaza base (frontier/lab_plaza_base.py -> work/frontier/plaza-exp/base-game, or
# BASE) with faraway Plaza, as frontier/lab_building_costs.sh, and keeps each "load budget" line.
# The control must reproduce the build's 2665344 bytes (reports/frontier.md §24).
# Usage: frontier/probes/personalidad/plaza_variants.sh [BASE]   Output: work/frontier/personalidad/plaza_variants.txt
set -uo pipefail
cd "$(dirname "$0")/../../.."; source scripts/env.sh >/dev/null 2>&1
BASE=${1:-work/frontier/plaza-exp/base-game}
D=work/frontier/personalidad; OUT=$D/plaza_variants.txt; mkdir -p $D; : > $OUT
variant() {   # name, then plaza.building values (catalogue name|anchor x|anchor y)
  local name=$1; shift; local X=$D/v-$name; rm -rf $X; mkdir -p $X; cp -r "$BASE" $X/game
  { printf 'plaza.zone=209\nplaza.rect=1,0,39,38\nplaza.heightof=0\n'
    local i=0; for b in "$@"; do echo "plaza.building.$i=$b"; i=$((i+1)); done; } > $X/plan
  faraway/run.sh Plaza $X/game $X/ws $X/plan > $X/log 2>&1
  local b err; b=$(grep -o '^load budget [0-9]* bytes: world pack [0-9]*, prop pack [0-9]*, models [0-9]*' $X/log | tail -1)
  err=$(grep -m1 -o 'Exception[^|]*' $X/log | cut -c1-160)
  echo "$name | ${b:-FAILED $err}" >> $OUT; rm -rf $X/game $X/ws
}
# island_build.FACILITIES today: Tower, Dome, Factory, Pyramid, Pike, Arena, Palace
T="Rustboro flat-roof house|16|2"; DO="Fallarbor house|4|13"; F="Gym|16|13"; PY="Dewford shingle house|30|13"
PI="Route 124 treasure cabin|3|25"; AR="Battle Resort thatched house|17|25"; PA="Rustboro two-story house|28|25"
SEVEN=("$T" "$DO" "$F" "$PY" "$PI" "$AR" "$PA")
# one sign two tiles east and two south of each door (doors: reports/frontier.md §24, cell-local y = global y - 40)
SP=("Sign post|21|8" "Sign post|8|18" "Sign post|22|19" "Sign post|34|19" "Sign post|7|31" "Sign post|22|31" "Sign post|33|31")
RS=(); BB=(); for s in "${SP[@]}"; do RS+=("Route sign|${s#*|}"); BB+=("Billboard|${s#*|}"); done
FEN=("Iron fence (4-tile run)|15|25" "Iron fence (4-tile run)|25|25")          # Arena: both sides of its house
TFEN=("Iron fence (4-tile run)|14|2" "Iron fence (4-tile run)|24|2")           # Tower: both sides of its house
# replacements keep the door tile: anchor = door - the catalogue's doorDX/doorDY
PYW="Dewford wide house|29|13"; PYL="Lavaridge house|31|13"; PAG="Mossdeep gold-shingle house|28|25"
TAP="Rustboro apartment house|17|1"; FGW="Route 113 glass workshop|16|13"
variant control "${SEVEN[@]}"
variant signpost "${SEVEN[@]}" "${SP[@]}"
variant routesign "${SEVEN[@]}" "${RS[@]}"
variant billboard "${SEVEN[@]}" "${BB[@]}"
variant sp-arena-fences "${SEVEN[@]}" "${SP[@]}" "${FEN[@]}"
variant sp-arena-tower-fences "${SEVEN[@]}" "${SP[@]}" "${FEN[@]}" "${TFEN[@]}"
variant sp-pyramid-dewfordwide "$T" "$DO" "$F" "$PYW" "$PI" "$AR" "$PA" "${SP[@]}"
variant sp-pyramid-dewfordwide-arena-fences "$T" "$DO" "$F" "$PYW" "$PI" "$AR" "$PA" "${SP[@]}" "${FEN[@]}"
variant sp-pyramid-lavaridge "$T" "$DO" "$F" "$PYL" "$PI" "$AR" "$PA" "${SP[@]}"
variant sp-tower-apartment "$TAP" "$DO" "$F" "$PY" "$PI" "$AR" "$PA" "${SP[@]}"
variant sp-palace-gold "$T" "$DO" "$F" "$PY" "$PI" "$AR" "$PAG" "${SP[@]}"
variant sp-pike-tree "${SEVEN[@]}" "${SP[@]}" "Roadside tree|11|26"
variant sp-dome-bushes "${SEVEN[@]}" "${SP[@]}" "Bush|1|17" "Bush|10|17"
variant nosign-tower-apartment "$TAP" "$DO" "$F" "$PY" "$PI" "$AR" "$PA"
variant nosign-palace-gold "$T" "$DO" "$F" "$PY" "$PI" "$AR" "$PAG"
variant nosign-factory-glass "$T" "$DO" "$FGW" "$PY" "$PI" "$AR" "$PA"
variant swap-pyramid-palace "$T" "$DO" "$F" "$PYL" "$PI" "$AR" "$PAG"
variant sp-all-swaps "$TAP" "$DO" "$F" "$PYL" "$PI" "$AR" "$PAG" "${SP[@]}" "${FEN[@]}"
echo DONE >> $OUT
