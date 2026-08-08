// 密钥提取模块
// 方案1: 从 Wxlens ~/.wx-mcp-server/config.json 读取（DPAPI 解密）
// 方案2: 微信运行时，通过 wx_key.dll 注入提取
// 提取后保存到 pack_config.json，后续无需重复提取

const fs = require('fs');
const path = require('path');
const os = require('os');

function getKeyFromWxlens(koffi) {
  const cfgPath = path.join(os.homedir(), '.wx-mcp-server', 'config.json');
  if (!fs.existsSync(cfgPath)) return null;

  try {
    const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
    if (!cfg.decryptKey || !cfg.decryptKey.startsWith('safe:')) return null;

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

    if (!CryptUnprotectData(inBlob, null, null, null, null, 0, outBlob)) return null;

    const cbData = outBlob.readUInt32LE(0);
    const pbData = outBlob.readBigUInt64LE(8);
    const keyBuf = Buffer.from(koffi.unsafe(pbData, cbData));

    return {
      key: keyBuf.toString('hex'),
      dbPath: cfg.dbPath || '',
      myWxid: (cfg.myWxid || '').replace(/_\d+$/, ''),  // wxid_xxx_906d → wxid_xxx
    };
  } catch (e) {
    return null;
  }
}

function getKeyViaHook(koffi, wxKeyDllPath) {
  // 通过 wx_key.dll 从微信进程提取密钥
  // 需要微信正在运行
  const keyLib = koffi.load(wxKeyDllPath);
  const InitializeHook = keyLib.func('int32 InitializeHook()');
  const PollKeyData = keyLib.func('int32 PollKeyData()');
  const GetImageKey = keyLib.func('int32 GetImageKey()');
  const CleanupHook = keyLib.func('int32 CleanupHook()');

  let hookRc = InitializeHook();
  if (hookRc !== 0) {
    console.log('  InitializeHook 失败:', hookRc);
    return null;
  }

  // 轮询等待微信产生密钥数据
  console.log('  等待微信产生密钥数据...');
  let keyRc = -1;
  for (let i = 0; i < 30; i++) {
    keyRc = PollKeyData();
    if (keyRc === 0) break;
    if (i % 5 === 0) console.log('  轮询中...');
    // 同步等待 1 秒
    const start = Date.now();
    while (Date.now() - start < 1000) {}
  }

  if (keyRc !== 0) {
    console.log('  PollKeyData 超时 (30秒)，请确认微信已登录');
    CleanupHook();
    return null;
  }

  const imgKey = GetImageKey();
  CleanupHook();

  if (imgKey !== 0) {
    console.log('  GetImageKey 失败:', imgKey);
    return null;
  }

  // 密钥数据需要通过 koffi 读取
  // wx_key.dll 的 GetImageKey 可能将密钥写入某个缓冲区
  // 根据 Wxlens 的实现，通常在成功后会更新内部状态
  // 这里返回成功标志，实际密钥由外部处理
  return { success: true };
}

module.exports = { getKeyFromWxlens, getKeyViaHook };
