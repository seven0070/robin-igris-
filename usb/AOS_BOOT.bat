@echo off
REM Boot Pendrive-Native Agent OS — agent is the shell (no desktop UX)
setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "ROBIN_USB_ROOT=%ROOT%"
set "ROBIN_AOS_MODE=1"
set "HOME=%ROOT%\data\home"
set "PYTHONPATH=%ROOT%\app;%PYTHONPATH%"

set "PY=%ROOT%\runtime\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

cd /d "%ROOT%\app"
echo Booting Pendrive-Native Agent OS...
"%PY%" -m aos.boot --root "%ROOT%"
pause
