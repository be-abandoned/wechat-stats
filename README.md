# 微信聊天统计 · WeChat Stats

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18-brightgreen)](https://nodejs.org)
[![Python](https://img.shields.io/badge/python-3.x-yellow)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11%20x64-lightgrey)](#环境要求)

> **本地运行的微信聊天数据统计看板。** 所有数据只在你自己电脑上处理，程序不发起任何外部网络请求；读取数据走 Wxlens 的本地 HTTP API，**不需要提取数据库密钥**。
>
> **A local-first WeChat chat statistics dashboard.** Everything runs on your own machine and no data ever leaves it. Messages are read through Wxlens' local HTTP API, so no database key extraction is required.

📖 English documentation: [README.en.md](README.en.md)

---

## 功能

- **私聊 / 群聊统计**：消息条数、按小时与时段分布、活跃度排名，生成可交互的 HTML 看板（`output/combined.html`）。
- **朋友圈读取**（`scripts/sns_timeline.js`）：最新动态的文案与点赞名单，支持按数量、关键词、wxid 过滤。
- **一键启动**：双击 `启动.bat` 完成「检查 Node → 拉取统计 → 生成看板 → 打开浏览器」全流程。
- **看板内刷新**：看板右上角的 🔄 按钮通过 `127.0.0.1:8765` 本地服务重新拉取数据，无需手动重启。
- **完全离线**：除读取本机 Wxlens 服务外不联网，源码为明文脚本，可自行审查。

## 朋友圈（文案 + 点赞）

```bash
# 运行环境：微信运行中 + Wxlens 已安装（提供 koffi 运行时）
node scripts\sns_timeline.js                 # 最新 20 条
node scripts\sns_timeline.js --limit 50      # 最新 50 条
node scripts\sns_timeline.js --keyword 番茄  # 关键词过滤（如搜自己发的动态）
node scripts\sns_timeline.js --username wxid_xxx
node scripts\sns_timeline.js --raw           # 输出原始 JSON
```

输出格式：每条动态显示 作者 / 时间 / 文案 / 点赞名单（昵称），`--all` 额外显示评论。
技术原理：通过 WCDB 的 `wcdb_get_sns_timeline` API 直读 `db_storage\sns\sns.db` 的 `SnsTimeLine` 表。

## 快速开始（HTTP 模式 — 推荐）

1. **安装 Wxlens** — 从 [GitHub Release](https://github.com/be-abandoned/wechat-stats/releases/tag/v4.5.0) 下载 `WxLens-4.5.0-Setup.exe`
   （[直达链接](https://github.com/be-abandoned/wechat-stats/releases/download/v4.5.0/WxLens-4.5.0-Setup.exe)），
   安装后**打开一次**完成首次初始化（会启动本地 API 服务 `127.0.0.1:5032`）。
2. **确保微信正在运行**且已登录。
3. **双击 `启动.bat`** — 自动拉取最新统计、生成看板、打开 `output\combined.html`（首次运行会自动注册 `wechatdash://` 协议）。
4. **刷新数据**：再次双击 `启动.bat`，或点击看板中的 **🔄 刷新** 按钮（由端口 8765 的本地服务支持；启动器会保持其运行，`wechatdash://` 协议让按钮在需要时自动启动它）。

### HTTP 模式 — 工作原理

```
启动.bat  → launcher.js → 检测 API (127.0.0.1:5032)
      ↓ （离线则自动启动 Wxlens MCP 服务 / 最多等待约 40 秒）
http_stats.js  → 通过 Wxlens HTTP API 拉取会话和消息
      ↓
gen_html.py    → dashboard.html + race.html → combined.html（自动打开）
```

### 环境要求

- **Windows 10/11 x64**
- **已安装并打开过 Wxlens**（首次初始化会启动 5032 API）
- **微信正在运行且已登录**
- **Node.js 18+**（任何支持全局 `fetch` 的版本；启动脚本从 PATH 查找 `node`，失败则回退到常见安装位置）
- **Python 3** + `pypinyin`（用于 HTML 生成）。启动器优先检测项目本地虚拟环境（`.venv` / `venv`），其次使用 PATH 中的 `python`。安装：`pip install pypinyin`
- 命令行替代方式：`node scripts\launcher.js`（与双击 `启动.bat` 等效）
- 日志：`output\run.log`（启动器）、`output\refresh.log`（刷新服务）

### 可选：联系人昵称映射

`scripts/wxid_names.json` **不在仓库中**（它包含真实联系人数据）。需要中文昵称时自行创建：

```json
{ "names": { "wxid_example": "备注名" } }
```

文件缺失时看板直接显示 wxid，不影响统计功能。

### 文件说明

| 文件 | 用途 |
|---|---|
| `启动.bat` | **统一启动入口** — Node 检测 → 协议注册 → 统计 → HTML → 打开看板 |
| `start-dashboard.bat` | 内部：启动刷新服务；同时是 `wechatdash://` 协议处理器（无需手动运行） |
| `scripts/launcher.js` | Node 启动器（HTTP 模式流水线） |
| `scripts/http_stats.js` | 从 Wxlens API 拉取会话/消息，写入 `stats.json` |
| `scripts/refresh_server.js` | `127.0.0.1:8765` 本地刷新服务（看板刷新按钮） |
| `scripts/api_check.js` | 端口健康检查 |
| `scripts/sns_timeline.js` | 朋友圈动态读取 |
| `scripts/gen_html.py` 等 | 看板 HTML 生成 |
| `setup.bat` | 旧版：从 Wxlens 复制运行时二进制文件（仅旧版路径需要） |

## 旧版路径（直读数据库，需提取密钥）

> ⚠️ **该路径已不推荐使用**，仅作为历史实现保留。它会从 Wxlens 配置中解密数据库密钥（DPAPI），在部分机器上会失败。

```
setup.bat → 从 Wxlens 复制 electron.exe + WCDB DLLs
     ↓
scripts/init.js → 从 Wxlens 配置提取密钥（DPAPI 解密）
     ↓
chat_stats.js → 通过 WCDB 读取微信数据库 → stats.json
     ↓
gen_html.py → dashboard.html + race.html → combined.html
```

环境要求：已安装 Wxlens（用于运行时二进制文件）。`setup.bat` 会在以下位置查找：
`D:\APP\Wxlens`、`%LOCALAPPDATA%\Programs\WxLens`、`C:\Program Files\WxLens`，以及 Windows 注册表中的卸载项。

## 刷新数据

- HTTP 模式：双击 `启动.bat`，或点击看板中的 **🔄 刷新** 按钮
- 旧版：删除 `output/` 文件夹，重新运行 `setup.bat` 然后 `scripts/init.js`

## 重新初始化（旧版）

删除 `pack_config.json` 后重新运行 `启动.bat`（例如更换 Windows 用户后）。

## 隐私与安全

- **数据不出本机**：所有读写都在本地完成，程序不向任何外部服务器发送数据。
- **不收集遥测**：无统计上报、无崩溃上报、无账号体系。
- **默认不读取数据库密钥**：推荐的 HTTP 模式通过 Wxlens 本地 API 读取；旧版 DPAPI 路径默认不运行。
- **仓库内不含真实聊天数据**：示例看板与联系人映射文件均已从版本库移除，并已加入 `.gitignore`。
- 请只对自己**有权限访问**的微信账号与设备使用本工具，不要上传他人的聊天记录。

## 已知限制

- 仅支持 Windows（依赖 Wxlens 的本地服务与 WCDB 二进制）。
- 依赖第三方的 **Wxlens** 应用；Wxlens 更新后数据接口可能变化。
- 旧版密钥提取路径在部分机器上失败，遇到问题请改用 HTTP 模式。

## 许可证

[MIT](LICENSE) © 2026 be-abandoned

## 贡献

欢迎提交 issue 与 pull request，请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。**提交前请勿包含任何真实聊天数据、联系人昵称或 wxid。**
