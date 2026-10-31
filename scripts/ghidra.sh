#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
exec "$GHIDRA_INSTALL_DIR/ghidraRun" "$@"
