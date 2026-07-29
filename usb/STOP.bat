@echo off
set "ROOT=%~dp0"
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Robin*" >nul 2>&1
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
  rem best-effort: user can close the LAUNCH window instead
)
echo Close the LAUNCH window if it is still open, then eject the USB.
pause
