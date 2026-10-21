# Contributing

Thanks for taking a look at WeChat Stats! This is a small, local-first tool, so the contribution
process is deliberately light.

## Before you open an issue

- Check that you are on the latest commit of `main`.
- Make sure **WeChat is running and logged in**, and that **Wxlens is installed and initialised**
  (its local API should answer on `127.0.0.1:5032`). The launcher logs to `output\run.log`; the
  refresh service logs to `output\refresh.log`.
- **Never paste real chat content, contact names or wxids.** Replace them with `wxid_example` and
  a made-up message before posting logs or screenshots.

## Reporting a bug

Please include:

1. Windows version, Node.js version (`node -v`), Python version (`python -V`).
2. Wxlens version.
3. The relevant part of `output\run.log`, with personal data removed.
4. What you expected and what actually happened.

## Pull requests

- Keep changes focused; one topic per pull request.
- Match the existing style: plain Node.js (CommonJS) scripts, no build step, no new runtime
  dependencies unless they are unavoidable.
- **Do not commit generated artefacts** — `output/`, `static/`, `pack_config.json` and
  `scripts/wxid_names.json` are ignored and must stay that way. Sample data must be fully
  anonymised.
- If you touch the legacy key-extraction path (`scripts/init.js`, `setup.bat`), state clearly in the
  pull request why it is still needed; the HTTP mode is the supported path.
- By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).

## Security issues

Please **do not** open a public issue for anything that could expose user data (for example a code
path that uploads data, or a way to read another user's chat history). Report it privately to the
maintainer through the contact address on the GitHub profile instead.

---

# 贡献指南（中文）

- 提交 issue 前请确认：微信在运行并已登录、Wxlens 已安装并初始化（`127.0.0.1:5032` 可访问）。
- **任何日志、截图、示例数据都必须去除真实的聊天内容、联系人昵称与 wxid**。
- 一个 PR 只做一件事，保持现有风格：纯 Node.js 脚本、无构建步骤、尽量不新增运行时依赖。
- 不要提交生成产物：`output/`、`static/`、`pack_config.json`、`scripts/wxid_names.json` 已在
  `.gitignore` 中，请保持。
- 贡献代码即表示同意以 [MIT 许可证](LICENSE) 授权。
- 涉及数据泄露风险的问题请勿公开提 issue，直接私下联系维护者。
