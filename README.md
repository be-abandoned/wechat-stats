# 微信聊天统计

本地微信聊天数据统计看板。**HTTP 模式**（推荐）通过 Wxlens 本地 API 读取聊天数据 — **无需提取数据库密钥**。支持**朋友圈文案+点赞**读取。

## 朋友圈（文案 + 点赞）

```bash
# 运行环境: 微信运行中 + Wxlens 已安装（提供 koffi 运行时）
node scripts\sns_timeline.js                 # 最新 20 条
node scripts\sns_timeline.js --limit 50      # 最新 50 条
node scripts\sns_timeline.js --keyword 番茄   # 关键词过滤（如搜自己发的动态）
node scripts\sns_timeline.js --username wxid_xxx
node scripts\sns_timeline.js --raw           # 输出原始 JSON
```

输出格式：每条动态显示 作者 / 时间 / 文案 / 点赞名单（昵称），`--all` 额外显示评论。
技术原理：通过 WCDB 的 `wcdb_get_sns_timeline` API 直读 `db_storage\sns\sns.db` 的 `SnsTimeLine` 表。

## 快速开始（HTTP 模式 — 推荐）

1. **安装 Wxlens** — 从
   [GitHub Release](https://github.com/be-abandoned/wechat-stats/releases/tag/v4.5.0)
   下载（`WxLens-4.5.0-Setup.exe`，直达链接：
   [WxLens-4.5.0-Setup.exe](https://github.com/be-abandoned/wechat-stats/releases/download/v4.5.0/WxLens-4.5.0-Setup.exe)），
   安装后**打开 Wxlens 一次**完成首次初始化（会启动本地 API 服务 `127.0.0.1:5032`）。
2. **确保微信正在运行**且已登录。
3. **双击 `啟動.bat`** — 自动拉取最新统计、生成看板、打开 `output\combined.html`（首次运行会自动注册 `wechatdash://` 协议）。
4. **刷新数据**：再次双击 `啟動.bat`，或点击看板中的 **🔄 刷新** 按钮（由端口 8765 的本地服务支持；启动器会保持其运行，`wechatdash://` 协议让按钮在需要时自动启动它）。

### HTTP 模式 — 工作原理

```
啟動.bat  → launcher.js → 检测 API (127.0.0.1:5032)
      ↓ （离线则自动启动 Wxlens MCP 服务 / 最多等待约 40 秒）
http_stats.js  → 通过 Wxlens HTTP API 拉取会话和消息
      ↓
gen_html.py    → dashboard.html + race.html → combined.html（自动打开）
```

### HTTP 模式 — 环境要求

- Windows 10/11 x64
- **已安装并打开过 Wxlens**（首次初始化会启动 5032 API）
- **微信正在运行且已登录**
- **Node.js 18+**（任何支持全局 `fetch` 的版本；启动脚本从 PATH 查找 `node`，失败则回退到常见安装位置）
- **Python 3** + `pypinyin`（用于 HTML 生成）。启动器优先检测项目本地虚拟环境（`.venv` / `venv`），其次使用 PATH 中的 `python`。安装：`pip install pypinyin`
- 命令行替代方式：`node scripts\launcher.js`（与双击 `啟動.bat` 等效）
- 日志：`output\run.log`（启动器）、`output\refresh.log`（刷新服务）

### 文件说明

| 文件 | 用途 |
|---|---|
| `啟動.bat` | **统一启动入口** — Node 检测 → 协议注册 → 统计 → HTML → 打开看板 |
| `start-dashboard.bat` | 内部：启动刷新服务；同时是 `wechatdash://` 协议处理器（无需手动运行） |
| `scripts/launcher.js` | Node 启动器（HTTP 模式流水线） |
| `scripts/http_stats.js` | 从 Wxlens API 拉取会话/消息，写入 `stats.json` |
| `scripts/refresh_server.js` | `127.0.0.1:8765` 本地刷新服务（看板刷新按钮） |
| `scripts/api_check.js` | 端口健康检查 |
| `setup.bat` | 旧版：从 Wxlens 复制运行时二进制文件（仅旧版路径需要） |

## 旧版路径（直读数据库，需提取密钥）

原始流程直接通过 WCDB 读取微信数据库，需要提取数据库密钥：

```
setup.bat → 从 Wxlens 复制 electron.exe + WCDB DLLs
     ↓
scripts/init.js → 从 Wxlens 配置提取密钥（DPAPI 解密）
     ↓
chat_stats.js → 通过 WCDB 读取微信数据库 → stats.json
     ↓
gen_html.py → dashboard.html + race.html → combined.html
```

> ⚠️ 注意：密钥提取（`init.js`）仍处于实验阶段，部分机器上可能失败。如失败，**改用 HTTP 模式**（见快速开始 — 双击 `啟動.bat`）。

环境要求：已安装 Wxlens（用于运行时二进制文件），`setup.bat` 会在以下位置查找：
`D:\APP\Wxlens`、`%LOCALAPPDATA%\Programs\WxLens`、`C:\Program Files\WxLens`，以及 Windows 注册表中的卸载项。

## 下载 Wxlens

| 来源 | 链接 |
|---|---|
| **GitHub Release（推荐）** | https://github.com/be-abandoned/wechat-stats/releases/tag/v4.5.0 |
| 直链安装包 | https://github.com/be-abandoned/wechat-stats/releases/download/v4.5.0/WxLens-4.5.0-Setup.exe |

## 刷新数据

- HTTP 模式：双击 `啟動.bat`，或点击看板中的 **🔄 刷新** 按钮
- 旧版：删除 `output/` 文件夹，重新运行 `setup.bat` 然后 `scripts/init.js`

## 重新初始化（旧版）

删除 `pack_config.json` 后重新运行 `啟動.bat`（例如更换 Windows 用户后）。

## 隐私说明

所有数据仅在本地处理，不产生任何外部网络请求。源码为明文脚本——可自行审查。
