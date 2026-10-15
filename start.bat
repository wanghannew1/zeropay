@echo off
rem ZeroPay Windows double-click launcher; bypasses PowerShell execution policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
