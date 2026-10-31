#!/usr/bin/env bash
ORAS_PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ORAS_PROJECT
export GHIDRA_INSTALL_DIR="$ORAS_PROJECT/tools/ghidra_12.1.4_PUBLIC"
export JAVA_HOME="/usr/lib/jvm/java-21-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$ORAS_PROJECT/tools/bin:$ORAS_PROJECT/.venv/bin:$PATH"
