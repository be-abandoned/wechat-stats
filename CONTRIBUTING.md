# Contributing

Thanks for taking a look at WeChat Stats! It is a small, local-first tool, so the process is
deliberately light.

## Scope

The project owns everything **after** the data arrives: statistics, HTML generation and the local
refresh service. It does **not** read databases, decrypt keys or bundle third-party runtimes, and it
will not start doing so — data comes from a local provider described in
[`docs/provider-api.md`](docs/provider-api.md). If you want to support a new data source, implement
that contract instead of adding a reader here.

## Before you open an issue

- Run against the synthetic provider first — it reproduces most problems without any private data:

  ```bash
  node tools/mock-provider.js          # terminal A
  npm start                            # terminal B
  ```

- Check the logs: `output/run.log` (launcher), `output/refresh.log` (refresh service).

## Reporting a bug

Please include:

1. OS and version, Node.js version (`node -v`), Python version (`python -V`).
2. Whether the issue reproduces with `tools/mock-provider.js` (this tells us if it is data-related).
3. The relevant part of `output/run.log`.
4. What you expected and what actually happened.

**Never paste real chat content, contact names or account ids.** Replace them with
`wxid_example` / made-up text before posting logs or screenshots.

## Pull requests

- Keep changes focused; one topic per pull request.
- Match the existing style: plain Node.js (CommonJS), no build step, no runtime dependencies unless
  unavoidable. Python stays compatible with the import-only generators in `scripts/`.
- Add or update the corresponding section of both `README.md` and `README.en.md` if behaviour changes.
- CI (`.github/workflows/ci.yml`) runs syntax checks plus the full pipeline against the synthetic
  provider. A pull request should stay green.
- **Do not commit generated artefacts or personal data** — `output/`, `static/`, `pack_config.json`,
  `scripts/wxid_names.json` and `*.stats.json` are ignored and must stay that way. Fixtures must be
  fully synthetic.
- By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).

## Security

Do not open a public issue for anything that could expose user data. See [SECURITY.md](SECURITY.md).

---

# 贡献指南（中文）

- **边界**：本项目只负责「数据到手之后」——统计、HTML 生成、本地刷新服务；不读数据库、不解密密钥、
  不打包第三方运行时。新增数据源请实现 [`docs/provider-api.md`](docs/provider-api.md) 的接口。
- 提 issue 前先用合成数据源复现：`node tools/mock-provider.js` + `npm start`；日志在 `output/run.log`。
- **任何日志、截图、示例数据都必须去除真实聊天内容、联系人昵称与账号 id**。
- 一个 PR 只做一件事；保持现有风格（CommonJS、无构建步骤、尽量零依赖）；行为变更请同步更新
  `README.md` 与 `README.en.md`；CI 需要保持通过。
- 不要提交生成产物与个人数据：`output/`、`static/`、`pack_config.json`、`scripts/wxid_names.json`、
  `*.stats.json` 已在 `.gitignore` 中。
- 贡献代码即表示同意以 [MIT 许可证](LICENSE) 授权；安全问题请见 [SECURITY.md](SECURITY.md)。
