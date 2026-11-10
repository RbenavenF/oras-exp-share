#!/usr/bin/env bash
# Laboratory input: explicit holds so a key survives one emulated frame.
set -euo pipefail
source scripts/env.sh
for key in "$@"; do
  python scripts/azahar_lab.py input keydown "$key" sleep 0.06 keyup "$key"
  sleep 1.5
done
