#!/bin/bash
# Double-click on macOS (Finder) — same as INSTALL_TO_USB.sh
cd "$(dirname "$0")" || exit 1
exec bash "./INSTALL_TO_USB.sh"
