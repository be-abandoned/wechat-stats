// api_check.js — probe whether the local chat data provider is online.
// Usage: node api_check.js [port]      port defaults to 5032
// Probe order:
//   GET /api/sessions -> 200 with body.ok === true   -> online
//                        200 with ok:false, or 5xx    -> service up but unusable -> offline
//                        404 / network error          -> fall back to GET /
//   GET /            -> HTTP 2xx                     -> online
// Exit code 0 = online, 1 = offline.
'use strict';

const port = process.argv[2] || process.env.CHAT_PROVIDER_PORT || '5032';
const base = `http://127.0.0.1:${port}`;
const timeout = setTimeout(() => { console.error('API check timeout'); process.exit(1); }, 3000);

async function check() {
  // 1. provider data endpoint
  try {
    const res = await fetch(base + '/api/sessions?limit=1', { signal: AbortSignal.timeout(2000) });
    if (res.status === 200) {
      const j = await res.json().catch(() => null);
      clearTimeout(timeout);
      process.exit(j && j.ok === true ? 0 : 1);
    }
    if (res.status >= 500) {
      clearTimeout(timeout);
      process.exit(1); // service answers but the data layer is not usable
    }
    // 404 and friends: not a data provider, try the generic root below
  } catch { /* unreachable, try root */ }

  // 2. generic root endpoint (any HTTP service that answers)
  try {
    const res = await fetch(base + '/', { signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      clearTimeout(timeout);
      process.exit(0);
    }
  } catch { /* offline */ }

  clearTimeout(timeout);
  process.exit(1);
}

check();
