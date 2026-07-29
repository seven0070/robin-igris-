#!/usr/bin/env bash
# Install Grok Build (xai-org/grok-build) for Robin Igris coding sidecar.
# https://github.com/xai-org/grok-build
set -euo pipefail

echo "==> Installing Grok Build CLI (official installer)"
if [[ "$(uname -s)" == "MINGW"* ]] || [[ "$(uname -s)" == "MSYS"* ]] || [[ "${OS:-}" == "Windows_NT" ]]; then
  echo "On Windows PowerShell use: irm https://x.ai/cli/install.ps1 | iex"
fi

curl -fsSL https://x.ai/cli/install.sh | bash

# Ensure ~/.grok/bin on PATH for this shell
export PATH="${HOME}/.grok/bin:${PATH}"

if command -v grok >/dev/null 2>&1; then
  echo "==> Installed: $(grok --version 2>&1 | head -1)"
else
  echo "==> grok not on PATH yet — add ~/.grok/bin to PATH and re-open the shell"
fi

echo ""
echo "Auth (pick one):"
echo "  export XAI_API_KEY=xai-..."
echo "  or run: grok   # browser OAuth on first launch"
echo ""
echo "Robin integration:"
echo "  :grok                 # status in AOS shell"
echo "  :grok fix the auth bug"
echo "  tools: grok_status / grok_ask / grok_code"
echo ""
echo "Optional: clone sources for contribution"
echo "  git clone https://github.com/xai-org/grok-build.git"
echo "  # pinned SOURCE_REV at integration: 2a818575225183d8ca915f5632a09b8067b5156a"
