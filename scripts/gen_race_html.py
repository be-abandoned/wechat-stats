# -*- coding: utf-8 -*-
"""生成「聊天频率排行」交互式 HTML（Bar Chart Race）
口径：每天一帧，显示当天往前 30 天收发消息总数 Top10；2022-01 起；每人一色；默认 4 天/秒；隐私模式"""
import os, json, re, sys
from datetime import datetime, timedelta
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = r'D:\WorkBuddy\微信聊天记录库-私聊'
OUT = os.environ.get('RACE_TMP') or os.path.join(BASE, '聊天频率排行.html')   # 支持临时输出（合并流程用）

def sanitize(n):
    s = re.sub(r'[\\/:*?"<>|]', '_', n)
    s = re.sub(r'[\xa0\u200b\u200c\u200d\s]+', ' ', s).strip()
    return s.rstrip('.')

# ── 读取每人 dayCount ──
people = []      # (name, dayCount)
minD = maxD = None
for d in sorted(os.listdir(BASE)):
    p = os.path.join(BASE, d, 'stats.json')
    if not os.path.isfile(p):
        continue
    st = json.load(open(p, encoding='utf-8'))
    dc = st.get('dayCount') or {}
    if not dc:
        continue
    name = st.get('display') or d
    people.append((name, dc))
    lo, hi = min(dc), max(dc)
    if minD is None or lo < minD: minD = lo
    if maxD is None or hi > maxD: maxD = hi

people.sort(key=lambda x: -max(x[1].values()))
print(f'联系人 {len(people)}，时间 {minD} ~ {maxD}（{(datetime.strptime(maxD, "%Y-%m-%d") - datetime.strptime(minD, "%Y-%m-%d")).days + 1} 天）')

day_data = {n: dc for n, dc in people}

