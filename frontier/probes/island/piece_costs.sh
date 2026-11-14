#!/usr/bin/env bash
# F11-ISLA-TRAZADO laboratory only: load budget (reports/frontier.md §23) of the island of an alpha package with one
# catalogue piece stamped alone on the plaza, as frontier/lab_building_costs.sh does for buildings (§24). No emulator.
# Usage: frontier/probes/island/piece_costs.sh [PACKAGE]  -> work/f11/piece_costs.txt ("name | load budget ..."), then DONE
set -uo pipefail
cd "$(dirname "$0")/../.."; source scripts/env.sh >/dev/null 2>&1
PKG=${1:-dist/oras-frontier-alpha-v0.2}; OUT=work/f11/piece_costs.txt; X=work/f11/cost; : > $OUT
python - "$PKG" <<'PY'
import shutil, sys; from pathlib import Path
sys.path[:0] = ['frontier']
import island_build
pkg, base, out = Path(sys.argv[1]) / 'luma/titles/000400000011C400/romfs', Path('baseline/oras/repolished/romfs'), Path('work/f11/cost-base')
shutil.rmtree(out, ignore_errors=True)
for rel in island_build.STAGED:     # the package's archive, else Repolished's (as the package installs over it)
    (out / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pkg / rel if (pkg / rel).exists() else base / rel, out / rel)
(out / 'sound').mkdir(); (out / 'sound/sango_sound.bcsar').write_bytes(b'')
PY
PIECES=("-path only-" "Battle Resort tree (yashi_m)" "Palm tree" "Bush" "Roadside tree" "Littleroot Town tree (r103_happa)"
  "Battle Resort stairs (chip_steps01a) 2" "Battle Resort rock (r105_chip_rock_c) 3" "New Mauville fence (c107r0601_saku)"
  "Iron fence (4-tile run)" "Battle Resort decor (gaitou)" "Battle Resort decor (stone)" "Battle Resort structure (batres_vase06)")
for name in "${PIECES[@]}"; do
  rm -rf $X; mkdir -p $X; cp -r work/f11/cost-base $X/game
  printf 'plaza.zone=209\nplaza.rect=1,0,39,38\nplaza.heightof=0\n' > $X/plan
  [ "$name" != "-path only-" ] && printf 'plaza.building.0=%s|16|13\n' "$name" >> $X/plan
  faraway/run.sh Plaza $X/game $X/ws $X/plan > $X/log 2>&1
  b=$(grep -o '^load budget [0-9]* bytes: world pack [0-9]*, prop pack [0-9]*, models [0-9]*' $X/log | tail -1)
  err=$(grep -m1 -o 'Exception[^|]*' $X/log | cut -c1-160)
  echo "$name | ${b:-FAILED $err}" >> $OUT
done
echo DONE >> $OUT
