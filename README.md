# WeChat Chat Stats

Local WeChat chat statistics dashboard. **HTTP Mode** (recommended) reads chat data
through the Wxlens local API — **no database key extraction needed**.

## Quick Start (HTTP Mode — recommended)

1. **Install Wxlens** — download from the
   [GitHub Release](https://github.com/be-abandoned/wechat-stats/releases/tag/v4.5.0)
   (`WxLens-4.5.0-Setup.exe`, direct link:
   [WxLens-4.5.0-Setup.exe](https://github.com/be-abandoned/wechat-stats/releases/download/v4.5.0/WxLens-4.5.0-Setup.exe)),
   run the installer, then **open Wxlens once** so it completes first-time
   initialization (this starts its local API service on `127.0.0.1:5032`).
2. **Make sure WeChat is running** and logged in.
3. **Double-click `启动-http.bat`** — it fetches the latest stats, generates the
   dashboard, and opens `output\combined.html` automatically.
4. **Refresh later**: double-click `启动-http.bat` again, or use the **🔄 Refresh**
   button inside the dashboard (backed by a small local service on port 8765;
   if the service is not running, double-click `启动看板.bat`, or run
   `register-wechatdash.bat` once so the button auto-starts it via the
   `wechatdash://` protocol).

### HTTP Mode — how it works

```
启动-http.bat  → launcher.js → checks API (127.0.0.1:5032)
      ↓ (offline → auto-starts Wxlens MCP service / waits up to ~40s)
http_stats.js  → pull sessions & messages via Wxlens HTTP API
      ↓
gen_html.py    → dashboard.html + race.html → combined.html (auto-opened)
```

### HTTP Mode — requirements & notes

- Windows 10/11 x64
- **Wxlens installed and opened once** (first-time init starts the 5032 API)
- **WeChat running and logged in**
- **Node.js 18+** (any version with global `fetch`; the launcher scripts find
  `node` from PATH, falling back to common install locations)
- **Python 3** with `pypinyin` for HTML generation: `pip install pypinyin`
  (skip if you only run the launcher without HTML — not recommended)
- Command-line alternative: `node scripts\launcher.js` (same as double-clicking
  `启动-http.bat`)
- Logs: `output\run.log` (launcher), `output\refresh.log` (refresh service)

## Legacy path (database-direct read, requires key extraction)

The original flow reads the WeChat database directly via WCDB and needs the
database key:

```
setup.bat → copies electron.exe + WCDB DLLs from Wxlens
     ↓
启动.bat → init.js → extract key from Wxlens config (DPAPI decrypt)
     ↓
chat_stats.js → read WeChat DB via WCDB → stats.json
     ↓
gen_html.py → dashboard.html + race.html → combined.html
```

> ⚠️ Note: key extraction (`init.js`) is experimental and may fail on some
> machines. If it fails, **use HTTP Mode instead** (see Quick Start).

Requirements: Wxlens installed (for runtime binaries), `setup.bat` finds it at
`D:\APP\Wxlens`, `%LOCALAPPDATA%\Programs\WxLens`, `C:\Program Files\WxLens`,
or via Windows registry uninstall entries.

## Download Wxlens

| Source | Link |
|---|---|
| **GitHub Release (recommended)** | https://github.com/be-abandoned/wechat-stats/releases/tag/v4.5.0 |
| Direct installer | https://github.com/be-abandoned/wechat-stats/releases/download/v4.5.0/WxLens-4.5.0-Setup.exe |

## Refresh Data

- HTTP Mode: double-click `启动-http.bat`, or the in-dashboard **🔄 Refresh** button
- Legacy: delete `output/` folder and run `启动.bat` again

## Re-initialize (legacy)

Delete `pack_config.json` and run `启动.bat` again (e.g. after changing Windows user).

## Privacy

All data stays local. No external network requests. Source code is plain text — review it yourself.
