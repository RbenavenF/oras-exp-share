#!/usr/bin/env bash
# Laboratory only: copy the built overlay and add a west-walking warp on Route 102 (zone 24, tile 123,133).
#   dev_overlay.sh ZONE WARP                 -> to an existing warp of ZONE
#   dev_overlay.sh ZONE new X Y HEIGHT       -> adds an arrival warp at (X,Y) in ZONE and goes there
# Never part of a release.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ZONE="$1"; WARP="${2:-0}"
DEV=work/faraway/dev
rm -rf "$DEV"; mkdir -p "$DEV"
cp -r work/faraway/build/game "$DEV/game"
if [ "$WARP" = new ]; then
  # Arrival pad: 1x1, leads back to Route 102 warp 0 only when walked into heading north (face 1).
  faraway/run.sh DevWarp "$DEV/game" "$DEV/ws0" "$ZONE" "$3" "$4" 1 1 24 0 "$5" 1 | tail -1
  WARP=$(faraway/run.sh Probe "$DEV/game" "$DEV/ws1" entities "$ZONE" | grep -c '^warp')
  WARP=$((WARP - 1))
fi
faraway/run.sh DevWarp "$DEV/game" "$DEV/ws" 24 123 133 1 1 "$ZONE" "$WARP" 2 3 | tail -1
cp -r work/faraway/build/overlay "$DEV/overlay"
cp "$DEV/game/a/0/1/3" "$DEV/overlay/romfs/a/0/1/3"
echo "$DEV/overlay -> zone $ZONE warp $WARP"
