#!/usr/bin/env bash
# Robin Igris setup helper — Hermes brain + companion stage + voice bridge
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Robin Igris setup"
echo "Root: $ROOT"

if ! command -v hermes >/dev/null 2>&1; then
  echo "Hermes Agent not found. Install with:"
  echo "  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
else
  echo "✓ hermes: $(hermes --version 2>/dev/null || echo installed)"
fi

if [[ ! -f "$ROOT/.env" && -f "$ROOT/.env.example" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "✓ wrote .env from .env.example"
fi

if [[ -f "$HOME/.hermes" || -d "$HOME/.hermes" ]]; then
  if [[ -f "$ROOT/character/SOUL.md" ]]; then
    cp "$ROOT/character/SOUL.md" "$HOME/.hermes/SOUL.md"
    echo "✓ installed character/SOUL.md → ~/.hermes/SOUL.md"
  fi
fi

echo "==> Python voice bridge deps"
python3 -m pip install -r "$ROOT/requirements.txt"

echo "==> Companion (AIRI Live2D stage)"
(cd "$ROOT/companion" && npm install)

echo ""
echo "Next:"
echo "  1) hermes model && hermes config set API_SERVER_ENABLED true"
echo "  2) hermes config set API_SERVER_KEY robin-igris-dev"
echo "  3) hermes gateway"
echo "  4) python -m robin_igris.voice_server"
echo "  5) cd companion && npm run dev"
