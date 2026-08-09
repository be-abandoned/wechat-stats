// refresh_server.js — 看板"刷新数据"后台服务（127.0.0.1:8765）
// 端点:  /          -> 200 (存活探测)
//        /refresh   -> 触发刷新 (异步执行)
//        /progress  -> {pct, step}
//        /stats     -> {since, until, sessions:[{name,delta}]}
const http = require('http');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const PORT = 8765;
const PACK = path.resolve(__dirname, '..');
const SCRIPTS = __dirname;
const NODE = process.execPath;
const PYTHON = process.env.PYTHON || 'python';  // override via env if pypinyin lives in a venv
const STATS_DIR = path.join(PACK, 'output', 'stats_data');
const STATE_FILE = path.join(PACK, 'output', 'refresh_state.json');
const LOG_FILE = path.join(PACK, 'output', 'refresh.log');

function log(s) {
  const line = `[${new Date().toLocaleString('zh-CN', { hour12: false })}] ${s}`;
  try { fs.appendFileSync(LOG_FILE, line + '\n'); } catch {}
}

let state = { running: false, pct: 0, step: '空闲', since: null, until: null, sessions: [] };

function saveState() { try { fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2)); } catch {} }
function loadState() {
  try {
    if (fs.existsSync(STATE_FILE)) state = { ...state, ...JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')) };
  } catch {}
}
loadState();

// 读取所有会话 stats.json -> { username: {name, total} }
function loadTotals() {
  const totals = {};
  try {
    if (!fs.existsSync(STATS_DIR)) return totals;
    for (const dir of fs.readdirSync(STATS_DIR)) {
      const p = path.join(STATS_DIR, dir, 'stats.json');
      if (!fs.existsSync(p)) continue;
      const d = JSON.parse(fs.readFileSync(p, 'utf8'));
      totals[d.username || dir] = { name: d.display || dir, total: d.total || 0 };
    }
  } catch {}
  return totals;
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

async function doRefresh() {
  if (state.running) return;
  state.running = true;
  try {
    const before = loadTotals();
    state.pct = 5; state.step = '正在拉取聊天记录…'; saveState();
    let r = await run(NODE, [path.join(SCRIPTS, 'http_stats.js')]);
    if (r.code !== 0) {
      log('http_stats failed exit=' + r.code + ' out=' + (r.out || '').slice(0, 500));
      state.pct = 100; state.step = '失败：统计生成出错'; saveState();
      setTimeout(() => { state.running = false; state.step = '空闲'; saveState(); }, 3000);
      return;
    }
    log('http_stats ok');
    state.pct = 55; state.step = '正在生成仪表盘…'; saveState();
    r = await run(PYTHON, [path.join(SCRIPTS, 'gen_html.py')]);
    if (r.code !== 0) {
      log('gen_html failed exit=' + r.code + ' out=' + (r.out || '').slice(0, 500));
      state.pct = 100; state.step = '失败：仪表盘生成出错'; saveState();
      setTimeout(() => { state.running = false; state.step = '空闲'; saveState(); }, 3000);
      return;
    }
    log('gen_html ok');
    // 增量对比
    const after = loadTotals();
    const sessions = [];
    for (const [u, v] of Object.entries(after)) {
      const b = before[u];
      const delta = b ? v.total - b.total : v.total;
      if (delta > 0) sessions.push({ name: v.name, delta });
    }
    sessions.sort((a, b) => b.delta - a.delta);
    state.since = state.until || null;
    state.until = new Date().toLocaleString('zh-CN', { hour12: false });
    state.sessions = sessions;
    state.pct = 100; state.step = '完成'; saveState();
    setTimeout(() => { state.running = false; state.step = '空闲'; saveState(); }, 4000);
  } catch (e) {
    log('refresh error: ' + (e && e.stack || e));
    state.pct = 100; state.step = '失败：' + (e.message || '未知错误'); saveState();
    setTimeout(() => { state.running = false; state.step = '空闲'; saveState(); }, 3000);
  }
}

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');
  if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }
  const url = new URL(req.url, 'http://127.0.0.1');
  try {
    if (url.pathname === '/') {
      res.writeHead(200, { 'Content-Type': 'text/plain' }); res.end('ok'); return;
    }
    if (url.pathname === '/refresh') {
      doRefresh();
      res.writeHead(202, { 'Content-Type': 'text/plain' }); res.end('started'); return;
    }
    if (url.pathname === '/progress') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ pct: state.pct, step: state.step })); return;
    }
    if (url.pathname === '/stats') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ since: state.since, until: state.until, sessions: state.sessions })); return;
    }
    res.writeHead(404, { 'Content-Type': 'text/plain' }); res.end('not found');
  } catch (e) {
    res.writeHead(500, { 'Content-Type': 'text/plain' }); res.end('error: ' + e.message);
  }
});

server.on('error', (e) => {
  if (e.code === 'EADDRINUSE') { console.log('refresh server already running'); process.exit(0); }
  console.error('server error:', e.message);
});
server.listen(PORT, '127.0.0.1', () => console.log('refresh server listening on 127.0.0.1:' + PORT));
