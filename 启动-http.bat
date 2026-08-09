@echo off
cd /d "%~dp0"

:: prefer node from PATH, fall back to common install locations
where node >nul 2>&1
if errorlevel 1 (
  if exist "%ProgramFiles%\nodejs\node.exe" (
    set "NODE=%ProgramFiles%\nodejs\node.exe"
  ) else if exist "%LOCALAPPDATA%\Programs\nodejs\node.exe" (
    set "NODE=%LOCALAPPDATA%\Programs\nodejs\node.exe"
  ) else (
    echo [ERROR] Node.js not found. Install Node.js 18+: https://nodejs.org
    echo Then run this script again.
    echo.
    pause
    exit /b 1
  )
) else (
  set "NODE=node"
)

"%NODE%" "%~dp0scripts\launcher.js"
pause
