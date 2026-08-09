// api_check.js — 检查本地 HTTP 服务是否在线
// 用法: node api_check.js [port]   端口默认 5032 (Wxlens API)
// 探测逻辑:
//   /api/sessions (Wxlens): 200 + body.ok===true -> 在线
//                           200 + ok:false | 503/500 -> 服务在但不可用 -> 离线
//                           404 或网络错误 -> 尝试通用 /
//   / (通用, 如 refresh server): HTTP 200 即在线
// 在线 exit 0, 离线 exit 1
const port = process.argv[2] || '5032';
const base = `http://127.0.0.1:${port}`;
const timeout = setTimeout(() => { console.error('API check timeout'); process.exit(1); }, 3000);

async function check() {
  // 1. Wxlens API probe
  try {
    const res = await fetch(base + '/api/sessions', { signal: AbortSignal.timeout(2000) });
    if (res.status === 200) {
      const j = await res.json().catch(() => null);
      if (j && j.ok === true) { clearTimeout(timeout); process.exit(0); }
      clearTimeout(timeout); process.exit(1); // 200 but ok:false -> unusable
    }
    if (res.status === 503 || res.status === 500) {
      clearTimeout(timeout); process.exit(1); // service up but DB not connected
    }
    // other status (404 etc.) -> not a Wxlens API, fall through
  } catch {}
  // 2. generic root endpoint
  try {
    const res = await fetch(base + '/', { signal: AbortSignal.timeout(2000) });
    if (res.ok) { clearTimeout(timeout); process.exit(0); }
  } catch {}
  clearTimeout(timeout);
  process.exit(1);
}
check();
