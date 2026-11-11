#!/usr/bin/env bash
# Lab only: press keys (a=A s=B z=X x=Y t/g/f/h = up/down/left/right, m=START), then screenshot; NAME=x copies it to
# work/frontier/pkg/shots/x.png. HOLD and PAUSE in seconds.
cd "$(dirname "$0")/../../.."; source scripts/env.sh >/dev/null 2>&1
for k in "$@"; do python scripts/azahar_lab.py input keydown $k sleep ${HOLD:-0.08} keyup $k; sleep ${PAUSE:-1.2}; done
python scripts/azahar_lab.py screenshot >/dev/null
mkdir -p work/frontier/pkg/shots
[ -n "${NAME:-}" ] && cp work/azahar-lab/screen.png work/frontier/pkg/shots/$NAME.png || true
