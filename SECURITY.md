# Security policy

## Scope

WeChat Stats renders statistics from chat data that a **local provider** hands it over HTTP on
`127.0.0.1`. The project itself never reads a database, never decrypts anything, and never sends
data off the machine. Reports are welcome for anything that breaks one of those statements, for
example:

- a code path that sends data to a non-loopback host;
- a provider response that can inject script into the generated dashboard (XSS);
- path traversal or arbitrary file writes driven by provider-supplied names;
- crashing or writing outside `output/` when a provider returns malformed JSON.

Out of scope: how a third-party provider obtains the data, and any tool that extracts or decrypts
another application's database key — this repository deliberately contains none of that.

## Reporting

Please **do not** open a public issue for a vulnerability, and never include real chat content,
contact names or account ids in a report.

Report privately through the contact address on the [maintainer's GitHub
profile](https://github.com/be-abandoned) and include:

1. Affected commit or version.
2. A minimal reproduction (a mock payload is ideal — the pipeline accepts any provider, so a fake
   provider is enough to demonstrate most issues).
3. Impact: what data or code is exposed, and to whom.

You can expect an acknowledgement within a week for a concrete report. There is no bounty; credit
is given in the fix commit unless you prefer otherwise.

## Data hygiene in this repository

- No real chat export, contact name or account id may be committed. `.gitignore` covers the local
  outputs (`output/`, `scripts/wxid_names.json`, `static/`).
- `tools/mock-provider.js` is the only bundled data source and it is entirely synthetic.
- If you discover personal data in the history, report it the same way rather than opening an issue.
