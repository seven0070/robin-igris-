#!/usr/bin/env bash
# One-click: install Robin Igris onto a plugged-in USB pendrive.
# Auto-detects removable volumes; override with ROBIN_USB_DEST=/path
set -euo pipefail

ROOT_REPO="$(cd "$(dirname "$0")/.." && pwd)"
FOLDER_NAME="${ROBIN_USB_FOLDER:-ROBIN_IGRIS}"

is_skip_vol() {
  local base
  base="$(basename "$1")"
  case "$base" in
    ""|"."|".."|"Macintosh HD"|"Macintosh HD - Data"|"System"|"Data"|"Preboot"|"Recovery"|"Update"|"com.apple.TimeMachine.localsnapshots")
      return 0 ;;
  esac
  return 1
}

collect_candidates() {
  local d
  for d in /media/*/* /run/media/*/* /mnt/*; do
    [[ -d "$d" ]] || continue
    is_skip_vol "$d" && continue
    [[ -w "$d" ]] || continue
    printf '%s\n' "$d"
  done
  if [[ "$(uname -s)" == "Darwin" ]]; then
    for d in /Volumes/*; do
      [[ -d "$d" ]] || continue
      is_skip_vol "$d" && continue
      [[ -w "$d" ]] || continue
      printf '%s\n' "$d"
    done
  fi
}

# Portable array build (bash 3.2 on macOS has no mapfile)
CANDS=()
while IFS= read -r line; do
  [[ -n "$line" ]] && CANDS+=("$line")
done < <(collect_candidates | awk 'NF' | sort -u)

DEST_ROOT="${ROBIN_USB_DEST:-}"
if [[ -z "$DEST_ROOT" ]]; then
  if [[ ${#CANDS[@]} -eq 0 ]]; then
    echo "No USB volume auto-detected."
    echo "Plug in a formatted pendrive (exFAT/NTFS), or set:"
    echo "  ROBIN_USB_DEST=/path/to/USB ./scripts/one-click-usb.sh"
    printf 'USB mount path: '
    read -r DEST_ROOT
  elif [[ ${#CANDS[@]} -eq 1 ]]; then
    DEST_ROOT="${CANDS[0]}"
    echo "==> Using USB: $DEST_ROOT"
  else
    echo "Multiple volumes found:"
    i=1
    for d in "${CANDS[@]}"; do
      echo "  [$i] $d"
      i=$((i + 1))
    done
    printf 'Pick number (or paste path): '
    read -r pick
    if [[ "$pick" =~ ^[0-9]+$ ]] && (( pick >= 1 && pick <= ${#CANDS[@]} )); then
      DEST_ROOT="${CANDS[$((pick - 1))]}"
    else
      DEST_ROOT="$pick"
    fi
  fi
fi

if [[ -z "${DEST_ROOT:-}" || ! -d "$DEST_ROOT" ]]; then
  echo "Invalid USB path: ${DEST_ROOT:-empty}"
  exit 1
fi
if [[ ! -w "$DEST_ROOT" ]]; then
  echo "USB path not writable: $DEST_ROOT"
  exit 1
fi

DEST="$DEST_ROOT/$FOLDER_NAME"
echo ""
echo "=============================================="
echo "  Robin Igris — one-click USB install"
echo "=============================================="
echo "  Repo : $ROOT_REPO"
echo "  Dest : $DEST"
echo ""

need=()
command -v python3 >/dev/null || need+=("python3")
command -v npm >/dev/null || need+=("npm")
if [[ ${#need[@]} -gt 0 ]]; then
  echo "Missing tools: ${need[*]}"
  echo "Install them, then re-run. Continuing may fail at venv/companion build."
fi

chmod +x "$ROOT_REPO/scripts/prepare-usb.sh" 2>/dev/null || true
mkdir -p "$DEST"
"$ROOT_REPO/scripts/prepare-usb.sh" "$DEST"

cat > "$DEST/START_HERE.txt" <<'EOF'
Robin Igris is installed on this pendrive.

Windows:  double-click  AOS_BOOT.bat
macOS/Linux:  ./aos-boot.sh

Optional companion UI: LAUNCH.bat / launch.sh
Shell: :robin

Edit .env for API keys (OmniRoute).
Backup: data/aos/soul/  and  data/aos/robin/
EOF

echo ""
echo "One-click install complete."
echo "  Open: $DEST"
echo "  Boot: AOS_BOOT.bat  or  ./aos-boot.sh"
echo "  Then: :robin"
