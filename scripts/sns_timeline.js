// 朋友圈时间线读取脚本（文案 + 点赞记录）
// 用法:
//   node scripts/sns_timeline.js                    # 最新 20 条
//   node scripts/sns_timeline.js --limit 50         # 最新 50 条
//   node scripts/sns_timeline.js --keyword 番茄     # 按关键词过滤
//   node scripts/sns_timeline.js --username wxid_xxx
//   node scripts/sns_timeline.js --raw              # 输出原始 JSON
// 运行环境: 需要微信运行中 + Wxlens 已装（提供 electron + koffi + wcdb_api.dll）
const path = require('path');
const fs = require('fs');
const os = require('os');

// ====== 命令行参数 ======
const args = process.argv.slice(2);
function getArg(name, def) {
  const i = args.indexOf('--' + name);
  return i >= 0 && args[i + 1] ? args[i + 1] : def;
}
const LIMIT = parseInt(getArg('limit', '20'), 10);
const USERNAME = getArg('username', '');
const KEYWORD = getArg('keyword', '');
const RAW = args.includes('--raw');
const ALL = args.includes('--all');

// ====== 定位运行时（koffi + electron + DLL）=====
const PROJECT_DIR = path.resolve(__dirname, '..');
const WXLENS_CANDIDATES = [
  process.env.WXLENS_DIR,
  'D:\\APP\\Wxlens',
  path.join(os.homedir(), 'AppData', 'Local', 'Programs', 'WxLens'),
  'C:\\Program Files\\WxLens',
].filter(Boolean);

function findWxlens() {
  for (const dir of WXLENS_CANDIDATES) {
    if (fs.existsSync(path.join(dir, 'electron.exe'))) return dir;
  }
  return null;
}

function loadKoffi(wxlens) {
  const tryPaths = [
    path.join(PROJECT_DIR, 'node_modules', 'koffi'),
    path.join(wxlens, 'resources', 'app.asar.unpacked', 'node_modules', 'koffi'),
    path.join(wxlens, 'resources', 'app.asar.unpacked', 'tools', 'wx-mcp-server', 'node_modules', 'koffi'),
  ];
  for (const p of tryPaths) {
    try { return require(p); } catch {}
  }
  throw new Error('未找到 koffi 模块，请先运行 setup.bat 或安装 Wxlens');
}

function findDllDir(wxlens) {
  const candidates = [
    path.join(wxlens, 'resources', 'resources', 'wcdb', 'win32', 'x64'),
    path.join(PROJECT_DIR, 'wcdb'),
  ];
  for (const d of candidates) {
    if (fs.existsSync(path.join(d, 'wcdb_api.dll'))) return d;
  }
  throw new Error('未找到 wcdb_api.dll');
}

// ====== 密钥获取 ======
function getKey() {
  // 1. 项目配置
  const cfgPath = path.join(PROJECT_DIR, 'pack_config.json');
  if (fs.existsSync(cfgPath)) {
    try {
      const c = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
      if (c.key && c.key.length >= 64) return c.key;
    } catch {}
  }
  // 2. 环境变量
  if (process.env.WX_DB_KEY && process.env.WX_DB_KEY.length >= 64) return process.env.WX_DB_KEY;
  // 3. 本地密钥文件（开发用）
  for (const p of [
    path.join(os.homedir(), '.workbuddy', 'db_key.txt'),
    path.join(PROJECT_DIR, 'db_key.txt'),
  ]) {
    try {
      const k = fs.readFileSync(p, 'utf8').trim();
      if (k.length >= 64) return k;
    } catch {}
  }
  throw new Error('未找到数据库密钥，请先运行初始化（启动.bat）或设置 WX_DB_KEY');
}

function findAccountDir() {
  const cfgPath = path.join(PROJECT_DIR, 'pack_config.json');
  if (fs.existsSync(cfgPath)) {
    try {
      const c = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
      if (c.dbPath && fs.existsSync(c.dbPath)) return c.dbPath;
    } catch {}
  }
  // 自动查找 xwechat_files
  for (const drive of ['D:', 'C:', 'E:']) {
    const dir = drive + '\\xwechat_files';
    if (!fs.existsSync(dir)) continue;
    for (const entry of fs.readdirSync(dir)) {
      const full = path.join(dir, entry);
      if (entry.startsWith('wxid_') && fs.statSync(full).isDirectory() && fs.existsSync(path.join(full, 'db_storage'))) {
        return full;
      }
    }
  }
  throw new Error('未找到微信数据目录');
}

