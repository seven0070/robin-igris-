#!/usr/bin/env bash
# Optional: install Grok Build onto a prepared USB kit PATH hint file.
# Usage: ./scripts/usb-link-grok.sh /path/to/USB/ROBIN_IGRIS
set -euo pipefail
DEST="${1:-}"
if [[ -z "$DEST" ]]; then
  echo "Usage: $0 /path/to/USB/ROBIN_IGRIS"
  exit 1
fi
mkdir -p "$DEST/bin" "$DEST/docs"
cp "$(cd "$(dirname "$0")/.." && pwd)/docs/GROK_BUILD.md" "$DEST/docs/GROK_BUILD.md" 2>/dev/null || true
cat > "$DEST/bin/README-GROK.txt" <<'EOF'
Grok Build coding sidecar
=========================
1) On the host (or portable Git Bash):
     curl -fsSL https://x.ai/cli/install.sh | bash
2) Set XAI_API_KEY in ROBIN_IGRIS/.env
3) From AOS shell: :grok   or   :grok <coding task>
Upstream: https://github.com/xai-org/grok-build
EOF
echo "Wrote $DEST/bin/README-GROK.txt"
echo "Install CLI with: ./scripts/install-grok-build.sh"
