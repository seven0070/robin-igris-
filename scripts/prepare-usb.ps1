# Prepare Robin Igris onto a USB drive (Windows PowerShell)
# Usage: .\scripts\prepare-usb.ps1 E:\ROBIN_IGRIS
param(
  [Parameter(Mandatory = $true)][string]$Dest
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force -Path @(
  "$Dest\app",
  "$Dest\data\home",
  "$Dest\data\system3",
  "$Dest\data\logs",
  "$Dest\runtime",
  "$Dest\companion-dist"
) | Out-Null
New-Item -ItemType File -Force -Path "$Dest\.robin_usb" | Out-Null

Write-Host "==> Copying app"
robocopy "$Repo" "$Dest\app" /MIR /XD .git .venv node_modules companion\node_modules companion\dist companion\.cache companion\public\assets data __pycache__ .pytest_cache /NFL /NDL /NJH /NJS | Out-Null

Write-Host "==> Building companion"
Push-Location "$Repo\companion"
npm install
$env:VITE_HERMES_BASE_URL = "/hermes/v1"
$env:VITE_VOICE_BASE_URL = ""
$env:VITE_AGENT_NAME = "Robin Igris"
npm run build
robocopy "$Repo\companion\dist" "$Dest\companion-dist" /MIR /NFL /NDL /NJH /NJS | Out-Null
if (Test-Path "$Repo\companion\public\assets") {
  robocopy "$Repo\companion\public\assets" "$Dest\companion-dist\assets" /E /NFL /NDL /NJH /NJS | Out-Null
}
Pop-Location

Write-Host "==> Portable venv on USB"
python -m venv "$Dest\runtime\venv"
& "$Dest\runtime\venv\Scripts\python.exe" -m pip install -U pip
& "$Dest\runtime\venv\Scripts\pip.exe" install -r "$Dest\app\requirements.txt"

Copy-Item "$Repo\usb\LAUNCH.bat" "$Dest\LAUNCH.bat" -Force
Copy-Item "$Repo\usb\STOP.bat" "$Dest\STOP.bat" -Force
Copy-Item "$Repo\usb\launch.sh" "$Dest\launch.sh" -Force
Copy-Item "$Repo\usb\stop.sh" "$Dest\stop.sh" -Force
Copy-Item "$Repo\usb\LAUNCH.command" "$Dest\LAUNCH.command" -Force
Copy-Item "$Repo\usb\README.md" "$Dest\README.md" -Force

if (-not (Test-Path "$Dest\.env")) {
  Copy-Item "$Repo\.env.example" "$Dest\.env"
  Add-Content "$Dest\.env" @"

ROBIN_SERVE_COMPANION=1
ROBIN_OPEN_BROWSER=1
VOICE_HOST=127.0.0.1
VOICE_PORT=8787
TTS_PROVIDER=edge
"@
}

New-Item -ItemType Directory -Force -Path "$Dest\data\home\.hermes" | Out-Null
Copy-Item "$Repo\character\SOUL.md" "$Dest\data\home\.hermes\SOUL.md" -Force

Write-Host "USB kit ready at $Dest"
Write-Host "Edit .env then use LAUNCH.bat on any PC"
