#!/usr/bin/env bash
# Launch Robin Igris from this USB kit (Linux / macOS / Git Bash)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export ROBIN_USB_ROOT="$ROOT"
export ROBIN_COMPANION_DIST="$ROOT/companion-dist"
export ROBIN_SERVE_COMPANION=1
export ROBIN_SYSTEM3_ROOT="$ROOT/data/system3"
export HOME="${HOME_OVERRIDE:-$ROOT/data/home}"
export XDG_CONFIG_HOME="$ROOT/data/xdg"

PY="$ROOT/runtime/venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3 || command -v python)"
fi

cd "$ROOT/app"
echo "Robin Igris — USB portable"
echo "Root: $ROOT"
echo "Opening display on this PC's browser…"
exec "$PY" -m robin_igris.portable_boot
