// launcher.js — WeChat Stats 启动器（Node 版，替代复杂 bat 逻辑）
// 职责: 检查 API -> 必要时自动拉起 MCP 服务 -> 拉统计 -> 生成 HTML -> 打开看板
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const PACK = path.resolve(__dirname, '..');
const SCRIPTS = __dirname;
const API = process.env.WX_API || 'http://127.0.0.1:5032';
const LOG = path.join(PACK, 'output', 'run.log');
const NODE = process.execPath;
const PYTHON = process.env.PYTHON || 'python';  // override via env if pypinyin lives in a venv
const MCP_START = path.join(process.env.LOCALAPPDATA || '', 'Programs', 'WxLens', 'resources', 'wxlens-mcp', 'start.cmd');
const HTML = path.join(PACK, 'output', 'combined.html');

function log(s) {
  const line = `[${new Date().toLocaleString('zh-CN', { hour12: false })}] ${s}`;
  console.log(line);
  try {
    fs.mkdirSync(path.dirname(LOG), { recursive: true });
    fs.appendFileSync(LOG, line + '\n');
  } catch {}
}

async function apiUp() {
  try {
    const res = await fetch(API + '/api/sessions', { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch { return false; }
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

function openDetached(target) {
  spawn('cmd', ['/c', 'start', '""', target], { detached: true, stdio: 'ignore' }).unref();
}

async function main() {
  log('===== RUN =====');

  // 1. API check
  if (!(await apiUp())) {
    log('API offline, auto-starting MCP service...');
    if (fs.existsSync(MCP_START)) {
      openDetached(MCP_START);
    } else {
      log('[ERROR] start.cmd not found: ' + MCP_START);
      process.exit(1);
    }
    // 2. wait up to ~40s
    let ok = false;
    for (let i = 1; i <= 20; i++) {
      await new Promise(r => setTimeout(r, 2000));
      if (await apiUp()) { ok = true; break; }
      if (i % 5 === 0) log(`  waiting for API... ${i * 2}s`);
    }
    if (!ok) {
      log('[ERROR] Wxlens API did not start. Please open Wxlens once and make sure WeChat is running.');
      process.exit(1);
    }
  }
  log('[OK] Wxlens API online');

  // 3. fetch stats
  log('[1/2] Fetching chat stats...');
  let r = await run(NODE, [path.join(SCRIPTS, 'http_stats.js')]);
  if (r.out) log(r.out.trim());
  if (r.code !== 0) { log('[ERROR] Stats generation failed (exit=' + r.code + ')'); process.exit(1); }
  log('[OK] Stats done');

  // 4. generate HTML
  log('[2/2] Generating HTML dashboard...');
  r = await run(PYTHON, [path.join(SCRIPTS, 'gen_html.py')]);
  if (r.out) log(r.out.trim());
  if (r.code !== 0) { log('[ERROR] HTML generation failed (exit=' + r.code + ')'); process.exit(1); }
  log('[OK] HTML done');

  // 5. open dashboard
  if (fs.existsSync(HTML)) {
    openDetached(HTML);
    log('[OK] Dashboard opened: ' + HTML);
  } else {
    log('[WARN] combined.html not found: ' + HTML);
  }

  // 6. ensure refresh server (8765) is running for the in-dashboard Refresh button
  try {
    const up = await fetch('http://127.0.0.1:8765/', { signal: AbortSignal.timeout(2000) }).then(r => r.ok).catch(() => false);
    if (!up) {
      spawn(NODE, [path.join(SCRIPTS, 'refresh_server.js')], { detached: true, stdio: 'ignore' }).unref();
      log('[OK] refresh server started (8765)');
    } else {
      log('[OK] refresh server already running (8765)');
    }
  } catch { log('[WARN] refresh server check failed'); }

  log('===== DONE =====');
  console.log('\nDone! Dashboard: ' + HTML);
}

main().catch(e => { log('[ERROR] ' + (e && e.message)); process.exit(1); });
