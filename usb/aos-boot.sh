#!/usr/bin/env bash
# Boot Pendrive-Native Agent OS (agent is the shell)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export ROBIN_USB_ROOT="$ROOT"
export ROBIN_AOS_MODE=1
export HOME="${HOME_OVERRIDE:-$ROOT/data/home}"
export PYTHONPATH="$ROOT/app:${PYTHONPATH:-}"

PY="$ROOT/runtime/venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3 || command -v python)"
fi

cd "$ROOT/app"
exec "$PY" -m aos.boot --root "$ROOT"