// ====== WCDB 初始化 ======
function findSessionDb(dir, d) {
  if (d > 6) return null;
  try {
    for (const e of fs.readdirSync(dir)) {
      const f = path.join(dir, e);
      if (e.toLowerCase() === 'session.db' && fs.statSync(f).isFile()) return f;
    }
    for (const e of fs.readdirSync(dir)) {
      const f = path.join(dir, e);
      try { if (fs.statSync(f).isDirectory()) { const r = findSessionDb(f, d + 1); if (r) return r; } } catch {}
    }
  } catch {}
  return null;
}

function main() {
  const wxlens = findWxlens();
  if (!wxlens) { console.error('[ERROR] 未找到 Wxlens 安装目录'); process.exit(1); }

  const koffi = loadKoffi(wxlens);
  const dllDir = findDllDir(wxlens);
  const hexKey = getKey();
  const accountDir = findAccountDir();

  // 加载 DLL
  koffi.load(path.join(dllDir, 'WCDB.dll'));
  try { koffi.load(path.join(dllDir, 'SDL2.dll')); } catch {}
  const lib = koffi.load(path.join(dllDir, 'wcdb_api.dll'));

  const InitProtection = lib.func('int32 InitProtection(const char*)');
  const wcdbInit = lib.func('int32 wcdb_init()');
  const wcdbOpenAccount = lib.func('int32 wcdb_open_account(const char*, const char*, _Out_ int64*)');
  const wcdbGetSnsTimeline = lib.func('int32 wcdb_get_sns_timeline(int64, int32, int32, const char*, const char*, int32, int32, _Out_ void**)');
  const wcdbGetDisplayNames = lib.func('int32 wcdb_get_display_names(int64, const char*, _Out_ void**)');
  const wcdbFreeString = lib.func('void wcdb_free_string(void*)');
  const wcdbShutdown = lib.func('int32 wcdb_shutdown()');

  for (const rp of [dllDir, path.dirname(dllDir), wxlens]) {
    if (InitProtection(rp) === 0) break;
  }
  if (wcdbInit() !== 0) { console.error('[ERROR] wcdb_init 失败'); process.exit(1); }

  const sessionDb = findSessionDb(accountDir, 0);
  if (!sessionDb) { console.error('[ERROR] 未找到 session.db'); process.exit(1); }

  const h = [0];
  if (wcdbOpenAccount(sessionDb, hexKey, h) !== 0 || !h[0]) {
    console.error('[ERROR] 数据库打开失败（密钥错误或微信未运行）');
    console.error('  提示: 请先启动微信并登录，再运行本脚本');
    process.exit(1);
  }
  const handle = h[0];

  function decodeFree(ptr) {
    if (!ptr) return null;
    let s = null;
    try { s = koffi.decode(ptr, 'char', -1); } catch {}
    try { wcdbFreeString(ptr); } catch {}
    return s;
  }

  // 调用时间线
  const outPtr = [null];
  const usernameJson = USERNAME ? JSON.stringify([USERNAME]) : '';
  const rc = wcdbGetSnsTimeline(handle, LIMIT, 0, usernameJson, KEYWORD || '', 0, 0, outPtr);
  if (rc !== 0 || !outPtr[0]) {
    console.error('[ERROR] 获取朋友圈失败 rc=' + rc);
    wcdbShutdown();
    process.exit(1);
  }
  const jsonStr = decodeFree(outPtr[0]);
  if (!jsonStr) { console.error('[ERROR] 解析朋友圈数据失败'); process.exit(1); }

  let timeline = [];
  try { timeline = JSON.parse(jsonStr); } catch {
    console.error('[ERROR] 返回数据不是合法 JSON');
    console.error(jsonStr.slice(0, 500));
    process.exit(1);
  }
  if (!Array.isArray(timeline)) {
    // 兼容 {timeline: [...]} 包装
    if (timeline && Array.isArray(timeline.timeline)) timeline = timeline.timeline;
    else if (timeline && Array.isArray(timeline.data)) timeline = timeline.data;
  }

  // ====== 点赞解析（双保险）======
  function parseLikes(post) {
    // 方法1: DLL 返回的 likes 字段
    if (Array.isArray(post.likes) && post.likes.length > 0) {
      return post.likes.map(l => (typeof l === 'string' ? l : (l.nickname || l.username || JSON.stringify(l))));
    }
    // 方法2: rawXml 解析
    const xml = post.rawXml || post.raw_xml || '';
    const likes = [];
    // 匹配 <likeUsers> 或 <LikeUsers> 内的 <username>/<nickname>
    const blockMatch = xml.match(/<(?:likeUsers|LikeUsers)[^>]*>([\s\S]*?)<\/(?:likeUsers|LikeUsers)>/i);
    if (blockMatch) {
      const block = blockMatch[1];
      const userBlocks = block.match(/<(?:user|User)[^>]*>[\s\S]*?<\/(?:user|User)>/g) || [];
      for (const ub of userBlocks) {
        const u = ub.match(/<(?:username|UserName)>(.*?)<\/(?:username|UserName)>/i);
        const n = ub.match(/<(?:nickname|NickName)>(.*?)<\/(?:nickname|NickName)>/i);
        if (u) likes.push({ username: u[1].trim(), nickname: n ? n[1].trim() : u[1].trim() });
      }
      // 兼容平铺 username/nickname
      if (likes.length === 0) {
        const us = block.match(/<(?:username|UserName)>(.*?)<\/(?:username|UserName)>/g) || [];
        const ns = block.match(/<(?:nickname|NickName)>(.*?)<\/(?:nickname|NickName)>/g) || [];
        us.forEach((u, i) => likes.push({ username: u.replace(/<[^>]+>/g, ''), nickname: ns[i] ? ns[i].replace(/<[^>]+>/g, '') : u.replace(/<[^>]+>/g, '') }));
      }
    }
    return likes;
  }

  // ====== 昵称解析（username → 中文名）======
  const nameCache = new Map();
  function resolveNames(usernames) {
    const uniq = [...new Set(usernames.filter(u => u && !nameCache.has(u)))];
    for (let i = 0; i < uniq.length; i += 50) {
      const batch = uniq.slice(i, i + 50);
      try {
        const p = [null];
        wcdbGetDisplayNames(handle, JSON.stringify(batch), p);
        if (p[0]) {
          const d = JSON.parse(koffi.decode(p[0], 'char', -1) || '{}');
          for (const k of Object.keys(d)) nameCache.set(k, d[k]);
          wcdbFreeString(p[0]);
        }
      } catch {}
    }
    return usernames.map(u => nameCache.get(u) || u);
  }

  // ====== 输出 ======
  if (RAW) {
    console.log(JSON.stringify(timeline, null, 2));
    wcdbShutdown();
    return;
  }

  console.log('');
  console.log('========================================');
  console.log('  微信朋友圈 · 最新 ' + timeline.length + ' 条');
  console.log('========================================');
  console.log('');

  const allLikerUsernames = new Set();
  for (const post of timeline) {
    const likeInfo = parseLikes(post);
    const likeNames = likeInfo.map(l => typeof l === 'string' ? l : (l.nickname || l.username));
    likeInfo.forEach(l => { if (typeof l === 'object' && l.username) allLikerUsernames.add(l.username); });
    post.__likes = likeInfo;
  }

  // 批量解析点赞者中文名
  const nameMap = new Map();
  const toResolve = [...allLikerUsernames].filter(u => u);
  if (toResolve.length) {
    for (let i = 0; i < toResolve.length; i += 50) {
      const batch = toResolve.slice(i, i + 50);
      try {
        const p = [null];
        wcdbGetDisplayNames(handle, JSON.stringify(batch), p);
        if (p[0]) {
          const d = JSON.parse(koffi.decode(p[0], 'char', -1) || '{}');
          for (const k of Object.keys(d)) nameMap.set(k, d[k]);
          wcdbFreeString(p[0]);
        }
      } catch {}
    }
  }

  timeline.forEach((post, idx) => {
    const time = post.createTime ? new Date(Number(post.createTime) * 1000 + 8 * 3600 * 1000).toISOString().slice(0, 16).replace('T', ' ') : '';
    const author = post.nickname || nameMap.get(post.username) || post.username || '未知';
    const content = (post.contentDesc || post.content || '').toString();
    const likeInfo = post.__likes || [];
    const likeTexts = likeInfo.map(l => {
      if (typeof l === 'string') return l;
      const n = l.nickname || nameMap.get(l.username) || l.username || '';
      return n;
    });

    console.log(`[${idx + 1}] ${author}  (${time})`);
    console.log(`    文案: ${content || '(无文字)'}`);
    if (likeTexts.length) {
      console.log(`    点赞: ${likeTexts.join(', ')}`);
    } else {
      console.log(`    点赞: (无)`);
    }
    if (ALL && post.comments && post.comments.length) {
      console.log(`    评论: ${post.comments.map(c => c.nickname + ': ' + (c.content || '')).join(' | ')}`);
    }
    console.log('');
  });

  wcdbShutdown();
  console.log('=== 完成 ===');
}

try {
  main();
} catch (e) {
  console.error('[ERROR]', e.message);
  process.exit(1);
}
