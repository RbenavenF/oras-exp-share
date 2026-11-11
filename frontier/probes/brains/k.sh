#!/usr/bin/env bash
# k.sh KEY... : press each key (a=A s=B g=down f=left h=right t=up m=start), then screenshot to $NAME.png if set.
# Lane-relative (run from the lane root).
source scripts/env.sh >/dev/null 2>&1
for k in "$@"; do python scripts/azahar_lab.py input keydown $k sleep ${HOLD:-0.08} keyup $k; sleep ${PAUSE:-1.2}; done
python scripts/azahar_lab.py screenshot >/dev/null
[ -n "${NAME:-}" ] && mkdir -p ${SHOTS:-work/frontier/brains}; cp work/azahar-lab/screen.png ${SHOTS:-work/frontier/brains}/$NAME.png || true
