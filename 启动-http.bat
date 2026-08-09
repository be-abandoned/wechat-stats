@echo off
cd /d "%~dp0"

:: prefer node from PATH, fall back to a managed runtime if absent
where node >nul 2>&1
if errorlevel 1 (
  set "NODE=C:\Users\Abandon\.workbuddy\binaries\node\versions\22.22.2\node.exe"
) else (
  set "NODE=node"
)

"%NODE%" "%~dp0scripts\launcher.js"
pause
