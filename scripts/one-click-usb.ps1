# One-click: install Robin Igris onto a plugged-in USB pendrive (Windows).
# Auto-detects removable drives; override: -Dest E:\  or  $env:ROBIN_USB_DEST='E:\'
param(
  [string]$Dest = $env:ROBIN_USB_DEST,
  [string]$FolderName = $(if ($env:ROBIN_USB_FOLDER) { $env:ROBIN_USB_FOLDER } else { "ROBIN_IGRIS" })
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot

function Get-RemovableRoots {
  $roots = @()
  try {
    Get-Volume -ErrorAction SilentlyContinue |
      Where-Object { $_.DriveType -eq 'Removable' -and $_.DriveLetter } |
      ForEach-Object { $roots += ("{0}:\" -f $_.DriveLetter) }
  } catch {}
  # Fallback: Win32_LogicalDisk DriveType 2 = Removable
  try {
    Get-CimInstance -ClassName Win32_LogicalDisk -ErrorAction SilentlyContinue |
      Where-Object { $_.DriveType -eq 2 -and $_.DeviceID } |
      ForEach-Object { $roots += ($_.DeviceID + '\') }
  } catch {}
  $roots | Where-Object { $_ -and ($_ -notmatch '^[Cc]:') } | Select-Object -Unique
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗"
Write-Host "║   Robin Igris — one-click USB install        ║"
Write-Host "╚══════════════════════════════════════════════╝"

if (-not $Dest) {
  $cands = @(Get-RemovableRoots)
  if ($cands.Count -eq 0) {
    Write-Host "No removable USB detected. Plug in a pendrive (exFAT/NTFS)."
    $Dest = Read-Host "USB drive letter path (e.g. E:\)"
  } elseif ($cands.Count -eq 1) {
    $Dest = $cands[0]
    Write-Host "==> Using USB: $Dest"
  } else {
    Write-Host "Multiple drives:"
    for ($i = 0; $i -lt $cands.Count; $i++) {
      Write-Host ("  [{0}] {1}" -f ($i + 1), $cands[$i])
    }
    $pick = Read-Host "Pick number (or paste path like E:\)"
    if ($pick -match '^\d+$') {
      $idx = [int]$pick - 1
      if ($idx -ge 0 -and $idx -lt $cands.Count) { $Dest = $cands[$idx] }
      else { throw "Invalid selection" }
    } else {
      $Dest = $pick
    }
  }
}

if (-not $Dest.EndsWith('\')) { $Dest = $Dest + '\' }
if (-not (Test-Path $Dest)) { throw "USB path not found: $Dest" }

$Target = Join-Path $Dest $FolderName
Write-Host "  Repo : $Repo"
Write-Host "  Dest : $Target"
Write-Host ""

& "$PSScriptRoot\prepare-usb.ps1" -Dest $Target

@"
Robin Igris is installed on this pendrive.

Windows:  double-click  AOS_BOOT.bat
Optional: LAUNCH.bat (companion UI)

Shell: :robin
Edit .env for API keys (OmniRoute).
Backup: data\aos\soul\  and  data\aos\robin\
"@ | Set-Content -Path (Join-Path $Target "START_HERE.txt") -Encoding UTF8

Write-Host ""
Write-Host "One-click install complete."
Write-Host "Open: $Target"
Write-Host "Boot: AOS_BOOT.bat"
