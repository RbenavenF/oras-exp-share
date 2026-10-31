#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"

# Configuración separada de cualquier instalación personal de Azahar.
export XDG_CONFIG_HOME="$ORAS_PROJECT/work/xdg/config"
export XDG_DATA_HOME="$ORAS_PROJECT/work/xdg/data"
export XDG_CACHE_HOME="$ORAS_PROJECT/work/xdg/cache"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"

exec "$ORAS_PROJECT/tools/azahar.AppImage" "$@"
