# WeChat Chat Stats

Double-click `setup.bat` once, then `启动.bat` anytime.

## Quick Start

1. Install **Wxlens** (https://wxlens.com) and run it once
2. Double-click `setup.bat` — copies runtime from Wxlens
3. Double-click `启动.bat` — initializes, generates stats, opens dashboard
4. Next time: just double-click `启动.bat` (instant)

## Requirements

- Windows 10/11 x64
- WeChat logged in at least once
- Wxlens installed (for key extraction + runtime binaries)
- Python 3 (optional, for HTML generation; `pip install pypinyin`)

## How It Works

```
setup.bat → copies electron.exe + WCDB DLLs from Wxlens
     ↓
启动.bat → init.js → extract key from Wxlens config (DPAPI decrypt)
     ↓
chat_stats.js → read WeChat DB via WCDB → stats.json
     ↓
gen_html.py → dashboard.html + race.html → combined.html
```

## Refresh Data

Delete `output/` folder and run `启动.bat` again.

## Re-initialize

Delete `pack_config.json` and run `启动.bat` again (e.g. after changing Windows user).

## Privacy

All data stays local. No network requests. Source code is plain text — review it yourself.
