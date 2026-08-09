// 首次运行初始化向导
// 1. 检测微信数据目录
// 2. 提取数据库密钥
// 3. 保存配置
// 后续运行直接跳过

const fs = require('fs');
const path = require('path');
const os = require('os');

const PACK_DIR = path.resolve(__dirname, '..');
const CONFIG_FILE = path.join(PACK_DIR, 'pack_config.json');

// ====== 已有配置则直接返回 ======
if (fs.existsSync(CONFIG_FILE)) {
  try {
    const cfg = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
    if (cfg.key && cfg.key.length >= 64 && cfg.dbPath && fs.existsSync(cfg.dbPath)) {
      console.log('[OK] 已有配置，初始化跳过');
      process.exit(0);
    }
  } catch(e) {}
}

console.log('');
console.log('========================================');
console.log('  WeChat Stats - First Time Setup');
console.log('========================================');
console.log('');

// ====== 查找微信数据目录 ======
function findWxDataDirs() {
  const candidates = [];
  for (const drive of ['D:', 'C:', 'E:', 'F:']) {
    const dir = drive + '\\xwechat_files';
    if (fs.existsSync(dir)) {
      for (const entry of fs.readdirSync(dir)) {
        const full = path.join(dir, entry);
        try {
          if (fs.statSync(full).isDirectory() && entry.startsWith('wxid_')) {
            if (fs.existsSync(path.join(full, 'db_storage'))) {
              candidates.push({ path: full, wxid: entry.replace(/_\d+$/, '') });
            }
          }
        } catch(e) {}
      }
    }
  }
  // Documents\WeChat Files\
  const wxDocs = path.join(os.homedir(), 'Documents', 'WeChat Files');
  if (fs.existsSync(wxDocs)) {
    for (const entry of fs.readdirSync(wxDocs)) {
      if (entry === 'All Users' || entry === 'Applet' || entry === 'WMPF') continue;
      const full = path.join(wxDocs, entry);
      try {
        if (!fs.statSync(full).isDirectory()) continue;
        // Must have db_storage or config to be a valid WeChat account
        if (!fs.existsSync(path.join(full, 'db_storage')) && !fs.existsSync(path.join(full, 'config'))) continue;
        candidates.push({ path: full, wxid: entry.replace(/_\d+$/, '') });
      } catch(e) {}
    }
  }
  return [...new Set(candidates.map(c => JSON.stringify(c)))].map(JSON.parse);
}

// ====== 密钥提取 ======
function extractKey(koffi) {
  // 方法1: 从 Wxlens 配置读取（如果用户安装过 Wxlens）
  const wxMcpConfig = path.join(os.homedir(), '.wx-mcp-server', 'config.json');
  if (fs.existsSync(wxMcpConfig)) {
    try {
      const cfg = JSON.parse(fs.readFileSync(wxMcpConfig, 'utf8'));
      if (cfg.decryptKey && cfg.decryptKey.startsWith('safe:')) {
        const base64Data = cfg.decryptKey.slice(5);
        const fullBuf = Buffer.from(base64Data, 'base64');
        const v10 = Buffer.from('v10');
        const data = fullBuf.slice(0, 3).equals(v10) ? fullBuf.slice(3) : fullBuf;

        const inBuf = koffi.alloc('uint8', data.length);
        for (let i = 0; i < data.length; i++) inBuf[i] = data[i];
        const inBlob = Buffer.alloc(16);
        inBlob.writeUInt32LE(data.length, 0);
        inBlob.writeBigUInt64LE(BigInt(koffi.address(inBuf)), 8);
        const outBlob = Buffer.alloc(16);

        const crypt32 = koffi.load('crypt32.dll');
        const CryptUnprotectData = crypt32.func(
          'bool CryptUnprotectData(void* pDataIn, void* ppszDataDescr, void* pOptionalEntropy, void* pvReserved, void* pPromptStruct, uint32 dwFlags, void* pDataOut)'
        );

        if (CryptUnprotectData(inBlob, null, null, null, null, 0, outBlob)) {
          const cbData = outBlob.readUInt32LE(0);
          const pbData = outBlob.readBigUInt64LE(8);
          const keyHex = Buffer.from(koffi.unsafe(pbData, cbData)).toString('hex');
          console.log('  [OK] 从 Wxlens 配置提取密钥成功');
          return {
            key: keyHex,
            dbPath: cfg.dbPath || '',
            myWxid: (cfg.myWxid || '').replace(/_\d+$/, ''),
          };
        }
      }
    } catch(e) { console.log('  [WARN] Wxlens 配置解析失败:', e.message); }
  }

  // 方法2: 通过 wx_key.dll 从微信进程提取（需要微信正在运行）
  const wxKeyDll = path.join(PACK_DIR, 'wcdb', 'wx_key.dll');
  if (fs.existsSync(wxKeyDll)) {
    try {
      const keyLib = koffi.load(wxKeyDll);
      const InitializeHook = keyLib.func('int32 InitializeHook()');
      const PollKeyData = keyLib.func('int32 PollKeyData()');
      const GetImageKey = keyLib.func('int32 GetImageKey()');
      const CleanupHook = keyLib.func('int32 CleanupHook()');

      if (InitializeHook() === 0) {
        console.log('  等待微信产生密钥数据...');
        let ok = false;
        for (let i = 0; i < 30; i++) {
          if (PollKeyData() === 0) { ok = true; break; }
          if (i % 10 === 0) console.log(`  ${(30-i)}秒...`);
          const start = Date.now(); while (Date.now() - start < 1000) {}
        }
        if (!ok) {
          console.log('[WARN] 密钥提取超时，请确认微信已登录');
          CleanupHook();
        } else if (GetImageKey() === 0) {
          CleanupHook();
          console.log('[OK] 从微信进程提取密钥成功');
          return { keyViaHook: true };
        }
      }
    } catch(e) { console.log('  [WARN] wx_key.dll 加载失败:', e.message); }
  }

  return null;
}

