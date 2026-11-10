#!/usr/bin/env bash
# k.sh KEY... : press each key (a=A s=B g=down f=left h=right t=up m=start), then screenshot to $NAME.png if set
cd /home/rbenaven/projects/oras-exp-share; source scripts/env.sh >/dev/null 2>&1
for k in "$@"; do python scripts/azahar_lab.py input keydown $k sleep ${HOLD:-0.08} keyup $k; sleep ${PAUSE:-1.2}; done
python scripts/azahar_lab.py screenshot >/dev/null
[ -n "${NAME:-}" ] && cp work/azahar-lab/screen.png work/frontier/palace/c/$NAME.png || true
