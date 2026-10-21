# WeChat Stats

[![CI](https://github.com/be-abandoned/wechat-stats/actions/workflows/ci.yml/badge.svg)](https://github.com/be-abandoned/wechat-stats/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18-brightgreen)](https://nodejs.org)
[![Python](https://img.shields.io/badge/python-3.x-yellow)](https://www.python.org)

A **local-first statistics dashboard for chat conversations**. It turns a chat export into an
interactive HTML dashboard: message counts, activity ranking, hour-of-day and time-of-day patterns,
reply latency, and a bar-chart-race animation of your most active conversations.

Everything runs on your machine. The project **never reads an encrypted database and never
decrypts a key** — it consumes plain JSON from a local HTTP provider that you run yourself, on
`127.0.0.1`. No network calls, no uploads, no telemetry.

中文文档：[README.md](README.md)

---

## Try it in 30 seconds (no real data needed)

The repository ships a **synthetic** data provider, so the full pipeline runs on a fresh clone:

```bash
node tools/mock-provider.js      # terminal A: synthetic provider on 127.0.0.1:5032
npm start                        # terminal B: stats -> dashboard -> opens output/combined.html
```

The demo data is randomly generated: 8 conversations, ~15k messages, ids like `wxid_demo_*`. It
contains no real content and is regenerated deterministically on every start.

## What you get

- **Per-conversation stats** — total messages, sent/received split, active days, best streak, average
  messages per active day, average and maximum text length.
- **Time patterns** — 24-hour histogram, day-part split (night / morning / afternoon / evening),
  month-by-month trend.
- **Reply behaviour** — median and mean reply gap in both directions, share of replies within an hour.
- **Activity ranking** — a bar-chart-race animation over the last 30 days per frame.
- **One interactive page** — a single self-contained `output/combined.html` that works offline, with
  a 🔄 refresh button backed by a local service on `127.0.0.1:8765`.

## Architecture

```
your local provider (implements the two endpoints in docs/provider-api.md)
        |  GET /api/sessions, GET /api/messages  (loopback only)
        v
scripts/http_stats.js   -> computes stats into output/stats_data/<chat>/stats.json
        v
scripts/gen_html.py     -> runs the three generators (dashboard / race / combined)
        v
output/combined.html    -> opened in your browser; the refresh button uses scripts/refresh_server.js
```

Entry point: double-click `start.bat` on Windows (`启动.bat` does the same and additionally registers
the `wechatdash://` protocol used by the refresh button), or run `node scripts/launcher.js` anywhere
(Node 18+).

## Provider contract

Two endpoints, JSON, any language:

| Endpoint | Purpose |
|---|---|
| `GET /api/sessions?limit=N` | List conversations (id, display name, last message time) |
| `GET /api/messages?session_id=X&limit=N&offset=M` | Paginated messages (timestamp, direction, type, content) |

Field-by-field details, message type codes and examples: [`docs/provider-api.md`](docs/provider-api.md).
Reference implementation: [`tools/mock-provider.js`](tools/mock-provider.js) (zero dependencies).

> **Why is there no bundled reader?** Reading an encrypted chat database means extracting a key and
> depending on a specific client build — brittle, unportable, and not something a statistics tool
> should do. This repository owns the part *after* the data: pure stat functions, generators and UI.

## Requirements

- **Node.js 18+** (built-in `fetch`)
- **Python 3** + `pypinyin` for pinyin-aware name ordering: `pip install pypinyin`
- Any OS. On Windows there is also `启动.bat` (one-click entry; it registers the `wechatdash://`
  protocol used by the in-dashboard refresh button).

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `CHAT_PROVIDER_URL` | `http://127.0.0.1:5032` | Address of your local provider |
| `PYTHON` | project `.venv` -> `venv` -> `python` | Interpreter used for HTML generation |
| `PORT` | `5032` | Mock provider port only |

## Project layout

| Path | Purpose |
|---|---|
| `start.bat` | Windows entry point (ASCII name): Node check -> launcher |
| `启动.bat` | Same, plus registration of the `wechatdash://` protocol used by the refresh button |
| `scripts/launcher.js` | Pipeline orchestration (probe provider -> stats -> HTML -> open -> keep refresh service alive) |
| `scripts/http_stats.js` | Pulls from the provider and computes stats into `output/stats_data/*/stats.json` |
| `scripts/gen_html.py` | Adapts the generators to the output directory and runs them in order |
| `scripts/gen_dashboard_html.py`, `gen_race_html.py`, `gen_combined.py` | Dashboard / race / merge |
| `scripts/refresh_server.js` | Local refresh service on `127.0.0.1:8765` |
| `scripts/api_check.js` | Provider health probe (exit 0 = online) |
| `tools/mock-provider.js` | Synthetic provider for demos and tests |
| `docs/provider-api.md` | Provider contract |

## Privacy and security

- **Your data stays local.** The only outbound interaction is a request to a provider on `127.0.0.1`.
- **No telemetry** — no usage reporting, no crash reporting, no accounts.
- **No key handling** — the repository contains no code that decrypts, extracts or copies keys, and
  no third-party runtime binaries.
- **No real data in git** — `.gitignore` covers runtime output and personal config; the bundled demo
  data is synthetic.
- Only use this with data **you are allowed to access**, and never upload someone else's chat history.

## Known limitations

- Dashboard generation needs Python + `pypinyin`; the Node part has no dependencies.
- You must supply and run the provider; if its interface changes, the mapping needs updating.
- Group chats (`@chatroom`) and system accounts are currently excluded from statistics.

## License

[MIT](LICENSE) © 2026 be-abandoned

## Contributing

Issues and pull requests are welcome — read [CONTRIBUTING.md](CONTRIBUTING.md) first, and see
[SECURITY.md](SECURITY.md) for anything security related. **Never include real chat content,
contact names or account ids.**
