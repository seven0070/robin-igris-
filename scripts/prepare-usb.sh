#!/usr/bin/env bash
# Prepare a 128GB USB folder with a self-contained Robin Igris kit.
# Usage: ./scripts/prepare-usb.sh /path/to/USB/ROBIN_IGRIS
set -euo pipefail

ROOT_REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-}"
if [[ -z "$DEST" ]]; then
  echo "Usage: $0 /path/to/USB/ROBIN_IGRIS"
  exit 1
fi

mkdir -p "$DEST"/{app,data/{home,system3,logs,xdg},runtime,companion-dist}
touch "$DEST/.robin_usb"

echo "==> Copying app"
USE_RSYNC=0
if type rsync >/dev/null 2>&1; then USE_RSYNC=1; fi
if [[ "$USE_RSYNC" == "1" ]]; then
  rsync -a --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude 'node_modules' \
    --exclude 'companion/node_modules' \
    --exclude 'companion/dist' \
    --exclude 'companion/.cache' \
    --exclude 'companion/public/assets' \
    --exclude 'data' \
    --exclude '__pycache__' \
    --exclude '.pytest_cache' \
    "$ROOT_REPO/" "$DEST/app/"
else
  rm -rf "$DEST/app"
  mkdir -p "$DEST/app"
  cp -a "$ROOT_REPO/." "$DEST/app/"
  rm -rf "$DEST/app/.git" "$DEST/app/.venv" \
    "$DEST/app/companion/node_modules" "$DEST/app/companion/dist" \
    "$DEST/app/companion/.cache" "$DEST/app/data" \
    "$DEST/app/node_modules" 2>/dev/null || true
  find "$DEST/app" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
fi

echo "==> Building companion (AIRI Live2D) for USB display"
(
  cd "$ROOT_REPO/companion"
  npm install
  VITE_HERMES_BASE_URL=/hermes/v1 \
  VITE_VOICE_BASE_URL= \
  VITE_AGENT_NAME="Robin Igris" \
  npm run build
  if command -v rsync >/dev/null 2>&1; then
    rsync -a dist/ "$DEST/companion-dist/"
    if [[ -d public/assets ]]; then
      mkdir -p "$DEST/companion-dist/assets"
      rsync -a public/assets/ "$DEST/companion-dist/assets/"
    fi
  else
    rm -rf "$DEST/companion-dist"
    mkdir -p "$DEST/companion-dist"
    cp -a dist/. "$DEST/companion-dist/"
    if [[ -d public/assets ]]; then
      mkdir -p "$DEST/companion-dist/assets"
      cp -a public/assets/. "$DEST/companion-dist/assets/"
    fi
  fi
)

echo "==> Creating portable venv on the stick"
python3 -m venv "$DEST/runtime/venv"
# shellcheck disable=SC1091
source "$DEST/runtime/venv/bin/activate"
pip install -q -U pip
pip install -q -r "$DEST/app/requirements.txt"

echo "==> USB launchers + env"
cp "$ROOT_REPO/usb/launch.sh" "$DEST/launch.sh"
cp "$ROOT_REPO/usb/stop.sh" "$DEST/stop.sh"
cp "$ROOT_REPO/usb/LAUNCH.bat" "$DEST/LAUNCH.bat"
cp "$ROOT_REPO/usb/STOP.bat" "$DEST/STOP.bat"
cp "$ROOT_REPO/usb/LAUNCH.command" "$DEST/LAUNCH.command"
cp "$ROOT_REPO/usb/aos-boot.sh" "$DEST/aos-boot.sh"
cp "$ROOT_REPO/usb/AOS_BOOT.bat" "$DEST/AOS_BOOT.bat"
cp "$ROOT_REPO/usb/README.md" "$DEST/README.md"
chmod +x "$DEST/launch.sh" "$DEST/stop.sh" "$DEST/LAUNCH.command" "$DEST/aos-boot.sh"

if [[ ! -f "$DEST/.env" ]]; then
  cp "$ROOT_REPO/.env.example" "$DEST/.env"
  cat >> "$DEST/.env" <<'EOF'

# USB portable defaults
ROBIN_SERVE_COMPANION=1
ROBIN_OPEN_BROWSER=1
ROBIN_START_OMNIROUTE=1
ROBIN_START_HERMES=0
VOICE_HOST=127.0.0.1
VOICE_PORT=8787
TTS_PROVIDER=edge
EOF
fi

echo "==> OmniRoute helper"
cp "$ROOT_REPO/scripts/start-omniroute.sh" "$DEST/start-omniroute.sh"
chmod +x "$DEST/start-omniroute.sh"
mkdir -p "$DEST/data/omniroute"

# Seed character onto USB Hermes home if present later
mkdir -p "$DEST/data/home/.hermes"
cp "$ROOT_REPO/character/SOUL.md" "$DEST/data/home/.hermes/SOUL.md"
cp "$ROOT_REPO/character/SOUL.md" "$DEST/data/system3/SOUL.md" 2>/dev/null || true

echo "==> Born-for-pendrive dirs (shell / queue / soul)"
mkdir -p "$DEST/data/shell" "$DEST/data/queue" "$DEST/data/aos/soul" "$DEST/core" "$DEST/boot"
cp "$ROOT_REPO/docs/research/PNAOS_VISION.md" "$DEST/PNAOS_VISION.md" 2>/dev/null || true
cp "$ROOT_REPO/docs/research/USB_LAYOUT.md" "$DEST/USB_LAYOUT.md" 2>/dev/null || true

# Initialize Pendrive-Native Agent OS soul + manifest
echo "==> Initializing AOS soul"
PYTHONPATH="$DEST/app" "$DEST/runtime/venv/bin/python" -m aos init --root "$DEST" || true

echo "==> Grok Build coding sidecar notes"
mkdir -p "$DEST/bin" "$DEST/docs"
cp "$ROOT_REPO/docs/GROK_BUILD.md" "$DEST/docs/GROK_BUILD.md" 2>/dev/null || true
cat > "$DEST/bin/README-GROK.txt" <<'EOF'
Grok Build (optional coding sidecar)
  Install: curl -fsSL https://x.ai/cli/install.sh | bash
  Or:      ./app/scripts/install-grok-build.sh
  Auth:    XAI_API_KEY=xai-... in .env
  Use:     :grok  in AOS shell
  Repo:    https://github.com/xai-org/grok-build
EOF

echo ""
echo "USB kit ready at: $DEST"
echo "Next:"
echo "  1) Edit $DEST/.env (API keys — include XAI_API_KEY for Grok Build)"
echo "  2) Optional: ./scripts/install-grok-build.sh"
echo "  3) Eject safely"
echo "  4) Companion: LAUNCH.bat / launch.sh"
echo "  5) Agent OS:  AOS_BOOT.bat / aos-boot.sh  →  :robin  /  :grok"
du -sh "$DEST" 2>/dev/null || true
