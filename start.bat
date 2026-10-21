@echo off
REM Portable entry point (ASCII name). On Windows, 启动.bat does the same plus the
REM wechatdash:// protocol registration used by the in-dashboard Refresh button.
setlocal
cd /d "%~dp0"

where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js not found. Install Node.js 18+: https://nodejs.org
  pause
  exit /b 1
)

node "%~dp0scripts\launcher.js"
pause
