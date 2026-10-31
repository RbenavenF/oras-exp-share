#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
export XDG_CONFIG_HOME="$ORAS_PROJECT/work/ghidra-config"
export XDG_CACHE_HOME="$ORAS_PROJECT/work/ghidra-cache"
export GHIDRA_HEADLESS_MAXMEM=4G
mkdir -p "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$ORAS_PROJECT/work/ghidra-projects"
exec "$GHIDRA_INSTALL_DIR/support/analyzeHeadless" "$@"
