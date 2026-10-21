# 微信聊天统计 · WeChat Stats

[![CI](https://github.com/be-abandoned/wechat-stats/actions/workflows/ci.yml/badge.svg)](https://github.com/be-abandoned/wechat-stats/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18-brightgreen)](https://nodejs.org)
[![Python](https://img.shields.io/badge/python-3.x-yellow)](https://www.python.org)

> **把一段聊天记录变成可以看的统计看板。** 数据全部在你自己机器上处理，不联网、不上传、无遥测。
> 程序本身不读取任何加密数据库——它只向**本地 HTTP 数据源**要 JSON，数据源由你自己提供。
>
> **Turn a chat export into a readable statistics dashboard.** Everything runs on your machine:
> no network calls, no uploads, no telemetry. The project never touches an encrypted database —
> it reads JSON from a local HTTP provider that you supply.

📖 English documentation: [README.en.md](README.en.md)

---

## 30 秒试用（不需要任何真实数据）

仓库自带一个**合成数据**的演示数据源，克隆下来就能跑出完整看板：

```bash
node tools/mock-provider.js      # 终端 A：合成数据源，127.0.0.1:5032
npm start                        # 终端 B：拉统计 → 生成看板 → 打开 output/combined.html
```

演示数据是随机生成的 8 个会话、约 1.5 万条消息，标识全部是 `wxid_demo_*`，不含任何真实内容。

## 它做什么

- **会话统计**：消息总数、收发比例、活跃天数、连续聊天天数、平均每天条数、平均文本长度。
- **时间分布**：24 小时分布、时段（凌晨/上午/下午/晚上）占比、逐月趋势。
- **回复行为**：回复间隔中位数与均值、一小时内回复比例。
- **频率排行**（Bar Chart Race）：逐日滚动的近 30 天热度 Top10 动画。
- **交互看板**：单个自包含 HTML（`output/combined.html`），可离线打开；内置 🔄 刷新按钮，通过 `127.0.0.1:8765` 本地服务重新拉数据。

## 架构

```
你的本地数据源（实现 docs/provider-api.md 的两个接口）
        │  GET /api/sessions、GET /api/messages（仅 127.0.0.1）
        ▼
scripts/http_stats.js   → 计算统计，写入 output/stats_data/<会话>/stats.json
        ▼
scripts/gen_html.py     → 调用三个生成器（看板 / 排行 / 合并）
        ▼
output/combined.html    → 浏览器打开；🔄 按钮由 scripts/refresh_server.js 支撑
```

启动入口：Windows 双击 `start.bat`（`启动.bat` 额外注册 `wechatdash://` 协议，供看板刷新按钮使用），
或任意平台 `node scripts/launcher.js`。

## 数据源契约

只有两个接口，返回 JSON 即可，语言不限：

| 接口 | 作用 |
|---|---|
| `GET /api/sessions?limit=N` | 会话列表（id、显示名、最后消息时间） |
| `GET /api/messages?session_id=X&limit=N&offset=M` | 该会话的消息分页（时间戳、是否本人、类型、内容） |

完整字段、类型码与示例见 [`docs/provider-api.md`](docs/provider-api.md)；
参考实现见 [`tools/mock-provider.js`](tools/mock-provider.js)（零依赖）。

> **为什么不自带读取器？** 直接读聊天数据库需要绕过加密、提取密钥，那类代码既脆弱又不可移植，
> 也不该出现在一个统计工具里。本仓库只保留「拿到数据之后」的部分：纯函数式的统计、生成与展示。

## 环境要求

- **Node.js 18+**（内置 `fetch`）
- **Python 3** + `pypinyin`（生成看板时用于拼音排序）：`pip install pypinyin`
- 任意操作系统；Windows 上额外提供 `启动.bat` 一键入口（含 `wechatdash://` 协议注册，供看板刷新按钮使用）

## 配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| `CHAT_PROVIDER_URL` | `http://127.0.0.1:5032` | 本地数据源地址 |
| `PYTHON` | 项目内 `.venv` → `venv` → `python` | HTML 生成使用的解释器 |
| `PORT` | `5032` | 仅演示数据源使用的监听端口 |

## 文件说明

| 文件 | 用途 |
|---|---|
| `start.bat` | Windows 入口（ASCII 文件名）：检查 Node → 启动器 |
| `启动.bat` | 同上，并注册 `wechatdash://` 协议（看板刷新按钮使用） |
| `scripts/launcher.js` | 流水线编排（检查数据源 → 统计 → 生成 → 打开 → 保活刷新服务） |
| `scripts/http_stats.js` | 从数据源拉取并计算统计，产物 `output/stats_data/*/stats.json` |
| `scripts/gen_html.py` | 把生成器适配到输出目录并依次运行 |
| `scripts/gen_dashboard_html.py` / `gen_race_html.py` / `gen_combined.py` | 看板 / 排行动画 / 合并 |
| `scripts/refresh_server.js` | `127.0.0.1:8765` 本地刷新服务 |
| `scripts/api_check.js` | 数据源健康检查（退出码 0 = 在线） |
| `tools/mock-provider.js` | 合成数据源，用于演示与测试 |
| `docs/provider-api.md` | 数据源接口契约 |

## 隐私与安全

- **数据不出本机**：唯一的外部交互是向 `127.0.0.1` 的本地数据源取数。
- **不收集遥测**：无上报、无账号体系、无崩溃收集。
- **不接触密钥/数据库**：仓库内没有任何解密、提取密钥或复制第三方运行时的代码。
- **仓库不含真实数据**：`.gitignore` 覆盖运行产物与个人配置；演示数据是合成的。
- 只对**你有权限访问**的数据使用本工具；不要上传他人的聊天记录。

## 已知限制

- 看板生成依赖 Python + `pypinyin`；Node 部分零依赖。
- 数据源需要你自己提供并保持运行；接口变更时统计口径需自行对齐。
- 群聊（`@chatroom`）与系统账号目前不计入统计。

## 许可证

[MIT](LICENSE) © 2026 be-abandoned

## 贡献

欢迎 issue 与 PR，请先读 [CONTRIBUTING.md](CONTRIBUTING.md)；安全问题见 [SECURITY.md](SECURITY.md)。
**提交前请勿包含任何真实聊天内容、联系人昵称或账号 id。**
