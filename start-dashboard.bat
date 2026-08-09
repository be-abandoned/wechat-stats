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

:: start refresh server (hidden) if not already running on 8765
"%NODE%" "%~dp0scripts\api_check.js" 8765 >nul 2>&1
if not errorlevel 1 goto :open

:: protocol invoked (wechatdash://start) -> only start server, do not open dashboard
if /i "%1"=="wechatdash://start" goto :start_only

start "WxDashRefresh" /min "%NODE%" "%~dp0scripts\refresh_server.js"
goto :open

:start_only
start "WxDashRefresh" /min "%NODE%" "%~dp0scripts\refresh_server.js"
exit /b 0

:open
timeout /t 2 /nobreak >nul 2>&1
start "" "%~dp0output\combined.html"
