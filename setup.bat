@echo off
setlocal enabledelayedexpansion
title WeChat Stats Setup
cd /d "%~dp0"

echo.
echo ========================================
echo   WeChat Stats - Setup
echo   Copying runtime from Wxlens...
echo ========================================
echo.

:: Find Wxlens installation
set WXLENS=
if exist "D:\APP\Wxlens\electron.exe" set WXLENS=D:\APP\Wxlens
if "%WXLENS%"=="" if exist "%LOCALAPPDATA%\Programs\WxLens\electron.exe" set WXLENS=%LOCALAPPDATA%\Programs\WxLens
if "%WXLENS%"=="" if exist "C:\Program Files\WxLens\electron.exe" set WXLENS=C:\Program Files\WxLens

if "%WXLENS%"=="" (
    echo [ERROR] Wxlens not found!
    echo.
    echo Please install Wxlens first. See README for download link.
    echo Then run this setup again.
    echo.
    pause
    exit /b 1
)

echo [OK] Found Wxlens at: %WXLENS%
echo.

:: Copy Electron runtime
echo Copying Electron runtime...
copy /Y "%WXLENS%\electron.exe" "%~dp0electron.exe" >nul
copy /Y "%WXLENS%\icudtl.dat" "%~dp0icudtl.dat" >nul
copy /Y "%WXLENS%\v8_context_snapshot.bin" "%~dp0v8_context_snapshot.bin" >nul
copy /Y "%WXLENS%\snapshot_blob.bin" "%~dp0snapshot_blob.bin" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Failed to copy Electron runtime
    pause
    exit /b 1
)
echo [OK] Electron runtime

:: Copy WCDB DLLs
echo Copying WCDB libraries...
if not exist "%~dp0wcdb" mkdir "%~dp0wcdb"
copy /Y "%WXLENS%\resources\resources\wcdb\win32\x64\WCDB.dll" "%~dp0wcdb\" >nul 2>&1
copy /Y "%WXLENS%\resources\resources\wcdb\win32\x64\wcdb_api.dll" "%~dp0wcdb\" >nul 2>&1
copy /Y "%WXLENS%\resources\resources\wcdb\win32\x64\SDL2.dll" "%~dp0wcdb\" >nul 2>&1
copy /Y "%WXLENS%\resources\resources\key\win32\x64\wx_key.dll" "%~dp0wcdb\" >nul 2>&1
if not exist "%~dp0wcdb\WCDB.dll" (
    echo [ERROR] Failed to copy WCDB DLLs
    pause
    exit /b 1
)
echo [OK] WCDB libraries

:: Copy koffi
echo Copying koffi module...
if not exist "%~dp0node_modules" mkdir "%~dp0node_modules"
xcopy /E /I /Y "%WXLENS%\resources\app.asar.unpacked\tools\wx-mcp-server\node_modules\koffi" "%~dp0node_modules\koffi" >nul 2>&1
if not exist "%~dp0node_modules\koffi\index.js" (
    echo [ERROR] Failed to copy koffi
    pause
    exit /b 1
)
echo [OK] koffi

echo.
echo ========================================
echo   Setup complete!
echo   You can now run: 启动.bat
echo ========================================
echo.
pause
