// 微信聊天统计生成器（可移植版）
// 读取 pack_config.json → 打开微信数据库 → 生成会话 stats.json
// 运行: ELECTRON_RUN_AS_NODE=1 electron.exe chat_stats.js

const path = require('path');
const fs = require('fs');

// ====== 读取配置 ======
const PACK_DIR = path.resolve(__dirname, '..');
const CONFIG_FILE = path.join(PACK_DIR, 'pack_config.json');
if (!fs.existsSync(CONFIG_FILE)) {
  console.log('[ERROR] 未找到 pack_config.json，请先运行初始化');
  process.exit(1);
}
const cfg = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
const ACCOUNT_DIR = cfg.dbPath;
const MY_WXID = cfg.myWxid;
const hexKey = cfg.key;

// 输出目录（可环境变量覆盖）
const OUT_DIR = process.env.OUTPUT_DIR || path.join(PACK_DIR, 'output');
const VAULT = path.join(OUT_DIR, 'stats_data');

const WCDB_DIR = path.join(PACK_DIR, 'wcdb');
const BATCH = 3000;

// ====== 加载依赖 ======
const koffi = require(path.join(PACK_DIR, 'node_modules', 'koffi'));

// WCDB 初始化
try { koffi.load(path.join(WCDB_DIR, 'SDL2.dll')); } catch(e) {}
koffi.load(path.join(WCDB_DIR, 'WCDB.dll'));
const lib = koffi.load(path.join(WCDB_DIR, 'wcdb_api.dll'));

const InitProtection = lib.func('int32 InitProtection(const char* resourcePath)');
const wcdbInit = lib.func('int32 wcdb_init()');
const wcdbOpenAccount = lib.func('int32 wcdb_open_account(const char* path, const char* key, _Out_ int64* handle)');
const wcdbGetSessions = lib.func('int32 wcdb_get_sessions(int64 handle, _Out_ void** outJson)');
const wcdbGetMessages = lib.func('int32 wcdb_get_messages(int64 handle, const char* username, int32 limit, int32 offset, _Out_ void** outJson)');
const wcdbGetMessageCount = lib.func('int32 wcdb_get_message_count(int64 handle, const char* username, _Out_ int32* outCount)');
const wcdbGetDisplayNames = lib.func('int32 wcdb_get_display_names(int64 handle, const char* usernamesJson, _Out_ void** outJson)');
const wcdbFreeString = lib.func('void wcdb_free_string(void* ptr)');
const wcdbShutdown = lib.func('int32 wcdb_shutdown()');
let wcdbSetMyWxid = null;
try { wcdbSetMyWxid = lib.func('int32 wcdb_set_my_wxid(int64 handle, const char* wxid)'); } catch {}

function decodePtr(ptr) { if (!ptr) return null; try { return koffi.decode(ptr, 'char', -1); } catch { return null; } }
function parseFree(ptr) {
  const s = decodePtr(ptr);
  try { if (ptr) wcdbFreeString(ptr); } catch {}
  try { return JSON.parse(s); } catch { return s; }
}

// ====== 工具 ======
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
  const s = String(t);
  if (/^(1[0-9]|2[0-9]){1}/.test(s) && Number(t) > 100000) return '引用/文件';
  return '其他';
}

function sanitizeName(name) { return String(name).replace(/[\\/:*?"<>|]/g, '_').trim(); }

// ====== 统计 ======
function computeStats(messages) {
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

  // 回复间隔
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

  // 主动发起
  const seenDay = new Set(); let myIni=0, otherIni=0;
  for (const m of sorted) {
    const t = parseTime(m.create_time);
    if (seenDay.has(t.date)) continue;
    seenDay.add(t.date);
    const isSelf = String(m.is_send)==='1'||m.sender_username===MY_WXID;
    if(isSelf) myIni++; else otherIni++;
  }

  // 最长连续
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

  // monthCount 序列化
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

// ====== main ======
async function main() {
  // Init WCDB
  const rps = [WCDB_DIR, path.join(WCDB_DIR, '..'), PACK_DIR];
  let ipOk = false;
  for (const rp of rps) { if (InitProtection(rp)===0) { ipOk=true; break; } }
  if (!ipOk) { console.log('InitProtection failed'); return; }
  if (wcdbInit()!==0) { console.log('wcdb_init failed'); return; }

  // Find & open DB
  function findSessionDb(dir, d) {
    if (d>5) return null;
    try {
      for (const e of fs.readdirSync(dir)) {
        const f = path.join(dir, e);
        if (e.toLowerCase()==='session.db' && fs.statSync(f).isFile()) return f;
      }
      for (const e of fs.readdirSync(dir)) {
        const f = path.join(dir, e);
        try { if (fs.statSync(f).isDirectory()) { const r = findSessionDb(f, d+1); if(r) return r; } } catch {}
      }
    } catch {}
    return null;
  }
  const sessionDb = findSessionDb(path.join(ACCOUNT_DIR, 'db_storage'), 0);
  if (!sessionDb) { console.log('找不到 session.db'); return; }

  const handleOut = [0];
  if (wcdbOpenAccount(sessionDb, hexKey, handleOut)!==0) { console.log('数据库打开失败，密钥可能不正确'); return; }
  const handle = handleOut[0];
  try { wcdbSetMyWxid(handle, MY_WXID); } catch {}

  const sp = [null]; wcdbGetSessions(handle, sp);
  const sessions = parseFree(sp[0]) || [];
  console.log('全部会话:', sessions.length);

  // 昵称缓存
  const nameCache = new Map();
  async function resolveName(id) {
    if (nameCache.has(id)) return nameCache.get(id);
    try {
      const p=[null];
      const rc = wcdbGetDisplayNames(handle, JSON.stringify([id]), p);
      if (rc !== 0 || !p[0]) { nameCache.set(id, id); return id; }
      const s = decodePtr(p[0]);
      try { wcdbFreeString(p[0]); } catch {}
      let d = null;
      try { d = JSON.parse(s); } catch {}
      const name = (d && d[id]) || id;
      nameCache.set(id, name);
      return name;
    } catch(e) {
      nameCache.set(id, id);
      return id;
    }
  }

  fs.mkdirSync(VAULT, { recursive: true });
  let done=0, skipped=0;

  const STATS_ONLY = process.env.STATS_ONLY || '';
  for (const s of sessions) {
    const username = s.username||s.session_id||'';
    if (!username||isSystemAccount(username)||username.endsWith('@chatroom')) { skipped++; continue; }
    if (STATS_ONLY && username !== STATS_ONLY) { skipped++; continue; }

    const cntOut=[0]; wcdbGetMessageCount(handle, username, cntOut);
    if (cntOut[0]===0) { skipped++; continue; }

    const display = await resolveName(username);
    const sessDir = sanitizeName(display);

    const all = [];
    for (let off=0; off<cntOut[0]; off+=BATCH) {
      const p=[null];
      if (wcdbGetMessages(handle, username, BATCH, off, p)!==0) break;
      const rows = parseFree(p[0]);
      if (!Array.isArray(rows)) break;
      all.push(...rows);
      if (off+BATCH>=cntOut[0]) break;
    }
    if (!all.length) { skipped++; continue; }

    const st = computeStats(all);
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
    if (done%20===0) console.log(`[${done}] ${display}: ${st.total}条`);
  }

  console.log(`\n=== 统计完成 ===`);
  console.log(`会话: ${done} | 跳过: ${skipped}`);
  console.log(`输出目录: ${VAULT}`);
  wcdbShutdown();
}

main().catch(e => { console.log('ERROR:', e); process.exit(1); });
