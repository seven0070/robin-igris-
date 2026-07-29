@echo off
REM One-click Robin Igris → USB (double-click this file)
cd /d "%~dp0"
title Robin Igris — USB Install
echo.
echo  Robin Igris — one-click install to pendrive
echo  Plug in your USB first (exFAT or NTFS).
echo.
where powershell >nul 2>&1
if errorlevel 1 (
  echo PowerShell required.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\one-click-usb.ps1"
echo.
pause
