// http_stats.js — 通过 Wxlens HTTP API 拉取微信数据生成统计（无需解密数据库）
// 运行: node scripts/http_stats.js   （Node 18+，内置 fetch）
// 输出: output/stats_data/<昵称>/stats.json （与 chat_stats.js 相同结构）

const path = require('path');
const fs = require('fs');

const API = process.env.WX_API || 'http://127.0.0.1:5032';
const PACK_DIR = path.resolve(__dirname, '..');
const OUT_DIR = process.env.OUTPUT_DIR || path.join(PACK_DIR, 'output');
const VAULT = path.join(OUT_DIR, 'stats_data');
const BATCH = 3000;

// ====== 工具（与 chat_stats.js 一致）======
const TZ = 8 * 3600 * 1000;
function parseTime(sec) {
  const d = new Date(Number(sec) * 1000 + TZ);
  const p = n => String(n).padStart(2, '0');
  return {
    date: `${d.getUTCFullYear()}-${p(d.getUTCMonth()+1)}-${p(d.getUTCDate())}`,
    month: `${d.getUTCFullYear()}-${p(d.getUTCMonth()+1)}`,
    hour: d.getUTCHours(),
    ts: Number(sec) * 1000,
  };
}

function isSystemAccount(u) {
  if (!u) return true;
  if (u.startsWith('gh_') || u === 'notifymessage' || u === 'weixin' || u === 'exmail_tool') return true;
  if (u.includes('weixinpay') || u === 'wxpay') return true;
  if (u.endsWith('@openim') || u.endsWith('@kefu.openim')) return true;
  return false;
}

function median(arr) {
  if (!arr.length) return null;
  const s = [...arr].sort((a,b)=>a-b);
  const mid = Math.floor(s.length/2);
  return s.length%2 ? s[mid] : (s[mid-1]+s[mid])/2;
}

const TYPE_LABELS = {1:'文本',3:'图片',34:'语音',43:'视频',47:'表情',48:'位置',49:'链接/文件',50:'通话',10000:'系统消息',10002:'系统消息'};
function typeLabel(t) {
  const n = Number(t);
  if (TYPE_LABELS[n] !== undefined) return TYPE_LABELS[n];
  return '其他';
}

