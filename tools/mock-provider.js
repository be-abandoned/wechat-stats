#!/usr/bin/env node
// mock-provider.js — a tiny, dependency-free chat data provider serving SYNTHETIC data.
//
// Purpose: let anyone try WeChat Stats end-to-end without touching a real chat database.
// It implements the same contract documented in docs/provider-api.md, so the rest of the
// pipeline (http_stats.js -> gen_html.py -> combined.html) runs unchanged.
//
// Usage:
//   node tools/mock-provider.js            # listens on 127.0.0.1:5032
//   PORT=5099 node tools/mock-provider.js  # custom port
//
// All data below is fabricated. No network access, no personal data, no files written.
'use strict';

const http = require('http');

const PORT = Number(process.env.PORT || process.env.CHAT_PROVIDER_PORT || 5032);

// --- deterministic PRNG so the demo dashboard is stable across runs -----------------
function mulberry32(seed) {
  return function next() {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const CONTACTS = [
  { username: 'wxid_demo_alex',   display: 'Alex Chen' },
  { username: 'wxid_demo_blair',  display: 'Blair Wu' },
  { username: 'wxid_demo_casey',  display: 'Casey Lin' },
  { username: 'wxid_demo_dana',   display: 'Dana Zhao' },
  { username: 'wxid_demo_emory',  display: 'Emory Sun' },
  { username: 'wxid_demo_frank',  display: 'Frank Qiu' },
  { username: 'wxid_demo_gale',   display: 'Gale He' },
  { username: 'wxid_demo_hana',   display: 'Hana Mori' },
];

const PHRASES = [
  'sounds good, see you then',
  'did you get the file I sent?',
  'let me check and get back to you',
  'meeting moved to 3pm',
  'that build looks broken on my machine',
  'nice work on the release!',
  'can you review the patch when you have time?',
  'lunch tomorrow?',
  'thanks, that fixed it',
  'I pushed the fix, please pull',
  'the numbers do not add up here',
  'ok',
  'haha yes',
  'shipping it friday',
  'do we still need that dependency?',
  'the test suite is green now',
];
const TYPES = [
  [1, 0.84], // text
  [3, 0.93], // image
  [34, 0.96], // voice
  [47, 0.985], // sticker
  [43, 1.0], // video
];

const START = Date.UTC(2024, 0, 1) / 1000;
const END = Date.UTC(2026, 8, 30) / 1000;
const DAY = 86400;

function pickType(r) {
  for (const [type, threshold] of TYPES) if (r < threshold) return type;
  return 1;
}

// Build one conversation: ~2.7 years of messages with day/session structure.
function buildConversation(contact, seedBase) {
  const rnd = mulberry32(seedBase);
  const messages = [];
  let localId = 1;

  for (let day = START; day < END; day += DAY) {
    const skip = rnd();
    if (skip < 0.75) continue; // most days have no conversation

    const sessions = 1 + Math.floor(rnd() * 2);
    let cursor = day + Math.floor(rnd() * 12) * 3600; // first message lands 00:00-12:00

    for (let s = 0; s < sessions; s++) {
      const rounds = 1 + Math.floor(rnd() * 6);
      let selfTurn = rnd() > 0.5;

      for (let k = 0; k < rounds; k++) {
        const burst = 1 + Math.floor(rnd() * 2);
        for (let b = 0; b < burst; b++) {
          const type = pickType(rnd());
          messages.push({
            timestamp: Math.floor(cursor),
            isSelf: selfTurn,
            senderId: selfTurn ? 'me' : contact.username,
            type,
            content: type === 1 ? PHRASES[Math.floor(rnd() * PHRASES.length)] : '',
            localId: localId++,
          });
          cursor += 20 + Math.floor(rnd() * 240); // 20s - 4min between messages
        }
        cursor += 120 + Math.floor(rnd() * 2400); // pause between turns
        selfTurn = !selfTurn;
      }
      cursor += 1800 + Math.floor(rnd() * 14400); // gap between sessions
    }
  }
  return messages;
}

const DATA = new Map();
CONTACTS.forEach((c, i) => {
  const messages = buildConversation(c, 1000 + i * 7919);
  DATA.set(c.username, { contact: c, messages });
});

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(payload),
    'cache-control': 'no-store',
  });
  res.end(payload);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);

  if (url.pathname === '/') {
    res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('mock chat provider\nGET /api/sessions\nGET /api/messages?session_id=...&limit=...&offset=...\n');
    return;
  }

  if (url.pathname === '/api/sessions') {
    const limit = Math.max(1, Math.min(1000, Number(url.searchParams.get('limit') || 1000)));
    const data = [...DATA.values()]
      .sort((a, b) => b.messages[b.messages.length - 1].timestamp - a.messages[a.messages.length - 1].timestamp)
      .slice(0, limit)
      .map(({ contact, messages }) => ({
        username: contact.username,
        sessionId: contact.username,
        displayName: contact.display,
        sessionName: contact.display,
        lastTimestamp: messages[messages.length - 1].timestamp,
        unreadCount: 0,
      }));
    json(res, 200, { ok: true, data });
    return;
  }

  if (url.pathname === '/api/messages') {
    const session = url.searchParams.get('session_id') || '';
    const limit = Math.max(1, Math.min(5000, Number(url.searchParams.get('limit') || 1000)));
    const offset = Math.max(0, Number(url.searchParams.get('offset') || 0));
    const entry = DATA.get(session);
    if (!entry) {
      json(res, 200, { ok: true, data: [] });
      return;
    }
    json(res, 200, { ok: true, data: entry.messages.slice(offset, offset + limit) });
    return;
  }

  json(res, 404, { ok: false, error: 'not found' });
});

server.listen(PORT, '127.0.0.1', () => {
  const total = [...DATA.values()].reduce((n, e) => n + e.messages.length, 0);
  console.log(`mock provider listening on http://127.0.0.1:${PORT}`);
  console.log(`synthetic data: ${CONTACTS.length} conversations, ${total} messages (fabricated)`);
  console.log('now run:  node scripts/launcher.js');
});
