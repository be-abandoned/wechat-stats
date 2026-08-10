@echo off
setlocal
title WeChat Stats
cd /d "%~dp0"

:: 1. Node.js: PATH first, then common install locations
where node >nul 2>&1
if errorlevel 1 (
  if exist "%ProgramFiles%\nodejs\node.exe" (
    set "NODE=%ProgramFiles%\nodejs\node.exe"
  ) else if exist "%LOCALAPPDATA%\Programs\nodejs\node.exe" (
    set "NODE=%LOCALAPPDATA%\Programs\nodejs\node.exe"
  ) else (
    echo [ERROR] Node.js not found. Install Node.js 18+: https://nodejs.org
    echo.
    pause
    exit /b 1
  )
) else (
  set "NODE=node"
)

:: 2. Register wechatdash:// protocol once (HKCU, no admin needed)
::    Lets the in-dashboard Refresh button auto-start the service.
reg query "HKCU\Software\Classes\wechatdash" >nul 2>&1
if errorlevel 1 (
  reg add "HKCU\Software\Classes\wechatdash" /ve /d "URL:WeChatDash" /f >nul
  reg add "HKCU\Software\Classes\wechatdash" /v "URL Protocol" /d "" /f >nul
  reg add "HKCU\Software\Classes\wechatdash\shell\open\command" /ve /d "\"%~dp0start-dashboard.bat\" \"%%1\"" /f >nul
)

:: 3. Run launcher (HTTP mode: stats -> HTML -> dashboard)
"%NODE%" "%~dp0scripts\launcher.js"
pause
