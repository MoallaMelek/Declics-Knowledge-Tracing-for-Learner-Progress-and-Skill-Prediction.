@echo off
rem Double-click after an update: stops the running DECLIC server (and only DECLIC), then starts the new version.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch.ps1" -Restart -Open %*
if errorlevel 1 pause