function sanitizeName(name) { return String(name).replace(/[\\/:*?"<>|]/g, '_').trim(); }

async function api(pathname) {
  const url = `${API}${pathname}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API ${pathname} -> HTTP ${res.status}`);
  const j = await res.json();
  if (!j.ok) throw new Error(`API ${pathname} -> ${JSON.stringify(j).slice(0,200)}`);
  return j.data;
}

// ====== 统计（与 chat_stats.js 的 computeStats 一致，字段已映射）======
function computeStats(messages, MY_WXID) {
  const st = {
    total: messages.length, mySend: 0, otherSend: 0,
    activeDays: new Set(),
    hourCount: Array(24).fill(0),
    dayCount: {},
    monthCount: {},
    typeCount: {},
    textLen: [], maxTextLen: 0,
    replyGapsMy: [], replyGapsOther: [],
    firstTs: null, lastTs: null,
  };

  for (const m of messages) {
    const t = parseTime(m.create_time);
    const isSelf = String(m.is_send)==='1' || m.sender_username===MY_WXID;
    if (isSelf) st.mySend++; else st.otherSend++;
    st.activeDays.add(t.date);
    st.hourCount[t.hour]++;
    st.dayCount[t.date] = (st.dayCount[t.date]||0)+1;

    if (!st.monthCount[t.month]) {
      st.monthCount[t.month] = { total:0, my:0, other:0, act:new Set(), myD:new Set(), otD:new Set(), types:{}, hours:Array(24).fill(0) };
    }
    const mm = st.monthCount[t.month];
    mm.total++; if(isSelf) mm.my++; else mm.other++;
    mm.act.add(t.date);
    if(isSelf) mm.myD.add(t.date); else mm.otD.add(t.date);
    const tl = typeLabel(m.local_type);
    mm.types[tl] = (mm.types[tl]||0)+1;
    mm.hours[t.hour]++;

    st.typeCount[tl] = (st.typeCount[tl]||0)+1;
    if (Number(m.local_type)===1) {
      const len = String(m.message_content||'').length;
      st.textLen.push(len);
      if (len>st.maxTextLen) st.maxTextLen=len;
    }
    if (st.firstTs===null || t.ts<st.firstTs) st.firstTs=t.ts;
    if (st.lastTs===null || t.ts>st.lastTs) st.lastTs=t.ts;
  }

  st.activeDays = st.activeDays.size;

  const sorted = [...messages].sort((a,b)=>Number(a.create_time)-Number(b.create_time)||Number(a.local_id)-Number(b.local_id));
  for (let i=0;i<sorted.length-1;i++) {
    const cSelf = String(sorted[i].is_send)==='1'||sorted[i].sender_username===MY_WXID;
    const nSelf = String(sorted[i+1].is_send)==='1'||sorted[i+1].sender_username===MY_WXID;
    if (cSelf!==nSelf) {
      const gap = (Number(sorted[i+1].create_time)-Number(sorted[i].create_time))*1000;
      if (gap>0 && gap<=12*3600*1000) {
        if(cSelf) st.replyGapsMy.push(gap); else st.replyGapsOther.push(gap);
      }
    }
  }

  const seenDay = new Set(); let myIni=0, otherIni=0;
  for (const m of sorted) {
    const t = parseTime(m.create_time);
    if (seenDay.has(t.date)) continue;
    seenDay.add(t.date);
    const isSelf = String(m.is_send)==='1'||m.sender_username===MY_WXID;
    if(isSelf) myIni++; else otherIni++;
  }

  const dates = [...new Set(sorted.map(m=>parseTime(m.create_time).date))].sort();
  let best={len:0,start:'',end:''}, curLen=0, curStart='';
  for (let i=0;i<dates.length;i++) {
    if (i===0||Math.round((new Date(dates[i])-new Date(dates[i-1]))/86400000)===1) {
      if(curLen===0) curStart=dates[i];
      curLen++;
    } else {
      if(curLen>best.len) best={len:curLen,start:curStart,end:dates[i-1]};
      curLen=1;curStart=dates[i];
    }
  }
  if(curLen>best.len) best={len:curLen,start:curStart,end:dates[dates.length-1]};
  const spanDays = st.firstTs&&st.lastTs ? Math.round((st.lastTs-st.firstTs)/86400000) : 0;

  const MONTH_TYPES = ['文本','图片','表情','视频','语音','通话'];
  for (const m of Object.keys(st.monthCount)) {
    const mm = st.monthCount[m];
    const seg = [0,0,0,0];
    for (let h=0;h<24;h++) seg[h>=2&&h<8?0:h>=8&&h<14?1:h>=14&&h<20?2:3] += mm.hours[h];
    const mo = {total:mm.total,my:mm.my,other:mm.other,activeDays:mm.act.size,myIni:mm.myD.size,otherIni:mm.otD.size,seg};
    for (const t of MONTH_TYPES) mo[t] = mm.types[t]||0;
    st.monthCount[m] = mo;
  }

  return {
    ...st,
    myIni, otherIni, bestStreak:best, spanDays,
    avgDaily: st.activeDays ? (st.total/st.activeDays).toFixed(1) : '0',
    textAvg: st.textLen.length ? (st.textLen.reduce((a,b)=>a+b,0)/st.textLen.length).toFixed(0) : '—',
    replyMedianMy: median(st.replyGapsMy), replyMeanMy: st.replyGapsMy.length ? st.replyGapsMy.reduce((a,b)=>a+b,0)/st.replyGapsMy.length : null,
    replyMedianOther: median(st.replyGapsOther), replyMeanOther: st.replyGapsOther.length ? st.replyGapsOther.reduce((a,b)=>a+b,0)/st.replyGapsOther.length : null,
    reply1hMy: st.replyGapsMy.length ? st.replyGapsMy.filter(g=>g<3600000).length/st.replyGapsMy.length : null,
    reply1hOther: st.replyGapsOther.length ? st.replyGapsOther.filter(g=>g<3600000).length/st.replyGapsOther.length : null,
  };
}

// ====== 字段映射：HTTP API -> chat_stats.js 内部字段 ======
function mapMsg(m) {
  return {
    create_time: String(m.timestamp),
    is_send: m.isSelf ? '1' : (m.isSend !== undefined ? String(m.isSend) : '0'),
    sender_username: m.senderId || '',
    local_type: String(m.type !== undefined ? m.type : m.typeName),
    message_content: m.content || '',
    local_id: m.localId || 0,
  };
}

// ====== main ======
async function main() {
  console.log(`连接 API: ${API}`);
  const sessions = await api('/api/sessions?limit=1000');
  console.log('全部会话:', sessions.length);

  // 尝试读取 pack_config.json 获取 myWxid（可选）
  let MY_WXID = '';
  try {
    const cfgPath = path.join(PACK_DIR, 'pack_config.json');
    if (fs.existsSync(cfgPath)) MY_WXID = JSON.parse(fs.readFileSync(cfgPath,'utf8')).myWxid || '';
  } catch {}

  fs.mkdirSync(VAULT, { recursive: true });
  let done=0, skipped=0;

  for (const s of sessions) {
    const username = s.username || s.sessionId || '';
    const display = (s.displayName || s.sessionName || username).trim();
    if (!username || isSystemAccount(username) || username.endsWith('@chatroom')) { skipped++; continue; }
    if (username === MY_WXID) { skipped++; continue; } // 跳过自己
    if (s.unreadCount === undefined && !s.lastTimestamp) { /* 保留，仍有消息 */ }

    // 分页拉全量消息
    const all = [];
    for (let off = 0; ; off += BATCH) {
      const rows = await api(`/api/messages?session_id=${encodeURIComponent(username)}&limit=${BATCH}&offset=${off}`);
      if (!rows || !rows.length) break;
      all.push(...rows.map(mapMsg));
      if (rows.length < BATCH) break;
    }
    if (!all.length) { skipped++; continue; }

    const st = computeStats(all, MY_WXID);
    const sessDir = sanitizeName(display);
    const jsonPath = path.join(VAULT, sessDir, 'stats.json');
    fs.mkdirSync(path.dirname(jsonPath), { recursive: true });
    fs.writeFileSync(jsonPath, JSON.stringify({
      username, display,
      total: st.total, mySend: st.mySend, otherSend: st.otherSend,
      activeDays: st.activeDays, spanDays: st.spanDays, avgDaily: st.avgDaily,
      myIni: st.myIni, otherIni: st.otherIni, bestStreak: st.bestStreak,
      replyMedianMy: st.replyMedianMy, replyMedianOther: st.replyMedianOther,
      replyMeanMy: st.replyMeanMy, replyMeanOther: st.replyMeanOther,
      reply1hMy: st.reply1hMy, reply1hOther: st.reply1hOther,
      textAvg: st.textAvg, maxTextLen: st.maxTextLen,
      firstTs: st.firstTs, lastTs: st.lastTs,
      monthCount: st.monthCount, hourCount: st.hourCount,
      typeCount: st.typeCount, dayCount: st.dayCount,
    }, null, 2), 'utf8');

    done++;
    console.log(`[${done}] ${display}: ${st.total}条`);
  }

  console.log(`\n=== 统计完成 ===`);
  console.log(`会话: ${done} | 跳过: ${skipped}`);
  console.log(`输出目录: ${VAULT}`);
}

main().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
