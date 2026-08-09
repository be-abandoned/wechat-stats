# WeChat Chat Stats

Double-click `setup.bat` once, then `启动.bat` anytime.

## Quick Start

1. Install **Wxlens** (https://wxlens.com) and run it once
2. Double-click `setup.bat` — copies runtime from Wxlens
3. Double-click `启动.bat` — initializes, generates stats, opens dashboard
4. Next time: just double-click `启动.bat` (instant)

## Alternative: HTTP Mode (no key extraction)

If the database-key extraction path is troublesome (e.g. Wxlens UI never reaches the
"key extracted" step), use the HTTP mode instead. It reads chat data through the
Wxlens local API (`127.0.0.1:5032`) — **no key decryption needed**.

```
启动-http.bat  → checks API → auto-starts Wxlens MCP service if offline
      ↓
launcher.js    → http_stats.js (pull sessions/messages via API)
      ↓
gen_html.py    → dashboard.html + race.html → combined.html (auto-opened)
```

Usage:

1. Make sure **WeChat is running**
2. Double-click `启动-http.bat` — fetches stats, generates the dashboard, opens it
3. The dashboard has an in-page **🔄 Refresh** button backed by a small local
   service (`refresh_server.js`, port 8765). If the refresh service is not running,
   double-click `启动看板.bat` (starts the service + opens the dashboard), or run
   `register-wechatdash.bat` once to let the button auto-start the service via the
   `wechatdash://` protocol.

### New files (HTTP mode)

| File | Purpose |
|---|---|
| `启动-http.bat` | One-click launcher (thin shell calling `launcher.js`) |
| `scripts/launcher.js` | Node launcher: API check → auto-start MCP → stats → HTML → open dashboard |
| `scripts/http_stats.js` | Pulls sessions/messages from the Wxlens API and writes the same `stats.json` structure as `chat_stats.js` |
| `scripts/refresh_server.js` | Local refresh service on `127.0.0.1:8765` for the in-dashboard Refresh button |
| `scripts/api_check.js` | Health check for a local port (5032 default, any port via arg) |
| `启动看板.bat` / `start-dashboard.bat` | Start refresh service (hidden) + open dashboard |
| `register-wechatdash.bat` | Registers the `wechatdash://` protocol (HKCU, run once) so the Refresh button can auto-start the service |

Logs: `output/run.log` (launcher), `output/refresh.log` (refresh service).

## Requirements

- Windows 10/11 x64
- WeChat logged in at least once
- Wxlens installed (for key extraction + runtime binaries)
- Python 3 (optional, for HTML generation; `pip install pypinyin`)
- Node.js 18+ (for HTTP mode; any modern version with global `fetch`)

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

- Default: delete `output/` folder and run `启动.bat` again
- HTTP mode: double-click `启动-http.bat`, or use the in-dashboard **🔄 Refresh** button

## Re-initialize

Delete `pack_config.json` and run `启动.bat` again (e.g. after changing Windows user).

## Privacy

All data stays local. No external network requests. Source code is plain text — review it yourself.