# 拼音首字母（隐私模式用）：许月红 → XYH
from pypinyin import lazy_pinyin
INITIALS = {n: ''.join(p[0].upper() for p in lazy_pinyin(n)) for n in day_data}

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>微信聊天频率排行</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Microsoft YaHei','PingFang SC',sans-serif; background:#EDEDED; color:#1f2937; padding:24px; }
.wrap { max-width:1080px; margin:0 auto; }
h1 { font-size:24px; font-weight:700; text-align:center; }
.sub { text-align:center; color:#6b7280; font-size:13px; margin-top:6px; }
.date { text-align:center; font-size:44px; font-weight:800; color:#07C160; margin:14px 0 10px; font-variant-numeric:tabular-nums; }
.card { background:#fff; border-radius:14px; box-shadow:0 1px 4px rgba(0,0,0,.07); padding:14px 18px; }
#stage { width:100%; display:block; border-radius:10px; }
.controls { display:flex; align-items:center; gap:10px; margin-top:12px; flex-wrap:wrap; }
.btn { display:inline-flex; align-items:center; justify-content:center; width:44px; height:40px; border:1px solid #e5e7eb; border-radius:10px; background:#fff; cursor:pointer; color:#374151; transition:background .15s, border-color .15s; }
.btn:hover { background:#F5F5F5; }
.btn.primary { background:#07C160; border-color:#07C160; color:#fff; width:56px; }
.btn.primary:hover { background:#0FAE6A; }
input[type=range] { flex:1; min-width:160px; accent-color:#07C160; height:32px; }
.rng-info { font-size:13px; color:#6b7280; font-variant-numeric:tabular-nums; min-width:150px; text-align:center; }
.speed { display:flex; gap:5px; flex-wrap:wrap; }
.speed button { padding:5px 9px; border:1px solid #e5e7eb; border-radius:8px; background:#fff; font-size:12.5px; color:#374151; cursor:pointer; white-space:nowrap; }
.speed button.on { background:#07C160; border-color:#07C160; color:#fff; font-weight:600; }
.ctrl-label { font-size:13px; color:#6b7280; }
.grp { display:inline-flex; align-items:center; gap:6px; }
.sel { padding:6px 10px; border:1px solid #e5e7eb; border-radius:8px; background:#fff; font-size:13px; color:#374151; cursor:pointer; outline:none; }
.sel:hover { border-color:#cbd5e1; }
#speedRange { accent-color:#07C160; width:130px; }
.hint { text-align:center; color:#9ca3af; font-size:12px; margin-top:10px; }
footer { text-align:center; color:#9ca3af; font-size:12px; margin-top:14px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>微信聊天频率排行</h1>
  <div class="sub" id="subEl">—</div>
  <div class="date" id="dateEl">—</div>
  <div class="card">
    <canvas id="stage" height="760"></canvas>
    <div class="controls">
      <span class="grp"><span class="ctrl-label">视图</span><span class="speed" id="viewBtns">
        <button data-v="bar" class="on">柱状</button><button data-v="line">折线</button>
      </span></span>
      <span class="grp"><span class="ctrl-label">数据</span>
        <select class="sel" id="srcSel" title="排行指标">
          <option value="rolling" selected>消息数</option>
          <option value="heat">热度</option>
        </select>
      </span>
      <button class="btn" id="rewBtn" title="回到开头"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M6 6h2v12H6zM20 6l-9 6 9 6z"/></svg></button>
      <button class="btn primary" id="playBtn" title="播放/暂停（空格）"><svg id="playIco" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></button>
      <button class="btn" id="endBtn" title="跳到末尾"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M16 6h2v12h-2zM4 6l9 6-9 6z"/></svg></button>
      <input type="range" id="range" min="0" max="1" step="1" value="0">
      <div class="rng-info" id="rngInfo">—</div>
    </div>
    <div class="controls" style="margin-top:8px">
      <span class="grp"><span class="ctrl-label">隐私</span>
        <select class="sel" id="privSel" title="姓名显示方式">
          <option value="0" selected>关闭</option>
          <option value="1">保留姓*</option>
          <option value="2">首字母</option>
          <option value="3">第二字</option>
        </select>
      </span>
      <span class="grp"><span class="ctrl-label">口径</span>
        <select class="sel" id="winSel" title="近 N 天消息数">
          <option value="1">1天</option><option value="7">7天</option>
          <option value="30">一个月</option><option value="90">三个月</option><option value="180">六个月</option><option value="365" selected>12个月</option>
          <option value="all">有记录以来</option>
        </select>
      </span>
      <span class="grp"><span class="ctrl-label">速度</span>
        <input type="range" id="speedRange" list="speedMarks" min="0" max="6" step="1" value="5">
        <datalist id="speedMarks">
          <option value="0" label="×1"></option><option value="1" label="×2"></option>
          <option value="2" label="×4"></option><option value="3" label="×8"></option>
          <option value="4" label="×16"></option><option value="5" label="×32"></option>
          <option value="6" label="×64"></option>
        </datalist>
        <span class="rng-info" id="speedLbl" style="min-width:40px">×32</span>
      </span>
    </div>
    <div class="controls" style="margin-top:8px">
      <span class="grp" id="axisGrp" style="display:none"><span class="ctrl-label">横轴</span>
        <select class="sel" id="axisSel" title="折线图横轴规则">
          <option value="roll90">滚动90天</option>
          <option value="roll6m">滚动6个月</option>
          <option value="roll12m" selected>滚动12个月</option>
          <option value="roll6m">滚动6个月</option>
          <option value="roll12m">滚动12个月</option>
          <option value="full">全历史</option>
        </select>
      </span>
      <span class="grp" id="lineGrp" style="display:none"><span class="ctrl-label">线数</span>
        <input type="range" id="lineRange" min="0" max="1" step="0.001" value="0.6644" style="width:130px">
        <span class="rng-info" id="lineLbl" style="min-width:36px">10</span>
      </span>
    </div>
  </div>
  <footer>数据更新至 __MAX_CN__</footer>
</div>
<script>
const DAY_DATA = __DAY_DATA__;
const INITIALS = __INITIALS__;
const MIN_DATE = '__MIN_DATE__';
const MAX_DATE = '__MAX_DATE__';
const TOP_N = 10;
const DEFAULT_SPEED = 32;
const WIN_LABELS = { 1: '1天', 7: '7天', 30: '一个月', 90: '三个月', 180: '六个月', 365: '12个月', Infinity: '有记录以来' };
let privacy = 0;   // 0 关闭 / 1 保留姓其余* / 2 拼音首字母 / 3 只显示第二个字；通用：名字超 3 字只留前 3
function maskName(nm) {
  let s = nm
  if (privacy === 1) s = nm[0] + '*'.repeat(nm.length - 1)
  else if (privacy === 2) s = INITIALS[nm] || nm
  else if (privacy === 3) {   // 保留第二字，其他用 *（最多 3 字符）
    const c = nm[1] || nm[0]
    s = nm.length >= 3 ? '*' + c + '*' : nm.length === 2 ? '*' + c : c
  }
  return s.length > 3 ? s.slice(0, 3) : s
}

// ── 数据构建：dates + 每人每日数组 + 可调窗口 rolling ──
const dates = [];
{
  const d = new Date(MIN_DATE + 'T00:00:00Z');
  const end = new Date(MAX_DATE + 'T00:00:00Z');
  while (d <= end) { dates.push(d.toISOString().slice(0, 10)); d.setUTCDate(d.getUTCDate() + 1); }
}
const dateIdx = new Map(dates.map((dt, i) => [dt, i]));
const names = Object.keys(DAY_DATA);
const daily = names.map(nm => {
  const arr = new Array(dates.length).fill(0);
  const dc = DAY_DATA[nm];
  for (const k in dc) { const i = dateIdx.get(k); if (i != null) arr[i] = dc[k]; }
  return arr;
});
let windowDays = 365;   // 可调窗口（1/7/30/90/180/365/Infinity）；初始=柱状默认 12 个月，与下拉 selected 一致
function buildRollingAll() {
  return daily.map(arr => {
    const out = new Array(arr.length);
    let s = 0;
    for (let i = 0; i < arr.length; i++) {
      s += arr[i];
      if (windowDays < Infinity && i >= windowDays) s -= arr[i - windowDays];
      out[i] = s;
    }
    return out;
  });
}
let rolling = buildRollingAll();
// 综合热度指数（双尺度 EWMA，基于原始日消息数，独立于时间窗口口径）
const heat = daily.map(arr => {
  const H = new Float64Array(arr.length)
  let s = 0, l = 0
  for (let i = 0; i < arr.length; i++) {
    const d = arr[i]
    s = 0.094 * d + 0.906 * s          // 短期 EWMA（半衰 7 天，捕获周级爆发，抑制逐日噪声）
    l = 0.032 * d + 0.968 * l          // 长期 EWMA（半衰 21 天，锚定趋势）
    const bl = Math.max(l, 1)
    H[i] = bl * (1 + Math.max(s / bl - 1, 0) * 0.5) + s * 0.3
  }
  return Array.from(H)
})
// 渲染层滑动平均（仅热度模式折线）：消除逐点锯齿，热度平滑语义不变
function smoothVals(vals, win) {
  if (vals.length <= win) return vals
  const out = new Array(vals.length)
  let sum = 0
  for (let i = 0; i < vals.length; i++) {
    sum += vals[i]
    if (i >= win) sum -= vals[i - win]
    out[i] = sum / win
  }
  return out
}
let dataSrc = 'rolling'               // 'rolling'=口径消息数 / 'heat'=综合热度
function dataOf(k, i) { return dataSrc === 'heat' ? heat[k][i] : rolling[k][i] }
function subText() {
  if (dataSrc === 'heat') return `综合热度指数 · 越高越活跃 ｜ ${MIN_DATE.slice(0, 4)}年${+MIN_DATE.slice(5, 7)}月 至 ${MAX_DATE.slice(0, 4)}年${+MAX_DATE.slice(5, 7)}月`
  return `每天统计「当天往前 ${WIN_LABELS[windowDays]}」收发消息条数 Top ${TOP_N} ｜ ${MIN_DATE.slice(0, 4)}年${+MIN_DATE.slice(5, 7)}月 至 ${MAX_DATE.slice(0, 4)}年${+MAX_DATE.slice(5, 7)}月`
}
document.getElementById('subEl').textContent = subText();

// ── 每人固定色（hash → tab20）──
const PALETTE = ['#4E79A7','#F28E2B','#E15759','#76B7B2','#59A14F','#EDC948','#B07AA1','#FF9DA7','#9C755F','#BAB0AC',
                 '#1B9E77','#D95F02','#7570B3','#E7298A','#66A61E','#E6AB02','#A6761D','#666666','#8DD3C7','#BEBADA'];
function colorFor(nm) {
  let h = 0;
  for (let i = 0; i < nm.length; i++) h = (h * 31 + nm.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

// ── 柱状图模式：榜上 Top10 颜色分配（色相环最大空隙法 + 最小间隔保护，两两不相似）──
const barHue = new Map();   // name -> 色相 0~360
function updateBarHues(curTop) {
  for (const [nm] of barHue) if (!curTop.includes(nm)) barHue.delete(nm)   // 出榜释放
  for (const nm of curTop) {
    if (barHue.has(nm)) continue
    const used = [...barHue.values()].sort((a, b) => a - b)
    const n = used.length
    let best = 0, bestGap = -1
    for (let i = 0; i <= n; i++) {
      const a = i === 0 ? (n ? used[n - 1] : 360) - 360 : used[i - 1]
      const b = i === n ? (n ? used[0] : -360) + 360 : used[i]
      const gap = b - a
      if (gap > bestGap) { bestGap = gap; best = (a + b) / 2 }
    }
    barHue.set(nm, ((best % 360) + 360) % 360)
  }
  // 最小间隔保护：若色相差 < 30°，对全部在线者均匀重排（360/N 均分，保证明显可区分）
  const hs = [...barHue.values()].sort((a, b) => a - b)
  let minGap = 360
  for (let i = 1; i < hs.length; i++) minGap = Math.min(minGap, hs[i] - hs[i - 1])
  if (hs.length > 1 && minGap < 30) {
    const step = 360 / hs.length
    ;[...barHue.keys()].forEach((nm, i) => barHue.set(nm, (i * step) % 360))   // 前导分号防 ASI 下标歧义
  }
}

// ── 折线图模式：动态前 N 名（1~32，对数滑条）+ 横轴规则（滚动90天 / 全历史压缩）──
const LINE_WIN = 90, LINE_MAX = 32;
const WIN_DAYS = { roll90: 90, roll6m: 180, roll12m: 365, full: Infinity }   // 横轴滚动窗口（天）
const nameIdx = new Map(names.map((n, i) => [n, i]));
let mode = 'bar';
let lineTop = 10;             // 当前曲线条数（1~32）
let lineAxis = 'roll';        // 'roll' 滚动90天 | 'full' 全历史压缩（左端=时间原点）
// 预计算每天 Top32 名单（N 切换无需重算，取前 N）
let TOP32_BY_DAY = buildTop32ByDay();   // 口径切换时重算
function buildTop32ByDay() {
  const out = [];
  for (let i = 0; i < dates.length; i++) {
    const arr = names.map((n, k) => [n, dataOf(k, i)]);
    arr.sort((a, b) => b[1] - a[1]);
    out.push(arr.slice(0, LINE_MAX).map(x => x[0]));
  }
  return out;
}
function curTopAt(iEnd) { return TOP32_BY_DAY[Math.min(iEnd, TOP32_BY_DAY.length - 1)].slice(0, lineTop) }
// 折线色相：色相环最大空隙法（任意 N 都两两均分色相），复用柱状同款逻辑
const lineHue = new Map();
function updateLineHues(curTop) {
  for (const [nm] of lineHue) if (!curTop.includes(nm)) lineHue.delete(nm)
  for (const nm of curTop) {
    if (lineHue.has(nm)) continue
    const used = [...lineHue.values()].sort((a, b) => a - b)
    const n = used.length
    let best = 0, bestGap = -1
    for (let i = 0; i <= n; i++) {
      const a = i === 0 ? (n ? used[n - 1] : 360) - 360 : used[i - 1]
      const b = i === n ? (n ? used[0] : -360) + 360 : used[i]
      const gap = b - a
      if (gap > bestGap) { bestGap = gap; best = (a + b) / 2 }
    }
    lineHue.set(nm, ((best % 360) + 360) % 360)
  }
  const hs = [...lineHue.values()].sort((a, b) => a - b)
  let minGap = 360
  for (let i = 1; i < hs.length; i++) minGap = Math.min(minGap, hs[i] - hs[i - 1])
  if (hs.length > 1 && minGap < 30) {
    const step = 360 / hs.length
    ;[...lineHue.keys()].forEach((nm, i) => lineHue.set(nm, (i * step) % 360))
  }
}

// ── Canvas 绘制 ──
const canvas = document.getElementById('stage');
const ctx = canvas.getContext('2d');
const dateEl = document.getElementById('dateEl');
function resize() {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.parentElement.clientWidth - 36;
  canvas.style.width = w + 'px';
  canvas.style.height = '760px';
  canvas.width = w * dpr;
  canvas.height = 760 * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener('resize', resize);
resize();

const fmtN = v => Number(v).toLocaleString('zh-CN');

// 柱子平滑位置（排名交换时上下滑动，不跳变）
const disp = new Map();   // name -> 当前显示 y 索引（浮点）
// 坐标轴上限平滑（高速 + 大窗口口径时，maxV 随榜首突增/回落会造成柱长抖动）
let smoothMax = 1;
function trackMax(rawMax, dt) {
  const k = dt ? 1 - Math.exp(-dt * 6) : 1
  smoothMax += (rawMax - smoothMax) * k
  return Math.max(smoothMax, 1)
}

function draw(pos, dt) {
  if (mode === 'bar') drawBar(pos, dt); else drawLine(pos);
  const di = Math.round(pos);
  const d = dates[Math.min(di, dates.length - 1)];
  dateEl.textContent = d.slice(0, 4) + '年' + (+d.slice(5, 7)) + '月' + (+d.slice(8, 10)) + '日';
}
function drawBar(pos, dt) {
  const i0 = Math.min(Math.floor(pos), dates.length - 1);
  const frac = pos - Math.floor(pos);
  const i1 = Math.min(i0 + 1, dates.length - 1);
  const cur = {};
  for (let k = 0; k < names.length; k++) {
    cur[names[k]] = dataOf(k, i0) + (dataOf(k, i1) - dataOf(k, i0)) * frac;
  }
  const top = names.map(n => [n, cur[n]]).filter(t => t[1] > 0).sort((a, b) => b[1] - a[1]).slice(0, TOP_N);   // 过滤 0 值，不拿人名+0 凑数
  const rawMax = Math.max(...top.map(t => t[1]), 1);
  const maxV = trackMax(rawMax, dt);   // 平滑轴上限，柱长变化不再随榜首跳变

  const W = canvas.width / (window.devicePixelRatio || 1);
  const H = 760;
  const PAD_L = 100, PAD_R = 150, PAD_T = 26, PAD_B = 22;
  const bw = W - PAD_L - PAD_R;
  const bh = (H - PAD_T - PAD_B) / TOP_N;
  ctx.clearRect(0, 0, W, H);

  // 榜上 Top10 颜色：色相环最大空隙分配（两两不相似）
  updateBarHues(top.map(t => t[0]));

  // ── 坐标轴：整百刻度 + 密度自适应（从 100 起步，刻度线间距 < 40px 时间隔翻倍）──
  let step = 100;
  while (bw / (maxV / step) < 40) step *= 2;   // 过密 → 100/200/300 → 200/400/600 → 400/800/1200 …
  ctx.strokeStyle = '#f0f0f0';
  ctx.lineWidth = 1;
  ctx.font = '12px "Microsoft YaHei"';
  ctx.fillStyle = '#9ca3af';
  ctx.textAlign = 'left';
  const nLines = Math.floor(maxV / step);
  for (let i = 0; i <= nLines; i++) {
    const x = PAD_L + bw * i * step / maxV;
    ctx.beginPath(); ctx.moveTo(x, PAD_T); ctx.lineTo(x, H - PAD_B); ctx.stroke();
    ctx.fillText(fmtN(i * step), x + 5, H - PAD_B + 16);
  }

  // ── 排名位置平滑（指数逼近目标排名，柱子上下滑动不跳变）──
  const rankOf = new Map();
  top.forEach((t, i) => rankOf.set(t[0], i));
  const k = dt ? 1 - Math.exp(-dt * 9) : 1;
  for (const [nm, y] of disp) {
    if (rankOf.has(nm)) {
      const target = rankOf.get(nm);
      const ny = y + (target - y) * k;
      disp.set(nm, Math.abs(ny - target) < 0.002 ? target : ny);
    } else {
      const ny = y + (TOP_N - 0.45 - y) * k;    // 出榜：滑向榜底外消失
      if (ny > TOP_N - 0.15) disp.delete(nm); else disp.set(nm, ny);
    }
  }
  for (const t of top) if (!disp.has(t[0])) disp.set(t[0], TOP_N + 0.6);   // 新进榜：从底部滑入
  // 柱子（位置用平滑后的 disp）
  top.forEach(([nm, v], idx) => {
    const yIdx = disp.get(nm) ?? idx;
    const y = PAD_T + yIdx * bh;
    const hgt = bh * 0.72;
    const w = Math.max(2, bw * v / maxV);
    ctx.fillStyle = barHue.has(nm) ? `hsl(${barHue.get(nm).toFixed(0)}, 48%, 56%)` : colorFor(nm);
    ctx.beginPath();
    ctx.roundRect(PAD_L, y + (bh - hgt) / 2, w, hgt, 6);
    ctx.fill();
    // 名字（柱内左侧；隐私处理 + 超 3 字截前 3 字）
    const nameTxt = maskName(nm);
    ctx.fillStyle = '#1f2937';
    ctx.font = 'bold 20px "Microsoft YaHei"';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText(nameTxt, PAD_L + 10, y + bh / 2);
    // 数值：放在柱子右端外侧，并避开名字区域（短柱时不互相遮挡）
    const nameW = ctx.measureText(nameTxt).width;
    const numX = PAD_L + Math.max(w + 8, nameW + 18);
    ctx.fillStyle = '#374151';
    ctx.font = 'bold 19px "Microsoft YaHei"';
    ctx.fillText(fmtN(Math.round(v)), numX, y + bh / 2);
    // 排名徽章
    const rankC = idx === 0 ? '#E6B422' : idx === 1 ? '#A8A8A8' : idx === 2 ? '#C98A5B' : '#D1D5DB';
    ctx.fillStyle = rankC;
    ctx.beginPath();
    ctx.arc(PAD_L - 38, y + bh / 2, 15, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 15px "Microsoft YaHei"';
    ctx.textAlign = 'center';
    ctx.fillText(String(idx + 1), PAD_L - 38, y + bh / 2 + 0.5);
  });
}
// ── 折线图：动态前 N 名曲线；横轴 roll=最近90天滚动 / full=全历史压缩（左端时间原点固定）──
function drawLine(pos) {
  const W = canvas.width / (window.devicePixelRatio || 1);
  const H = 760;
  const PAD_L = 64, PAD_R = 170, PAD_T = 26, PAD_B = 34;
  const iEnd = Math.min(Math.floor(pos), dates.length - 1);
  const winDays = WIN_DAYS[lineAxis] || 90;
  const iStart = lineAxis === 'full' ? 0 : Math.max(0, iEnd - (winDays - 1));
  const span = Math.max(iEnd - iStart, 1);
  const plotW = W - PAD_L - PAD_R;
  const plotH = H - PAD_T - PAD_B;
  ctx.clearRect(0, 0, W, H);

  // 当前 TopN 曲线（掉出即不绘制）
  const curTop = curTopAt(iEnd);
  updateLineHues(curTop);
  let maxV = 1;
  const series = new Map();
  for (const nm of curTop) {
    const k = nameIdx.get(nm);
    const vals = [];
    for (let i = iStart; i <= iEnd; i++) { const v = dataOf(k, i); vals.push(v); if (v > maxV) maxV = v; }
    series.set(nm, dataSrc === 'heat' ? smoothVals(vals, 5) : vals);   // 热度模式渲染前 5 天滑动平均
  }

  // Y 轴整百刻度（垂直密度 < 40px 翻倍）
  let step = 100;
  while (plotH / (maxV / step) < 40) step *= 2;
  ctx.strokeStyle = '#f0f0f0';
  ctx.lineWidth = 1;
  ctx.font = '12px "Microsoft YaHei"';
  ctx.fillStyle = '#9ca3af';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  const nLines = Math.floor(maxV / step);
  for (let i = 0; i <= nLines; i++) {
    const y = PAD_T + plotH - plotH * i * step / maxV;
    ctx.beginPath(); ctx.moveTo(PAD_L, y); ctx.lineTo(W - PAD_R, y); ctx.stroke();
    ctx.fillText(fmtN(i * step), PAD_L - 8, y);
  }
  // ── X 轴标签：普通日期只标月日（MM-DD），1 月 1 日下面标年份；未来区也标日期 ──
  // 滚动模式未来区 = 右侧 1/4 宽度 ≈ span/3 天
  const futureEnd = lineAxis === 'full' ? iEnd : iEnd + Math.round(span / 3);
  function dateAt(i) {
    if (i < dates.length) return dates[i]
    const d = new Date(dates[dates.length - 1] + 'T00:00:00Z')
    d.setUTCDate(d.getUTCDate() + (i - (dates.length - 1)))
    return d.toISOString().slice(0, 10)
  }
  function idxOf(ds) {
    const i = dateIdx.get(ds)
    if (i != null) return i
    const last = dates[dates.length - 1]
    return dates.length - 1 + Math.round((new Date(ds + 'T00:00:00Z') - new Date(last + 'T00:00:00Z')) / 86400000)
  }
  function xAt(i) { return lineAxis === 'full' ? PAD_L + plotW * (i - iStart) / span : PAD_L + plotW * 0.75 * (i - iStart) / span }
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  const labelGap = Math.max(15, Math.round(span / 10 / 15) * 15);   // 滚动模式月份标签间隔
  const monthTxt = ds => `${+ds.slice(5, 7)}月`;                       // 只显示 X月
  const YEAR_Y = H - PAD_B + 26;                                        // 年份行 = 月份下方
  if (lineAxis === 'full') {
    // 全历史：只在每年 1 月 1 日下面标年份
    ctx.font = 'bold 12px "Microsoft YaHei"';
    const y0 = +dates[iStart].slice(0, 4), y1 = +dates[iEnd].slice(0, 4)
    for (let Y = y0; Y <= y1; Y++) {
      const yi = idxOf(`${Y}-01-01`)
      if (yi >= iStart && yi <= iEnd) ctx.fillText(`${Y}年`, xAt(yi), H - PAD_B + 8)
    }
  } else {
    // 滚动：历史区 + 未来区月份标签（X月；跳过当前时间线，头顶大字已显示时间）
    ctx.font = '11px "Microsoft YaHei"';
    for (let i = 0; i <= span; i += labelGap) {
      if (i === span) continue
      ctx.fillText(monthTxt(dateAt(iStart + i)), xAt(iStart + i), H - PAD_B + 8)
    }
    for (let i = iEnd + labelGap; i <= futureEnd; i += labelGap) {
      ctx.fillText(monthTxt(dateAt(i)), xAt(i), H - PAD_B + 8)
    }
    // 年份标记：1 月下方第二行；1 月滑出左端则钉在原点；整年滑出则消失
    ctx.font = 'bold 12px "Microsoft YaHei"';
    const y0 = +dates[iStart].slice(0, 4), y1 = +dateAt(futureEnd).slice(0, 4)
    for (let Y = y0; Y <= y1; Y++) {
      const y1i = idxOf(`${Y}-01-01`), y12i = idxOf(`${Y}-12-31`)
      if (y12i < iStart) continue
      ctx.fillText(`${Y}年`, y1i >= iStart ? xAt(y1i) : PAD_L, YEAR_Y)
    }
    ctx.font = '11px "Microsoft YaHei"';
  }

  // 曲线（Catmull-Rom 平滑）；N 大时线宽减细；标签：值最大 5 人 + 最新加入 2 人（最多 7）
  // 横轴映射：滚动模式当前时间固定在 3/4 处（左侧 3/4=历史，右侧 1/4=未来）；全历史右端=当前
  const xOf = lineAxis === 'full'
    ? (i => PAD_L + plotW * (i - iStart) / span)
    : (i => PAD_L + plotW * 0.75 * (i - iStart) / span);
  const yOf = v => PAD_T + plotH - plotH * v / maxV;
  // 当前时间竖线（滚动模式，仅虚线）
  if (lineAxis !== 'full') {
    const curX = PAD_L + plotW * 0.75;
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = '#c9d2dc';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(curX, PAD_T); ctx.lineTo(curX, H - PAD_B); ctx.stroke();
    ctx.setLineDash([]);
  }
  const lw = lineTop <= 10 ? 2.6 : lineTop <= 20 ? 1.8 : 1.2;
  const labeled = pickLabeled(curTop, iEnd);
  const endPts = [];
  for (const [nm, vals] of series) {
    const hue = lineHue.get(nm)
    const c = hue != null ? `hsl(${hue.toFixed(0)}, 55%, 52%)` : '#BAB0AC';
    ctx.strokeStyle = c;
    ctx.lineWidth = lw;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.beginPath();
    // 像素空间 DP 简化（消除锯齿）+ 直线连接真实数据点 + round 圆角 → 完全保真，杜绝贝塞尔过冲回绕
    const pts = simplifyDP(vals.map((v, i) => ({ x: xOf(iStart + i), y: yOf(v) })), 2);
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
    ctx.stroke();
    // 端点圆点
    const ex = xOf(iEnd), ey = yOf(vals[vals.length - 1]);
    ctx.beginPath(); ctx.arc(ex, ey, lineTop <= 10 ? 4.5 : 3, 0, Math.PI * 2);
    ctx.fillStyle = c; ctx.fill();
    ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 2; ctx.stroke();
    if (labeled.has(nm)) endPts.push({ nm, x: ex, y: ey, v: vals[vals.length - 1], c });
  }
  // 端点名字 + 条数（右侧，贪心防重叠）
  endPts.sort((a, b) => a.y - b.y);
  const taken = [];
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  for (const p of endPts) {
    let ly = p.y;
    for (const t of taken) if (Math.abs(t - ly) < 26) ly = t + 26;
    taken.push(ly);
    const nmTxt = maskName(p.nm);
    ctx.fillStyle = p.c;
    ctx.font = 'bold 15px "Microsoft YaHei"';
    ctx.fillText(nmTxt, p.x + 10, ly);
    ctx.fillStyle = '#6b7280';
    ctx.font = '13px "Microsoft YaHei"';
    ctx.fillText(fmtN(Math.round(p.v)), p.x + 10 + ctx.measureText(nmTxt).width + 8, ly);
  }
}

// 每人最早消息日索引（判定"新认识的人"：最近才开始聊天）
const firstDayIdx = {}
for (const nm of names) {
  let mn = Infinity
  const dc = DAY_DATA[nm]
  for (const k in dc) { const i = dateIdx.get(k); if (i != null && i < mn) mn = i }
  firstDayIdx[nm] = mn === Infinity ? 0 : mn
}
const JOIN_WIN = 30, NEW_WIN = 90   // 上升速度窗口 / 新认识窗口（天）
function rise30(nm, iEnd) {
  const k = nameIdx.get(nm)
  const e = Math.min(iEnd, dates.length - 1), s = Math.max(0, e - JOIN_WIN)
  return dataOf(k, e) - dataOf(k, s)
}
// 折线标签：4 个给当前值最大 + 2 个给 30 天上升最快（仅正增长）+ 2 个给新认识（最早聊天日在近 90 天）
function pickLabeled(curTop, iEnd) {
  const labeled = new Set(curTop.slice(0, 4))                       // 值最大 4 人
  curTop.filter(nm => !labeled.has(nm) && rise30(nm, iEnd) > 0)     // 排除没上升的人（如长期不聊）
    .sort((a, b) => rise30(b, iEnd) - rise30(a, iEnd))
    .slice(0, 2)
    .forEach(nm => labeled.add(nm))                                  // 30 天正增长最快 2 人
  curTop.filter(nm => !labeled.has(nm) && (iEnd - firstDayIdx[nm]) <= NEW_WIN)
    .sort((a, b) => firstDayIdx[b] - firstDayIdx[a])
    .slice(0, 2)
    .forEach(nm => labeled.add(nm))                                  // 新认识 2 人（无则自然为 0）
  return labeled
}
// 折线锯齿美化：道格拉斯-普克简化（像素空间，仅去除近直线冗余点，不改变数据真实值）
function simplifyDP(pts, eps) {
  if (pts.length < 3) return pts
  const keep = new Uint8Array(pts.length); keep[0] = keep[pts.length - 1] = 1
  const stack = [[0, pts.length - 1]]
  while (stack.length) {
    const [s, e] = stack.pop()
    const a = pts[s], b = pts[e]
    const dx = b.x - a.x, dy = b.y - a.y
    const len = Math.hypot(dx, dy) || 1
    let maxD = 0, idx = -1
    for (let i = s + 1; i < e; i++) {
      const p = pts[i]
      const d = Math.abs(dy * p.x - dx * p.y + b.x * a.y - b.y * a.x) / len
      if (d > maxD) { maxD = d; idx = i }
    }
    if (maxD > eps) { keep[idx] = 1; stack.push([s, idx], [idx, e]) }
  }
  const out = []
  for (let i = 0; i < pts.length; i++) if (keep[i]) out.push(pts[i])
  return out
}
// ── 播放控制 ──
const START_POS = dateIdx.get('2022-06-08') ?? 0;   // 默认从 2022-06-08 开始播放
let pos = START_POS, speed = DEFAULT_SPEED, playing = false, lastT = 0;   // 首次加载不自动播放
const range = document.getElementById('range');
range.max = dates.length - 1;
const rngInfo = document.getElementById('rngInfo');
const playBtn = document.getElementById('playBtn');
const playIco = document.getElementById('playIco');

function setPlaying(on) {
  playing = on;
  // 播放中显示「暂停」图标（点击=暂停），暂停时显示「播放」图标（点击=播放）
  playIco.innerHTML = on ? '<path d="M7 5h4v14H7zM13 5h4v14h-4z"/>' : '<path d="M8 5v14l11-7z"/>';
}
setPlaying(playing);   // 初始化同步图标（打开即自动播放 → 显示暂停图标）
function syncRange() {
  range.value = Math.round(pos);
  const d = dates[Math.min(Math.round(pos), dates.length - 1)];
  rngInfo.textContent = d.slice(0, 4) + '-' + d.slice(5, 7) + '-' + d.slice(8, 10);
}
function frame(t) {
  if (!lastT) lastT = t;
  const dt = Math.min((t - lastT) / 1000, 0.1);
  lastT = t;
  if (playing) {
    pos += speed * dt;
    if (pos >= dates.length - 1) { pos = dates.length - 1; setPlaying(false); }
  }
  draw(pos, dt);
  syncRange();
  requestAnimationFrame(frame);
}

document.getElementById('rewBtn').addEventListener('click', () => { pos = 0; disp.clear(); setPlaying(true); });
document.getElementById('endBtn').addEventListener('click', () => { pos = dates.length - 1; setPlaying(false); });
playBtn.addEventListener('click', () => setPlaying(!playing));
range.addEventListener('input', () => { pos = +range.value; setPlaying(false); draw(pos); syncRange(); });
// 隐私模式切换（关闭 / 保留姓* / 拼音首字母）
document.getElementById('privSel').addEventListener('change', () => {
  privacy = +document.getElementById('privSel').value;
  draw(pos);
});
// 数据源切换（消息数 / 热度）；热度独立于口径，口径在热度模式视觉淡化
function syncSrcUI() {
  const winSel = document.getElementById('winSel')
  if (dataSrc === 'heat') {
    winSel.style.color = '#c9d2dc'; winSel.style.borderColor = '#e5e7eb'
  } else {
    winSel.style.color = ''; winSel.style.borderColor = ''
  }
}
document.getElementById('srcSel').addEventListener('change', () => {
  dataSrc = document.getElementById('srcSel').value
  syncSrcUI()
  TOP32_BY_DAY = buildTop32ByDay()
  document.getElementById('subEl').textContent = subText()
  draw(pos); syncRange()
})
syncSrcUI()
// 窗口口径切换：热度模式不重算（热度独立于窗口），消息数模式重算 rolling + TOP32_BY_DAY 排名缓存
document.getElementById('winSel').addEventListener('change', () => {
  const v = document.getElementById('winSel').value;
  windowDays = v === 'all' ? Infinity : +v;
  if (dataSrc === 'rolling') {
    rolling = buildRollingAll()
    TOP32_BY_DAY = buildTop32ByDay()
  }
  document.getElementById('subEl').textContent = subText();
  draw(pos);
  syncRange();
});
// 倍速档位滑条（1/2/4/8/16/32 天每秒）
const speedRange = document.getElementById('speedRange');
const speedLbl = document.getElementById('speedLbl');
speedRange.addEventListener('input', () => {
  speed = 1 << +speedRange.value;
  speedLbl.textContent = '×' + speed;
});
// 折线横轴规则（滚动90天 / 全历史压缩）
document.getElementById('axisSel').addEventListener('change', () => {
  lineAxis = document.getElementById('axisSel').value;
  draw(pos);
});
// 线数：对数滑条（1~32，指数等距、允许中间值如 5/10）
const lineRange = document.getElementById('lineRange');
const lineLbl = document.getElementById('lineLbl');
function lineCountFrom(v) { return Math.max(1, Math.min(32, Math.round(Math.pow(2, v * 5)))) }
lineRange.addEventListener('input', () => {
  lineTop = lineCountFrom(+lineRange.value);
  lineLbl.textContent = lineTop;
  draw(pos);
});
// 视图默认参数：柱状=6个月口径+×32；折线=6个月口径+×32+滚动12个月+10线
function applyViewDefaults() {
  const def = mode === 'line'
    ? { windowDays: 180, speed: 32, axis: 'roll12m', lineTop: 10 }
    : { windowDays: 365, speed: 32, axis: null, lineTop: null }
  document.getElementById('winSel').value = String(def.windowDays)
  windowDays = def.windowDays
  rolling = buildRollingAll()
  TOP32_BY_DAY = buildTop32ByDay()
  document.getElementById('subEl').textContent = subText()
  const spIdx = Math.round(Math.log2(def.speed))
  speedRange.value = spIdx
  speed = 1 << spIdx
  speedLbl.textContent = '×' + speed
  if (mode === 'line') {
    document.getElementById('axisSel').value = def.axis
    lineAxis = def.axis
    lineRange.value = Math.log2(def.lineTop) / 5
    lineTop = def.lineTop
    lineLbl.textContent = lineTop
  }
}
// 视图切换（柱状 / 折线）；横轴/线数控件仅折线模式显示
function syncLineCtrls() {
  const isLine = mode === 'line'
  document.getElementById('axisGrp').style.display = isLine ? '' : 'none'
  document.getElementById('lineGrp').style.display = isLine ? '' : 'none'
}
syncLineCtrls();
document.querySelectorAll('#viewBtns button').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('#viewBtns button').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    mode = b.dataset.v;
    syncLineCtrls();
    applyViewDefaults();
    pos = START_POS;   // 切换视图重置到 2022-06-08
    draw(pos);
    syncRange();
  });
});
document.addEventListener('keydown', e => {
  if (e.code === 'Space') { e.preventDefault(); setPlaying(!playing); }
  else if (e.key === 'ArrowRight') { pos = Math.min(pos + 1, dates.length - 1); draw(pos); syncRange(); }
  else if (e.key === 'ArrowLeft') { pos = Math.max(pos - 1, 0); draw(pos); syncRange(); }
});
requestAnimationFrame(frame);
</script>
</body>
</html>
"""

max_cn = f'{maxD[:4]}年{int(maxD[5:7])}月{int(maxD[8:10])}日'
html = (HTML
        .replace('__DAY_DATA__', json.dumps(day_data, ensure_ascii=False))
        .replace('__INITIALS__', json.dumps(INITIALS, ensure_ascii=False))
        .replace('__MIN_DATE__', minD)
        .replace('__MAX_DATE__', maxD)
        .replace('__MAX_CN__', max_cn))
open(OUT, 'w', encoding='utf-8').write(html)
print(f'已生成: {OUT}  {len(html)/1024:.0f} KB, {len(people)} 联系人')
