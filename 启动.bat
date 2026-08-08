@echo off
setlocal enabledelayedexpansion
title WeChat Stats
cd /d "%~dp0"

set ELECTRON=%~dp0electron.exe
set NODE_PATH=%~dp0node_modules

:: Auto-detect Python
set PYTHON=
for %%p in (python3 python py) do (
    where %%p >nul 2>nul && set PYTHON=%%p && goto :found_python
)
:found_python

echo.
echo ========================================
echo   WeChat Chat Stats Launcher
echo ========================================
echo.

:: Step 0: Auto-setup if first run (no electron.exe)
if not exist "%~dp0electron.exe" (
    echo [Setup] Runtime not found, running setup...
    echo.
    call "%~dp0setup.bat"
    if %errorlevel% neq 0 exit /b 1
)

:: Step 1: First-time init
if not exist "pack_config.json" (
    echo [First Run] Initializing...
    echo.
    set ELECTRON_RUN_AS_NODE=1
    "%ELECTRON%" "%~dp0scripts\init.js"
    if !errorlevel! neq 0 (
        echo.
        echo ========================================
        echo   Init failed! Possible reasons:
        echo   1. Wxlens not installed
        echo   2. WeChat data not found
        echo   3. WeChat not running
        echo.
        echo   See: install guide
        echo ========================================
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Init complete
    echo.
)

:: Step 2: Generate stats (first time only)
if not exist "output\stats_data" (
    echo [First Run] Generating statistics...
    echo This may take 5-15 minutes. Please wait...
    echo.
    set ELECTRON_RUN_AS_NODE=1
    "%ELECTRON%" "%~dp0scripts\chat_stats.js"
    if !errorlevel! neq 0 (
        echo Stats generation failed!
        pause
        exit /b 1
    )
    echo.
    echo [First Run] Generating HTML dashboard...
    if not "%PYTHON%"=="" (
        "%PYTHON%" "%~dp0scripts\gen_html.py"
    ) else (
        echo [WARN] Python not found, using sample page
    )
)

:: Step 3: Open dashboard
echo [OK] Opening dashboard...
if exist "output\combined.html" (
    start "" "%~dp0output\combined.html"
) else if exist "static\combined.html" (
    start "" "%~dp0static\combined.html"
) else (
    echo [WARN] No dashboard HTML found
)

echo.
echo ========================================
echo   Tips:
echo   - Next launch opens instantly
echo   - To refresh: delete "output" folder
echo   - To re-init: delete "pack_config.json"
echo ========================================
echo.
pause
