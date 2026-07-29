@echo off
REM Launch Robin Igris from this USB stick (Windows)
setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "ROBIN_USB_ROOT=%ROOT%"
set "ROBIN_COMPANION_DIST=%ROOT%\companion-dist"
set "ROBIN_SERVE_COMPANION=1"
set "ROBIN_SYSTEM3_ROOT=%ROOT%\data\system3"
set "HOME=%ROOT%\data\home"
set "XDG_CONFIG_HOME=%ROOT%\data\xdg"

set "PY=%ROOT%\runtime\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

cd /d "%ROOT%\app"
echo Robin Igris — USB portable
echo Root: %ROOT%
echo Opening display on this PC's browser...
"%PY%" -m robin_igris.portable_boot
pause
