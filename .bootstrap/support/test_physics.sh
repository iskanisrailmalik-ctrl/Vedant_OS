#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KOTLINC_BIN="${KOTLINC:-kotlinc}"
if ! command -v "$KOTLINC_BIN" >/dev/null 2>&1; then
  echo "ERROR: Kotlin compiler '"$KOTLINC_BIN"' not found. Install Kotlin or set KOTLINC to its executable." >&2
  exit 127
fi
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
"$KOTLINC_BIN" \
  "$ROOT/engine/physics/src/main/java/com/verdant/os/engine/physics/Pendulum.kt" \
  "$ROOT/scripts/PhysicsHarness.kt" \
  -include-runtime -d "$TMP_DIR/verdant-physics-harness.jar"
java -jar "$TMP_DIR/verdant-physics-harness.jar"
