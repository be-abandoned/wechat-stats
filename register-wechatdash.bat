@echo off
:: Register wechatdash:// protocol so the dashboard refresh button can auto-start the service
:: Run once. Does NOT need admin (HKCU only).
reg add "HKCU\Software\Classes\wechatdash" /ve /d "URL:WeChatDash" /f >nul
reg add "HKCU\Software\Classes\wechatdash" /v "URL Protocol" /d "" /f >nul
reg add "HKCU\Software\Classes\wechatdash\shell\open\command" /ve /d "\"%~dp0start-dashboard.bat\" \"%%1\"" /f >nul
echo [OK] wechatdash:// protocol registered.
echo Now the "Refresh" button in the dashboard can auto-start the service.
pause