// ====== 主流程 ======
const wxDirs = findWxDataDirs();
if (wxDirs.length === 0) {
  console.log('[ERROR] 未找到微信数据目录');
  console.log('请确保微信已安装并至少登录过一次（产生 xwechat_files 目录）');
  process.exit(1);
}

let chosenDbPath = wxDirs[0].path;
let myWxid = wxDirs[0].wxid;
if (wxDirs.length > 1) {
  // Prefer wxid_ accounts over others
  wxDirs.sort((a, b) => {
    const aWx = a.wxid.startsWith('wxid_') ? 0 : 1;
    const bWx = b.wxid.startsWith('wxid_') ? 0 : 1;
    return aWx - bWx;
  });
  chosenDbPath = wxDirs[0].path;
  myWxid = wxDirs[0].wxid;
  console.log('检测到多个微信账号目录：');
  wxDirs.forEach((d, i) => console.log(`  [${i+1}] ${d.wxid}  →  ${d.path}`));
  console.log(`自动选择第 1 个: ${myWxid}`);
}
console.log(`[OK] 微信数据目录: ${chosenDbPath}`);

// 加载 koffi（先尝试本包，再尝试 NODE_PATH）
let koffi;
try {
  koffi = require(path.join(PACK_DIR, 'node_modules', 'koffi'));
} catch(e) {
  try { koffi = require('koffi'); } catch(e2) {
    console.log('[ERROR] 未找到 koffi 模块');
    process.exit(1);
  }
}

console.log('正在提取数据库密钥...');
const result = extractKey(koffi);

if (!result || !result.key) {
  console.log('');
  console.log('[ERROR] 无法提取数据库密钥');
  console.log('请尝试以下任一方法：');
  console.log('  1. 启动微信并保持登录状态，然后重新运行本程序');
  console.log('  2. Download & install Wxlens from GitHub Release (see README), run it once, then retry');
  console.log('  3. 使用 HTTP 模式（免密钥）：双击「启动-http.bat」，见 README "Alternative: HTTP Mode"');
  process.exit(1);
}

// 保存配置
const packConfig = {
  dbPath: chosenDbPath,
  key: result.key,
  myWxid: result.myWxid || myWxid,
  initializedAt: new Date().toISOString(),
};
fs.writeFileSync(CONFIG_FILE, JSON.stringify(packConfig, null, 2));
console.log(`[OK] 配置已保存: ${CONFIG_FILE}`);
console.log('[OK] 账号: ' + (packConfig.myWxid));
console.log('');
console.log('初始化完成！');
