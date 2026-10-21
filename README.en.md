# WeChat Stats

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18-brightgreen)](https://nodejs.org)
[![Python](https://img.shields.io/badge/python-3.x-yellow)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20x64-lightgrey)](#requirements)

A **local-first statistics dashboard for your own WeChat chat data**. All processing happens on
your machine, and the tool never talks to an external server. Messages are read through the local
HTTP API of [Wxlens](https://github.com/be-abandoned/wechat-stats/releases/tag/v4.5.0), so no
database key extraction is required.

中文文档：[README.md](README.md)

---

## Features

- **Private and group chat statistics** — message counts, hour-of-day and time-of-day distribution,
  activity ranking, rendered as a self-contained interactive HTML dashboard
  (`output/combined.html`).
- **Moments reader** (`scripts/sns_timeline.js`) — latest posts with their text and the list of
  people who liked them; filter by count, keyword or wxid.
- **One-click start** — `启动.bat` runs the whole pipeline: check Node → pull stats → build the
  dashboard → open it in the browser.
- **Refresh from inside the dashboard** — the 🔄 button talks to a local service on
  `127.0.0.1:8765`, so you can re-pull data without restarting anything.
- **Fully offline** — apart from the local Wxlens API, nothing is contacted. The source is plain,
  readable scripts you can audit yourself.

## Moments (post text + likes)

```bash
# Requires: WeChat running, Wxlens installed (ships the koffi runtime)
node scripts\sns_timeline.js                 # latest 20 posts
node scripts\sns_timeline.js --limit 50      # latest 50 posts
node scripts\sns_timeline.js --keyword travel # keyword filter
node scripts\sns_timeline.js --username wxid_xxx
node scripts\sns_timeline.js --raw           # raw JSON output
```

Each post shows author / timestamp / text / likers (display names); `--all` also includes comments.
Implementation: reads the `SnsTimeLine` table in `db_storage\sns\sns.db` through WCDB's
`wcdb_get_sns_timeline` API.

## Quick start (HTTP mode — recommended)

1. **Install Wxlens** — download `WxLens-4.5.0-Setup.exe` from the
   [GitHub release](https://github.com/be-abandoned/wechat-stats/releases/tag/v4.5.0)
   ([direct link](https://github.com/be-abandoned/wechat-stats/releases/download/v4.5.0/WxLens-4.5.0-Setup.exe)).
   Open it once so it initialises and starts its local API on `127.0.0.1:5032`.
2. **Make sure WeChat is running** and logged in.
3. **Double-click `启动.bat`** — it pulls the latest statistics, builds the dashboard and opens
   `output\combined.html`. The first run also registers the `wechatdash://` protocol.
4. **Refresh** — run `启动.bat` again, or press the **🔄** button in the dashboard (served by the
   local service on port 8765; the launcher keeps it alive and the `wechatdash://` handler starts it
   on demand).

### How the HTTP pipeline works

```
启动.bat  -> launcher.js -> probe API (127.0.0.1:5032)
      |  (if offline, auto-start the Wxlens MCP service, wait up to ~40s)
http_stats.js  -> pull conversations and messages through the Wxlens HTTP API
      |
gen_html.py    -> dashboard.html + race.html -> combined.html (opened automatically)
```

### Requirements

- **Windows 10/11 x64**
- **Wxlens installed and initialised** (first launch starts the API on port 5032)
- **WeChat running and logged in**
- **Node.js 18+** (any version with global `fetch`; the launcher looks on `PATH` first, then common
  install locations)
- **Python 3** + `pypinyin` for HTML generation. The launcher prefers a project-local virtualenv
  (`.venv` / `venv`) and falls back to `python` on `PATH`. Install with `pip install pypinyin`.
- CLI alternative: `node scripts\launcher.js` (equivalent to double-clicking `启动.bat`)
- Logs: `output\run.log` (launcher), `output\refresh.log` (refresh service)

### Optional: contact name mapping

`scripts/wxid_names.json` is **not** part of the repository, because it contains real contact data.
Create it yourself if you want readable names:

```json
{ "names": { "wxid_example": "Display name" } }
```

Without the file the dashboard simply shows raw wxids; statistics are unaffected.

### File overview

| File | Purpose |
|---|---|
| `启动.bat` | Main entry point — Node check → protocol registration → stats → HTML → open dashboard |
| `start-dashboard.bat` | Internal: starts the refresh service and handles the `wechatdash://` protocol |
| `scripts/launcher.js` | Node launcher (HTTP mode pipeline) |
| `scripts/http_stats.js` | Pulls conversations/messages from the Wxlens API into `stats.json` |
| `scripts/refresh_server.js` | Local refresh service on `127.0.0.1:8765` |
| `scripts/api_check.js` | Port health check |
| `scripts/sns_timeline.js` | Moments reader |
| `scripts/gen_html.py` and friends | Dashboard HTML generation |
| `setup.bat` | Legacy helper: copies runtime binaries from Wxlens |

## Legacy path (direct database access, requires key extraction)

> ⚠️ **Deprecated.** Kept only as historical implementation. It decrypts the database key from
> Wxlens' configuration via DPAPI and fails on some machines.

```
setup.bat -> copy electron.exe + WCDB DLLs from Wxlens
     |
scripts/init.js -> extract the database key from the Wxlens config (DPAPI)
     |
chat_stats.js -> read the WeChat database through WCDB -> stats.json
     |
gen_html.py -> dashboard.html + race.html -> combined.html
```

`setup.bat` searches for Wxlens in `D:\APP\Wxlens`, `%LOCALAPPDATA%\Programs\WxLens`,
`C:\Program Files\WxLens`, and the Windows uninstall registry entries.

## Privacy and security

- **Your data stays on your machine.** Every read and write is local; nothing is sent to any
  external server.
- **No telemetry** — no usage reporting, no crash reporting, no accounts.
- **No key extraction by default** — the recommended HTTP mode reads through the local Wxlens API.
  The legacy DPAPI path is never run automatically.
- **No real chat data in the repository** — the sample dashboard and the contact name mapping have
  been removed from version control and are git-ignored.
- Only use this tool with WeChat accounts and devices **you are allowed to access**, and never
  upload someone else's chat history.

## Known limitations

- Windows only (depends on Wxlens' local service and WCDB binaries).
- Depends on the third-party **Wxlens** application; if it changes its data interface, readers may
  break.
- The legacy key-extraction path fails on some machines — use HTTP mode instead.

## License

[MIT](LICENSE) © 2026 be-abandoned

## Contributing

Issues and pull requests are welcome — please read [CONTRIBUTING.md](CONTRIBUTING.md) first.
**Never include real chat data, contact names or wxids in an issue or pull request.**
