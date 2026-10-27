@echo off
rem Double-click to start DECLIC and open the home page in the default browser.
rem The PowerShell execution policy is relaxed for this one process only.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch.ps1" -Open %*
if errorlevel 1 pause
