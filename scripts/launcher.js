// launcher.js — WeChat Stats pipeline launcher
// Flow: check provider -> fetch stats -> generate HTML -> open dashboard -> ensure refresh service
//
// The data source is a local HTTP provider described in docs/provider-api.md.
// Set CHAT_PROVIDER_URL to point at it (default http://127.0.0.1:5032).
'use strict';

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const PACK = path.resolve(__dirname, '..');
const SCRIPTS = __dirname;
const PROVIDER = (process.env.CHAT_PROVIDER_URL || 'http://127.0.0.1:5032').replace(/\/+$/, '');
const LOG = path.join(PACK, 'output', 'run.log');
const NODE = process.execPath;
const HTML = path.join(PACK, 'output', 'combined.html');

// Python detection: project-local virtualenv first, then anything on PATH.
// gen_html.py needs pypinyin; PYTHON can be set explicitly to a venv interpreter.
function findPython() {
  if (process.env.PYTHON) return process.env.PYTHON;
  const candidates = [
    path.join(PACK, '.venv', 'Scripts', 'python.exe'), // Windows venv
    path.join(PACK, 'venv', 'Scripts', 'python.exe'),
    path.join(PACK, '.venv', 'bin', 'python'),         // Unix venv
    path.join(PACK, 'venv', 'bin', 'python'),
    'python',
  ];
  for (const c of candidates) {
    if (c === 'python') return c;
    try { if (fs.existsSync(c)) return c; } catch { /* ignore */ }
  }
  return 'python';
}
const PYTHON = findPython();

function log(s) {
  const line = `[${new Date().toLocaleString('zh-CN', { hour12: false })}] ${s}`;
  console.log(line);
  try {
    fs.mkdirSync(path.dirname(LOG), { recursive: true });
    fs.appendFileSync(LOG, line + '\n');
  } catch { /* logging must never break the run */ }
}

async function providerUp() {
  try {
    const res = await fetch(PROVIDER + '/api/sessions?limit=1', { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

function run(cmd, args) {
  return new Promise((resolve) => {
    const p = spawn(cmd, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '';
    p.stdout.on('data', d => { out += d; });
    p.stderr.on('data', d => { out += d; });
    p.on('close', code => resolve({ code, out }));
  });
}

// Generate the dashboard; if pypinyin is missing, install it once and retry.
async function runGenHtml() {
  const r = await run(PYTHON, [path.join(SCRIPTS, 'gen_html.py')]);
  if (r.code === 0) return r;
  log('[WARN] HTML generation failed (exit=' + r.code + '), auto-installing pypinyin...');
  const inst = await run(PYTHON, ['-m', 'pip', 'install', '--user', 'pypinyin', '-q']);
  if (inst.out) log(inst.out.trim());
  if (inst.code !== 0) log('[WARN] pip install pypinyin failed (exit=' + inst.code + ')');
  return run(PYTHON, [path.join(SCRIPTS, 'gen_html.py')]);
}

function openDetached(target) {
  if (process.platform === 'win32') {
    spawn('cmd', ['/c', 'start', '""', target], { detached: true, stdio: 'ignore' }).unref();
  } else {
    spawn('xdg-open', [target], { detached: true, stdio: 'ignore' }).unref();
  }
}

async function main() {
  log('===== RUN =====');
  log('provider: ' + PROVIDER);

  if (!(await providerUp())) {
    log('[ERROR] Local chat data provider is not reachable: ' + PROVIDER);
    log('  Start your provider first, or point CHAT_PROVIDER_URL at it.');
    log('  No provider yet? Try the mock provider:  node tools/mock-provider.js');
    process.exit(1);
  }
  log('[OK] provider online');

  log('[1/2] Fetching chat stats...');
  let r = await run(NODE, [path.join(SCRIPTS, 'http_stats.js')]);
  if (r.out) log(r.out.trim());
  if (r.code !== 0) {
    log('[ERROR] Stats generation failed (exit=' + r.code + ')');
    process.exit(1);
  }
  log('[OK] stats done');

  log('[2/2] Generating HTML dashboard... (python=' + PYTHON + ')');
  r = await runGenHtml();
  if (r.out) log(r.out.trim());
  if (r.code !== 0) {
    log('[ERROR] HTML generation failed (exit=' + r.code + ')');
    log('  gen_html.py needs the pypinyin package:  pip install pypinyin');
    log('  (or set PYTHON=/path/to/venv/python and run again)');
    process.exit(1);
  }
  log('[OK] HTML done');

  if (fs.existsSync(HTML)) {
    openDetached(HTML);
    log('[OK] Dashboard opened: ' + HTML);
  } else {
    log('[WARN] combined.html not found: ' + HTML);
  }

  // Keep the refresh service (8765) alive so the in-dashboard Refresh button works.
  try {
    const up = await fetch('http://127.0.0.1:8765/', { signal: AbortSignal.timeout(2000) })
      .then(res => res.ok).catch(() => false);
    if (!up) {
      spawn(NODE, [path.join(SCRIPTS, 'refresh_server.js')], { detached: true, stdio: 'ignore' }).unref();
      log('[OK] refresh server started (8765)');
    } else {
      log('[OK] refresh server already running (8765)');
    }
  } catch {
    log('[WARN] refresh server check failed');
  }

  log('===== DONE =====');
  console.log('\nDone! Dashboard: ' + HTML);
}

main().catch(e => { log('[ERROR] ' + (e && e.message)); process.exit(1); });
