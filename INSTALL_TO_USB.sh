#!/usr/bin/env bash
# Linux/macOS one-click entry (same as INSTALL_TO_USB.command)
cd "$(dirname "$0")"
chmod +x scripts/one-click-usb.sh scripts/prepare-usb.sh 2>/dev/null || true
exec ./scripts/one-click-usb.sh
