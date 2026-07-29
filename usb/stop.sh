#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$ROOT/data/logs/voice.pid" ]]; then
  kill "$(cat "$ROOT/data/logs/voice.pid")" 2>/dev/null || true
fi
pkill -f "robin_igris.portable_boot" 2>/dev/null || true
pkill -f "robin_igris.voice_server" 2>/dev/null || true
echo "Stopped. You can eject the USB."
