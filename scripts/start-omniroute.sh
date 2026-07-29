#!/usr/bin/env bash
# Start OmniRoute LLM gateway for Robin Igris / PNAOS
# https://github.com/diegosouzapw/OmniRoute
set -euo pipefail

PORT="${OMNIROUTE_PORT:-20128}"
export PORT
export NEXT_PUBLIC_BASE_URL="${NEXT_PUBLIC_BASE_URL:-http://127.0.0.1:${PORT}}"

echo "OmniRoute → http://127.0.0.1:${PORT}  (API ${PORT}/v1)"
echo "Dashboard: http://127.0.0.1:${PORT}"

if [[ -n "${OMNIROUTE_CMD:-}" ]]; then
  exec $OMNIROUTE_CMD
fi

if command -v omniroute >/dev/null 2>&1; then
  exec omniroute
fi

if command -v npx >/dev/null 2>&1; then
  exec npx -y omniroute
fi

if command -v docker >/dev/null 2>&1; then
  DATA="${ROBIN_USB_ROOT:-$PWD}/data/omniroute"
  mkdir -p "$DATA"
  exec docker run --rm --name robin-omniroute \
    -p "127.0.0.1:${PORT}:20128" \
    -v "$DATA:/app/data" \
    diegosouzapw/omniroute:latest
fi

echo "Install OmniRoute first:"
echo "  npm i -g omniroute"
echo "  # or: docker pull diegosouzapw/omniroute"
exit 1
