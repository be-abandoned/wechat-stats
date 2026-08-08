# -*- coding: utf-8 -*-
"""生成私聊库联系人数据看板 HTML v2：下拉选属性 → 大横向条形图排名（自包含，无外部依赖）"""
import os, json, sys, datetime, re
from pypinyin import lazy_pinyin
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE = r'D:\WorkBuddy\微信聊天记录库-私聊'
OUT = os.environ.get('DASH_TMP') or os.path.join(BASE, '数据看板.html')   # 支持临时输出（合并流程用）

try:
    WXID_NAMES = json.load(open(r'D:\WorkBuddy\.workbuddy\wxid_names.json', encoding='utf-8'))['names']
except Exception:
    WXID_NAMES = {}

def sanitize_name(n):
    s = re.sub(r'[\\/:*?"<>|]', '_', n)
    s = re.sub(r'[\xa0\u200b\u200c\u200d\s]+', ' ', s).strip()
    return s.rstrip('.')

def has_chinese_copy(name):
    """该 wxid 目录是否已有中文名副本（有则跳过旧目录，避免看板重复）"""
    raw = WXID_NAMES.get(name, name)
    if raw == name: return False
    new = sanitize_name(raw)
    if not new or new == name: return False
    return os.path.isdir(os.path.join(BASE, new))

def segment_hour(hours):
    return [sum(hours[2:8]), sum(hours[8:14]), sum(hours[14:20]),
            sum(hours[20:24]) + sum(hours[0:2])]

def build_rows():
    rows = []
    for root, dirs, files in os.walk(BASE):
        if 'stats.json' not in files:
            continue
        name = os.path.basename(root)
        if re.match(r'^wxid_[0-9a-zA-Z_-]+$', name) and has_chinese_copy(name):
            continue  # 已有中文名副本，跳过旧 wxid 目录
        with open(os.path.join(root, 'stats.json'), encoding='utf-8') as f:
            st = json.load(f)
        tc = st.get('typeCount', {})
        seg = segment_hour(st.get('hourCount', [0]*24))
        rows.append({
            'name': st.get('display', os.path.basename(root)),
            'dir': os.path.basename(root),   # 目录名（详情图片相对路径用）
            'total': st.get('total', 0),
            'mySend': st.get('mySend', 0),
            'otherSend': st.get('otherSend', 0),
            'myIni': st.get('myIni', 0),
            'otherIni': st.get('otherIni', 0),
            'activeDays': st.get('activeDays', 0),
            'spanDays': st.get('spanDays', 0),
            'avgDaily': round(float(st.get('avgDaily', 0) or 0), 1),
            'seg': seg,
            'text': tc.get('文本', 0), 'img': tc.get('图片', 0), 'emoji': tc.get('表情', 0),
            'video': tc.get('视频', 0), 'voice': tc.get('语音', 0), 'call': tc.get('通话', 0),
            'd': st,   # 完整 stats.json → 点击行弹出的数据概览详情
        })
    rows.sort(key=lambda r: -r['total'])
    return rows

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>微信统计看板</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Microsoft YaHei','PingFang SC',sans-serif; background:#EDEDED; color:#1f2937; padding:28px; }
h1 { font-size:20px; font-weight:700; }
.sub { color:#6b7280; font-size:12px; margin:2px 0 8px; padding-left:34px; line-height:1.4; }
.controls { display:flex; gap:8px; align-items:center; margin-bottom:10px; flex-wrap:wrap; }
.ctrl-label { font-size:13px; color:#6b7280; }
.dd { position:relative; }
.dd-btn { display:flex; align-items:center; gap:10px; padding:7px 12px; border:1px solid #e5e7eb; border-radius:10px; background:#fff; font-size:14px; font-weight:500; color:#1f2937; cursor:pointer; outline:none; min-width:140px; transition:border-color .15s, box-shadow .15s, background .15s; }
.dd-btn:hover { border-color:#cbd5e1; background:#fafbfc; }
.dd.open .dd-btn { border-color:#07C160; box-shadow:0 0 0 3px rgba(7,193,96,.15); }
.dd-btn .arrow { margin-left:auto; display:flex; color:#9ca3af; transition:transform .2s; }
.dd.open .dd-btn .arrow { transform:rotate(180deg); color:#07C160; }
.dd-menu { position:absolute; top:calc(100% + 6px); left:0; width:100%; min-width:100%; background:#fff; border:1px solid #e5e7eb; border-radius:12px; box-shadow:0 12px 32px rgba(15,23,42,.12); padding:6px; z-index:50; max-height:360px; overflow-y:auto; opacity:0; transform:translateY(-6px); pointer-events:none; transition:opacity .16s ease, transform .16s ease; scrollbar-width:none; -ms-overflow-style:none; }
.dd-menu::-webkit-scrollbar { display:none; width:0; height:0; }
.dd.open .dd-menu { opacity:1; transform:none; pointer-events:auto; }
.dd-group { padding:8px 12px 5px; font-size:11px; color:#9ca3af; font-weight:600; letter-spacing:.08em; }
.dd-item { display:flex; align-items:center; gap:8px; padding:8px 12px; border-radius:8px; font-size:14px; color:#374151; cursor:pointer; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.dd-item:hover { background:#F5F5F5; }
.dd-item.sel { color:#07C160; font-weight:600; background:#E9F8EE; }
.dd-item .check { margin-left:auto; opacity:0; color:#07C160; font-size:12px; }
.dd-item.sel .check { opacity:1; }
.btn { padding:7px 14px; border:1px solid #e5e7eb; border-radius:9px; background:#fff; font-size:14px; cursor:pointer; color:#374151; }
.btn:hover { background:#F5F5F5; }
.btn.active { background:#07C160; color:#fff; border-color:#07C160; }
.hint { color:#9ca3af; font-size:12px; margin-left:6px; }
.card { background:#fff; border-radius:10px; box-shadow:0 1px 3px rgba(0,0,0,.06); padding:12px 16px; }
.chart-head { display:flex; justify-content:flex-end; align-items:baseline; margin-bottom:4px; }
.chart-title { font-size:17px; font-weight:700; color:#111827; }
.chart-meta { font-size:12px; color:#9ca3af; }
.row { display:flex; align-items:center; gap:10px; padding:3px 4px; border-bottom:1px solid #E7E7E7; will-change:transform,opacity; }
.row.leaving { opacity:0; transform:translateY(90px); }
.row:hover { background:#F5F5F5; border-radius:8px; }
.rank { width:28px; height:28px; border-radius:8px; background:#eef2f7; color:#64748b; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:11px; flex-shrink:0; }
.rank.r1 { background:#fef3c7; color:#d97706; }
.rank.r2 { background:#e2e8f0; color:#64748b; }
.rank.r3 { background:#ffedd5; color:#ea580c; }
.name { width:60px; font-weight:600; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex-shrink:0; }
.bar-bg { flex:1; height:18px; background:#F5F5F5; border-radius:7px; overflow:hidden; }
.bar { height:100%; border-radius:7px; background:linear-gradient(90deg,#9FEBBB,#07C160); min-width:2px; transition:width 1s cubic-bezier(.4,0,.2,1); }
.val { width:84px; text-align:right; font-weight:600; font-size:13px; font-variant-numeric:tabular-nums; flex-shrink:0; margin-left:10px; }
.unit { color:#9ca3af; font-size:11px; margin-left:2px; font-weight:400; }
.empty { text-align:center; color:#9ca3af; padding:40px; font-size:14px; }
footer { margin-top:16px; color:#9ca3af; font-size:12px; text-align:center; }
.row { cursor:pointer; }
.row:hover .name { color:#07C160; }
/* ── 二级详情页 ── */
#viewDetail { margin:-28px; padding:0 28px 28px; }   /* 抵消 body 内边距：详情页顶部从视口 0 开始，吸顶无"滑一段才冻结" */
.detail-top { position:sticky; top:0; z-index:20; background:#EDEDED; margin:0; padding:28px 0 14px; box-shadow:0 2px 6px rgba(0,0,0,.04); }
.detail-nav { margin-bottom:14px; }
.back-btn { display:inline-flex; align-items:center; padding:8px 16px; border:1px solid #e5e7eb; border-radius:9px; background:#fff; font-size:14px; color:#374151; cursor:pointer; transition:border-color .15s,color .15s; }
.back-btn:hover { border-color:#07C160; color:#07C160; }
.detail-head { display:flex; align-items:center; gap:16px; margin-bottom:18px; }
.d-avatar { width:64px; height:64px; border-radius:50%; background:linear-gradient(135deg,#07C160,#0FAE6A); color:#fff; display:flex; align-items:center; justify-content:center; font-size:26px; font-weight:700; flex-shrink:0; }
.d-name { font-size:24px; font-weight:700; color:#111827; }
.d-sub { font-size:13px; color:#9ca3af; margin-top:4px; }
/* 重要数据大数字横幅（无对比性质的数据） */
.d-hero { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-bottom:18px; }
.d-hero .h-card { background:#fff; border-radius:12px; padding:16px 18px; box-shadow:0 1px 3px rgba(0,0,0,.05); text-align:center; }
.d-hero .h-v { font-size:30px; font-weight:800; color:#111827; font-variant-numeric:tabular-nums; line-height:1.2; }
.d-hero .h-l { font-size:12px; color:#9ca3af; margin-top:4px; }
/* 我 vs 对方 对比表（行=我/对方，列=对比参数） */
.cmp-table { width:100%; border-collapse:separate; border-spacing:0; font-size:13px; }
.cmp-table th { padding:10px 10px; color:#9ca3af; font-size:12px; font-weight:600; border-bottom:1px solid #e5e7eb; text-align:right; white-space:nowrap; }
.cmp-table th:first-child { text-align:left; }
.cmp-table td { padding:12px 10px; text-align:right; font-variant-numeric:tabular-nums; font-weight:700; white-space:nowrap; }
.cmp-table td:first-child { text-align:left; font-size:13px; }
.cmp-table tr.me td { color:#0E9F58; }
.cmp-table tr.other td { color:#4b5563; }
.cmp-table tr.me td:first-child, .cmp-table tr.other td:first-child { color:#374151; font-weight:700; }
.cmp-table tr.me { background:#EDF9F1; }
.cmp-table tr.other { background:#FAFAFA; }
.cmp-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; vertical-align:1px; }
.cmp-dot.me { background:#07C160; }
.cmp-dot.other { background:#cbd5e1; }
.detail-grid { display:flex; flex-direction:column; gap:14px; }
.d-card { background:#fff; border-radius:12px; padding:18px 20px; box-shadow:0 1px 3px rgba(0,0,0,.05); }
.d-card-title { font-size:15px; font-weight:700; color:#111827; margin-bottom:12px; }
.chart-box { width:100%; }
.chart-box svg { display:block; }
.chart-box rect:hover { fill:#07C160; }
.chart-legend { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px; }
.lg-chip { display:inline-flex; align-items:center; gap:8px; padding:8px 18px; border:1px solid #e5e7eb; border-radius:20px; font-size:14px; font-weight:500; color:#374151; cursor:pointer; background:#fff; transition:all .15s; user-select:none; }
.lg-chip:hover { border-color:#cbd5e1; }
.lg-chip.off { opacity:.4; background:#fafafa; }
.lg-chip i { width:14px; height:14px; border-radius:4px; display:inline-block; }
.donut-box { display:flex; align-items:center; gap:24px; flex-wrap:wrap; justify-content:center; padding:6px 0; }
.donut-legend { font-size:13px; color:#374151; min-width:200px; flex:1; max-width:320px; }
.donut-legend .lg-row { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.donut-legend .sw { width:12px; height:12px; border-radius:3px; flex-shrink:0; }
.donut-legend .lg-n { font-weight:600; font-variant-numeric:tabular-nums; margin-left:14px; }
.d-stats { font-size:13px; color:#374151; }
.d-stats .s-group { font-size:12px; font-weight:700; color:#07C160; margin:12px 0 4px; }
.d-stats .s-group:first-child { margin-top:0; }
.d-stats .s-row { display:flex; justify-content:space-between; align-items:baseline; padding:7px 0; border-bottom:1px solid #f5f5f5; gap:16px; }
.d-stats .s-row:last-child { border-bottom:none; }
.d-stats .s-l { color:#9ca3af; flex-shrink:0; }
.d-stats .s-v { font-weight:600; text-align:right; font-variant-numeric:tabular-nums; }
</style>
</head>
<body>
<section id="viewList">
<h1><svg width="20" height="20" viewBox="0 0 24 24" fill="#07C160" style="vertical-align:-4px; margin-right:6px"><path d="M9.5,4C5.36,4 2,6.69 2,10C2,11.86 3.05,13.53 4.7,14.62C4.55,15.22 4.17,16.12 3.79,16.67C3.72,16.77 3.76,16.9 3.86,16.96C3.93,17 4.01,17.01 4.08,17C4.58,16.95 5.78,16.58 6.58,16.07C7.44,16.34 8.4,16.5 9.42,16.5C9.57,16.5 9.72,16.5 9.87,16.49C9.62,16.01 9.5,15.5 9.5,15C9.5,11.41 12.63,8.5 16.5,8.5C16.78,8.5 17.06,8.52 17.33,8.55C16.6,5.94 13.35,4 9.5,4M6.56,6.63C7.08,6.63 7.5,7.05 7.5,7.57C7.5,8.09 7.08,8.51 6.56,8.51C6.04,8.51 5.62,8.09 5.62,7.57C5.62,7.05 6.04,6.63 6.56,6.63M12.44,6.63C12.96,6.63 13.38,7.05 13.38,7.57C13.38,8.09 12.96,8.51 12.44,8.51C11.92,8.51 11.5,8.09 11.5,7.57C11.5,7.05 11.92,6.63 12.44,6.63M16.5,9.5C13.46,9.5 11,11.96 11,15C11,18.04 13.46,20.5 16.5,20.5C17.05,20.5 17.58,20.42 18.08,20.28C18.5,20.54 19.48,20.98 20.02,21.03C20.1,21.04 20.18,21.03 20.24,20.99C20.35,20.93 20.39,20.8 20.32,20.69C19.97,20.19 19.62,19.32 19.48,18.76C20.92,17.88 22,16.6 22,15C22,11.96 19.54,9.5 16.5,9.5M14.25,12.75C14.69,12.75 15.05,13.11 15.05,13.55C15.05,13.99 14.69,14.35 14.25,14.35C13.81,14.35 13.45,13.99 13.45,13.55C13.45,13.11 13.81,12.75 14.25,12.75M18.75,12.75C19.19,12.75 19.55,13.11 19.55,13.55C19.55,13.99 19.19,14.35 18.75,14.35C18.31,14.35 17.95,13.99 17.95,13.55C17.95,13.11 18.31,12.75 18.75,12.75Z"/></svg>微信统计看板</h1>
<div class="sub">人是一切社会关系的总和。<br><span style="display:inline-block; padding-left:8em">——马克思</span></div>

<div class="controls">
  <label class="ctrl-label">排序属性</label>
  <div class="dd">
    <button type="button" class="dd-btn" id="metricBtn">消息总数<span class="arrow"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg></span></button>
    <div class="dd-menu" id="metricMenu"></div>
  </div>
  <label class="ctrl-label">显示</label>
  <div class="dd" style="min-width:130px">
    <button type="button" class="dd-btn" id="limitBtn">Top 20<span class="arrow"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg></span></button>
    <div class="dd-menu" id="limitMenu"></div>
  </div>
  <label class="ctrl-label">时间</label>
  <div class="dd" style="min-width:128px">
    <button type="button" class="dd-btn" id="startBtn">—<span class="arrow"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg></span></button>
    <div class="dd-menu" id="startMenu"></div>
  </div>
  <label class="ctrl-label">至</label>
  <div class="dd" style="min-width:128px">
    <button type="button" class="dd-btn" id="endBtn">—<span class="arrow"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg></span></button>
    <div class="dd-menu" id="endMenu"></div>
  </div>
  <button id="resetTime" class="btn" title="恢复完整统计区间">重置时间</button>
  <button id="sortDir" class="btn active">降序 ▼</button>
  <div class="dd">
    <button type="button" class="dd-btn" id="privBtn">隐私:关<span class="arrow"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg></span></button>
    <div class="dd-menu" id="privMenu"></div>
  </div>
  <button id="refreshBtn" class="btn" title="刷新数据：需要后台刷新服务运行中" style="background:#07C160;color:#fff;border:none">🔄 刷新</button>
  <span id="refreshHint" style="font-size:12px"></span>
  <input id="search" type="text" placeholder="搜索联系人…" style="padding:7px 14px;border:none;border-radius:18px;font-size:14px;outline:none;width:200px;background:#F5F5F5">
</div>

<div class="card">
  <div class="chart-head">
    <div class="chart-meta" id="chartMeta"></div>
  </div>
  <div id="chart" style="position:relative"></div>
</div>
</section>

<!-- ═══ 二级页面：联系人数据概览详情 ═══ -->
<section id="viewDetail" style="display:none">
  <div class="detail-top">
    <div class="detail-nav">
      <button class="back-btn" id="backBtn"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-3px; margin-right:6px"><path d="m15 18-6-6 6-6"/></svg>返回统计</button>
    </div>
    <div class="detail-head">
      <div class="d-avatar" id="dAvatar"></div>
      <div>
        <div class="d-name" id="dName"></div>
        <div class="d-sub" id="dSub"></div>
      </div>
    </div>
  </div>
  <div class="d-hero" id="dHero"></div>
  <div class="d-card" style="margin-bottom:14px">
    <div class="d-card-title">双方互动对比</div>
    <div class="d-compare" id="dCompare"></div>
  </div>
  <div class="detail-grid">
    <div class="d-card wide">
      <div class="d-card-title">每月消息趋势</div>
      <div class="chart-legend" id="dMonthLegend"></div>
      <div id="dMonthChart" class="chart-box"></div>
    </div>
    <div class="d-card wide">
      <div class="d-card-title">时段活跃分布（每日 0-23 时）</div>
      <div id="dHourChart" class="chart-box"></div>
    </div>
    <div class="d-card wide">
      <div class="d-card-title">消息类型分布</div>
      <div id="dTypeChart" class="donut-box"></div>
    </div>
    <div class="d-card wide">
      <div class="d-card-title">互动与内容明细</div>
      <div id="dStats" class="d-stats"></div>
    </div>
  </div>
</section>
<footer style="text-align:right">数据更新时间：__GEN_TIME__</footer>

<script>
const DATA = __DATA_JSON__;
const META = {
  total:['消息总数','条'], mySend:['我发消息','条'], otherSend:['对方发消息','条'],
  myIni:['我主动发起天数','天'], otherIni:['对方主动发起天数','天'],
  activeDays:['活跃天数','天'], spanDays:['时间跨度','天'], avgDaily:['活跃日均消息','条/天'],
  seg0:['时段 02-08时 消息','条'], seg1:['时段 08-14时 消息','条'],
  seg2:['时段 14-20时 消息','条'], seg3:['时段 20-02时 消息','条'],
  text:['文本消息','条'], img:['图片消息','条'], emoji:['表情消息','条'],
  video:['视频消息','条'], voice:['语音消息','条'], call:['通话消息','条'],
};
let sortKey = 'total', desc = true;
let privacy = 0;   // 隐私模式：0 关闭 / 1 保留姓其余* / 2 拼音首字母 / 3 保留第二字
const INITIALS = __INITIALS__;
let limitV = 20;       // 显示条数
let rangeMap = new Map();   // 时间筛选区间内重算的 total/mySend/otherSend（name -> {total,my,other}）

// ── 时间区间筛选（按月，最小 1 个月）──
const fmtMonth = m => m.slice(0, 4) + '年' + m.slice(5) + '月';
let minM = null, maxM = null;
DATA.forEach(r => {
  const mc = (r.d && r.d.monthCount) || {};
  for (const m in mc) { if (!minM || m < minM) minM = m; if (!maxM || m > maxM) maxM = m; }
});
if (!minM) { minM = '2020-01'; maxM = '2026-12'; }
const startMin = minM.slice(0, 4) + '-01';   // 最早时间不得早于最早月所在年份的首月
const endMax = maxM.slice(0, 4) + '-12';     // 最晚时间不得晚于最晚月所在年份的末月
const allMonths = fillMonths(startMin, endMax);
let startM = minM, endM = maxM;              // 默认=完整统计区间

// 排序属性分组（自定义下拉菜单数据源）
const METRIC_GROUPS = [
  { g:'消息量', items:[['total','消息总数'],['mySend','我发消息'],['otherSend','对方发消息'],['text','文本消息'],['img','图片消息'],['emoji','表情消息'],['video','视频消息'],['voice','语音消息'],['call','通话消息']] },
  { g:'活跃度', items:[['activeDays','活跃天数'],['spanDays','时间跨度'],['avgDaily','活跃日均消息'],['myIni','我主动发起天数'],['otherIni','对方主动发起天数']] },
  { g:'时段分布', items:[['seg0','02-08时'],['seg1','08-14时'],['seg2','14-20时'],['seg3','20-02时']] },
];
const LIMIT_ITEMS = [['10','Top 10'],['20','Top 20'],['50','Top 50'],['9999','全部']];
const ARROW_SVG = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';

// 自定义下拉组件：打开/关闭、外部点击收起、选中打勾、按钮同步显示当前值
function initDD(btnId, menuId, groups, onPick, cur){
  const btn = document.getElementById(btnId);
  const menu = document.getElementById(menuId);
  const dd = btn.closest('.dd');
  let html = '';
  groups.forEach(g => {
    if (g.g) html += `<div class="dd-group">${g.g}</div>`;
    (g.items || g).forEach(it => {
      html += `<div class="dd-item" data-v="${it[0]}"><span>${it[1]}</span><span class="check">✓</span></div>`;
    });
  });
  menu.innerHTML = html;
  btn.addEventListener('click', e => { e.stopPropagation(); dd.classList.toggle('open'); });
  menu.addEventListener('click', e => {
    const it = e.target.closest('.dd-item'); if (!it) return;
    onPick(it.dataset.v);
    dd.classList.remove('open');
  });
  document.addEventListener('click', e => { if (!dd.contains(e.target)) dd.classList.remove('open'); });
  function sync(){
    const v = String(cur());
    const label = groups.flatMap(g => g.items || g).find(it => it[0] === v);
    btn.innerHTML = `<span>${label ? label[1] : ''}</span><span class="arrow">${ARROW_SVG}</span>`;
    menu.querySelectorAll('.dd-item').forEach(el => el.classList.toggle('sel', el.dataset.v === v));
  }
  sync();
  return sync;
}

// 脱敏：0 关闭 / 1 保留姓其余* / 2 拼音首字母 / 3 保留第二字；超 3 字截前 3
function maskName(n){
  const nm = String(n);
  let s = nm;
  if (privacy === 1) s = nm[0] + '*'.repeat(nm.length - 1);
  else if (privacy === 2) s = INITIALS[nm] || nm;
  else if (privacy === 3) {   // 保留第二字，其他用 *
    const c = nm[1] || nm[0];
    s = nm.length >= 3 ? '*' + c + '*' : nm.length === 2 ? '*' + c : c;
  }
  return s.length > 3 ? s.slice(0, 3) : s;
}
// 列表名字：统一只显示前 3 个字（先按隐私脱敏）；详情页展示全名（同样脱敏）
function listName(n){
  return maskName(n);
}

function getVal(r, k){
  // 时间筛选区间内，全部指标优先用区间重算值（按月聚合求和）
  const rr = rangeMap.get(r.name);
  if (rr) {
    if (k === 'seg0' || k === 'seg1' || k === 'seg2' || k === 'seg3') return rr.seg[parseInt(k[3])];
    if (k in rr) return rr[k];
  }
  return k.startsWith('seg') ? r.seg[parseInt(k[3])] : r[k];
}

// DOM 缓存：name -> row 元素（保留节点以支持柱子伸缩 + FLIP 行移动动画）
let rowCache = new Map();
const EASE = 'cubic-bezier(.65,0,.35,1)';   // easeInOutQuart：先加速后减速
let barAnim = new Map();                     // bar -> {raf}

function makeRow(name){
  const el = document.createElement('div');
  el.className = 'row';
  el.dataset.name = name;   // 点击行 → 打开该联系人的数据概览
  el.innerHTML = `
    <div class="rank"></div>
    <div class="name"></div>
    <div class="val"><span class="num"></span><span class="unit"></span></div>
    <div class="bar-bg"><div class="bar"></div></div>`;
  return el;
}
function easeInOutCubic(p){ return p<0.5 ? 4*p*p*p : 1-Math.pow(-2*p+2,3)/2; }

// JS 帧动画驱动柱子伸缩（1s，easeInOutCubic），绝对可靠
function animateBar(bar, to){
  if (barAnim.has(bar)) cancelAnimationFrame(barAnim.get(bar).raf);
  const from = parseFloat(bar.style.width) || 0;
  const t0 = performance.now(), dur = 1000;
  function step(now){
    const p = Math.min(1, (now - t0) / dur);
    bar.style.width = (from + (to - from) * easeInOutCubic(p)) + '%';
    if (p < 1) barAnim.set(bar, { raf: requestAnimationFrame(step) });
    else barAnim.delete(bar);
  }
  barAnim.set(bar, { raf: requestAnimationFrame(step) });
}

function render(){
  const kw = document.getElementById('search').value.trim().toLowerCase();
  const lim = limitV;
  let rows = DATA.filter(r => !kw || r.name.toLowerCase().includes(kw));
  // 时间区间预计算：区间内所有指标按月聚合（默认完整区间=全量）
  rangeMap = new Map();
  rows.forEach(r => {
    const mc = (r.d && r.d.monthCount) || {};
    const agg = { total: 0, mySend: 0, otherSend: 0, text: 0, img: 0, emoji: 0, video: 0, voice: 0, call: 0,
                  activeDays: 0, myIni: 0, otherIni: 0, seg: [0, 0, 0, 0] };
    for (const m in mc) {
      if (m >= startM && m <= endM) {
        const mm = mc[m];
        agg.total += mm.total || 0; agg.mySend += mm.my || 0; agg.otherSend += mm.other || 0;
        agg.text += mm['文本'] || 0; agg.img += mm['图片'] || 0; agg.emoji += mm['表情'] || 0;
        agg.video += mm['视频'] || 0; agg.voice += mm['语音'] || 0; agg.call += mm['通话'] || 0;
        agg.activeDays += mm.activeDays || 0; agg.myIni += mm.myIni || 0; agg.otherIni += mm.otherIni || 0;
        const s = mm.seg || [];
        for (let i = 0; i < 4; i++) agg.seg[i] += s[i] || 0;
      }
    }
    // 区间跨度（天）：结束月末 - 开始月初 + 1
    const sy = +startM.slice(0, 4), sm = +startM.slice(5), ey = +endM.slice(0, 4), em = +endM.slice(5);
    agg.spanDays = Math.round((Date.UTC(ey, em, 0) - Date.UTC(sy, sm - 1, 1)) / 86400000) + 1;
    agg.avgDaily = agg.activeDays ? +(agg.total / agg.activeDays).toFixed(1) : 0;
    rangeMap.set(r.name, agg);
  });
  rows.sort((a,b) => desc ? getVal(b,sortKey)-getVal(a,sortKey) : getVal(a,sortKey)-getVal(b,sortKey));
  const shown = rows.slice(0, lim);
  const maxV = Math.max(...shown.map(r=>getVal(r,sortKey)), 1);
  const [title, unit] = META[sortKey];

  document.getElementById('chartMeta').textContent = `显示 ${shown.length} / ${rows.length} 人 · 最大值 ${fmt(maxV)} ${unit} · ${fmtMonth(startM)} ~ ${fmtMonth(endM)}`;

  const chart = document.getElementById('chart');
  if (!rows.length) { chart.innerHTML = '<div class="empty">没有匹配的联系人</div>'; rowCache.clear(); return; }
  const emptyEl = chart.querySelector('.empty');
  if (emptyEl) emptyEl.remove();

  // ── FLIP 第一步（First）：同步记录所有现有行的视觉位置 ──
  const first = new Map();
  rowCache.forEach((el, name) => { first.set(name, el.getBoundingClientRect().top); });

  // ── 第二步：退榜行固定到当前视觉位置并脱离文档流（不影响其他人布局） ──
  const keep = new Set(shown.map(r => r.name));
  const leaving = [];
  const chartRect = chart.getBoundingClientRect();
  rowCache.forEach((el, name) => {
    if (!keep.has(name)) {
      const rc = el.getBoundingClientRect();
      el.style.position = 'absolute';
      el.style.top = (rc.top - chartRect.top + chart.scrollTop) + 'px';
      el.style.left = (rc.left - chartRect.left) + 'px';
      el.style.width = rc.width + 'px';
      el.style.zIndex = '5';
      el.style.pointerEvents = 'none';
      leaving.push(el);
      rowCache.delete(name);
    }
  });

  // ── 第三步（Last）：更新内容 + 按新顺序重排 DOM ──
  shown.forEach((r, idx) => {
    let el = rowCache.get(r.name);
    const isNew = !el;
    if (isNew) { el = makeRow(r.name); rowCache.set(r.name, el); }
    const v = getVal(r, sortKey);
    const w = Math.max(2, Math.round(v / maxV * 100));
    const bar = el.querySelector('.bar');
    if (isNew || !parseFloat(bar.style.width)) bar.style.width = w + '%';  // 新行直接到位
    else animateBar(bar, w);                                               // 已有行：柱子平滑伸缩
    el.querySelector('.num').textContent = fmt(v);
    el.querySelector('.unit').textContent = unit;
    const nm = listName(r.name);
    el.querySelector('.name').textContent = nm;
    el.querySelector('.name').title = privacy ? '' : r.name;
    const rkEl = el.querySelector('.rank');
    rkEl.textContent = idx + 1;
    rkEl.className = 'rank ' + (idx===0?'r1':idx===1?'r2':idx===2?'r3':'');
    chart.appendChild(el);   // 已有节点 = 移动；新节点 = 插入
  });

  // ── 第四步（Invert）：同一帧内同步施加反向位移，浏览器来不及绘制中间帧 ──
  const movers = [];
  shown.forEach(r => {
    const el = rowCache.get(r.name);
    el.style.transition = 'none';
    if (first.has(r.name)) {
      const delta = first.get(r.name) - el.getBoundingClientRect().top;
      if (Math.abs(delta) > 0.5) {
        el.style.transform = `translateY(${delta}px)`;   // 视觉上仍在旧位置
        movers.push(el);
      } else {
        el.style.transform = '';
      }
    } else {
      el.style.transform = 'translateY(60px)';          // 新入榜：从下方滑入
      el.style.opacity = '0';
      movers.push(el);
    }
  });
  void chart.offsetHeight;   // 一次性强制 reflow，让 Invert 状态生效

  // ── 第五步（Play）：启动过渡，各行滑向新位置；退榜行下滑淡出 ──
  movers.forEach(el => {
    el.style.transition = `transform 1s ${EASE}, opacity 1s ease`;
    el.style.transform = '';
    el.style.opacity = '1';
  });
  leaving.forEach(el => {
    el.style.transition = `transform 1s ${EASE}, opacity .8s ease`;
    el.style.transform = 'translateY(60px)';
    el.style.opacity = '0';
  });
  if (leaving.length) setTimeout(() => leaving.forEach(el => el.remove()), 1050);
}
function fmt(n){ return Number(n).toLocaleString('zh-CN'); }

// ── 二级页面：联系人数据概览详情 ──
const DATA_MAP = new Map(DATA.map(r => [r.name, r]));
const TYPE_ORDER = ['文本','图片','表情','语音','视频','通话'];
const TYPE_COLORS = { '文本':'#22C55E','图片':'#F59E0B','表情':'#3B82F6','语音':'#8B5CF6','视频':'#EC4899','通话':'#EF4444' };
const SVG_NS = 'http://www.w3.org/2000/svg';

function fmtDur(ms){
  if (ms == null) return '—';
  const m = Math.round(ms / 60000);
  if (m < 1) return Math.round(ms / 1000) + ' 秒';
  if (m < 60) return m + ' 分钟';
  const h = Math.floor(m / 60), mm = m % 60;
  if (h < 48) return h + ' 小时 ' + mm + ' 分';
  return Math.floor(h / 24) + ' 天 ' + h % 24 + ' 小时';
}
function fmtPct(r){ return r == null ? '—' : Math.round(r * 100) + '%'; }
function fmtNum(v){
  if (v >= 10000) return (v / 10000).toFixed(1).replace(/[.]0$/, '') + '万';
  return fmt(v);
}
// 生成"整数"刻度（1/2/5×10^n 步进），并保证轴顶 4×step 一定 ≥ 实际最大值（否则曲线会冲出图表）
function niceTicks(max){
  const rough = (max || 1) / 4;
  const pow = Math.pow(10, Math.floor(Math.log10(rough)));
  const norm = rough / pow;
  let step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10) * pow;
  while (4 * step < max) step *= 2;
  return { ticks: [step, 2 * step, 3 * step, 4 * step], max: 4 * step };
}
function sEl(tag, attrs, parent){
  const n = document.createElementNS(SVG_NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}

// 补全首末月之间的连续月份序列（忠实线性时间轴，空月不跳过）
function fillMonths(first, last){
  const [y1, m1] = first.split('-').map(Number);
  const [y2, m2] = last.split('-').map(Number);
  const res = [];
  let y = y1, m = m1;
  while (y < y2 || (y === y2 && m <= m2)) {
    res.push(`${y}-${String(m).padStart(2, '0')}`);
    m++; if (m > 12) { m = 1; y++; }
  }
  return res;
}

// 每月消息：左轴当月总数 + 右轴三条累计线（总数/我/对方），图例可多选显隐
const MONTH_LINES = [
  { key: 'total',    label: '当月总数',     color: '#9AA5B1', axis: 'l' },
  { key: 'cum',      label: '累计消息总数', color: '#9B8CFF', axis: 'r' },
  { key: 'cumMy',    label: '我累计消息数', color: '#5B8DEF', axis: 'r' },
  { key: 'cumOther', label: '对方累计消息数', color: '#F2A65A', axis: 'r' },
];
const monthVis = { total: true, cum: true, cumMy: false, cumOther: false };
let monthCtx = null;   // 图表上下文（供图例点击后重绘线层）

function drawMonthChart(id, monthCount, legendId){
  const box = document.getElementById(id);
  box.innerHTML = '';   // 清空容器，避免反复进入详情页叠加多幅图
  const monthsRaw = Object.keys(monthCount).sort();
  if (!monthsRaw.length) { box.innerHTML = '<div class="empty">无数据</div>'; return; }
  // 补全首末月之间所有月份：横轴忠实线性反映时间，空月补 0（不跳过）
  const months = fillMonths(monthsRaw[0], monthsRaw[monthsRaw.length - 1]);
  const rows = months.map(m => monthCount[m] || {});
  const my = rows.map(r => r.my || 0), other = rows.map(r => r.other || 0);
  const total = rows.map(r => r.total || 0);
  let aM = 0, aO = 0, aT = 0;
  const cumMy = my.map(v => (aM += v));
  const cumOther = other.map(v => (aO += v));
  const cum = total.map(v => (aT += v));
  const lt = niceTicks(Math.max(...total));
  const rt = niceTicks(Math.max(cum[cum.length - 1], cumMy[cumMy.length - 1], cumOther[cumOther.length - 1]));
  const W = 680, H = 280, PL = 52, PR = 52, PT = 20, PB = 38;
  const iw = W - PL - PR, ih = H - PT - PB;
  const x = i => PL + iw * i / (months.length - 1);
  const yL = v => PT + ih - ih * v / lt.max;
  const yR = v => PT + ih - ih * v / rt.max;
  const svg = sEl('svg', { width: '100%', viewBox: `0 0 ${W} ${H}` }, box);
  // 左轴网格 + 刻度（当月数量级）
  lt.ticks.forEach(t => {
    sEl('line', { x1: PL, y1: yL(t), x2: W - PR, y2: yL(t), stroke: '#f0f0f0', 'stroke-width': 1 }, svg);
    sEl('text', { x: PL - 8, y: yL(t) + 4, 'text-anchor': 'end', 'font-size': 10, fill: '#9ca3af' }, svg).textContent = fmtNum(t);
  });
  // 右轴刻度（累计数量级，不画网格避免错位）
  rt.ticks.forEach(t => {
    sEl('text', { x: W - PR + 8, y: yR(t) + 4, 'text-anchor': 'start', 'font-size': 10, fill: '#9ca3af' }, svg).textContent = fmtNum(t);
  });
  // X 轴月份标签（间隔显示防重叠）
  const step = Math.max(1, Math.ceil(months.length / 12));
  months.forEach((m, i) => {
    if (i % step !== 0 && i !== months.length - 1) return;
    sEl('text', { x: x(i), y: H - PB + 20, 'text-anchor': 'middle', 'font-size': 10, fill: '#9ca3af' }, svg).textContent = m.slice(2);
  });
  const lineG = sEl('g', {}, svg);
  monthCtx = { months, total, cum, cumMy, cumOther, x, yL, yR, lineG };
  buildMonthLegend(legendId);
  drawMonthLines();
}
function drawMonthLines(){
  if (!monthCtx) return;
  const { lineG } = monthCtx;
  lineG.innerHTML = '';
  monthCtx.paths = {};
  let idx = 0;
  MONTH_LINES.forEach(L => {
    if (monthVis[L.key]) showMonthLine(L, idx++);
  });
}
function getLineVals(L){
  const { total, cum, cumMy, cumOther } = monthCtx;
  return L.key === 'total' ? total : L.key === 'cum' ? cum : L.key === 'cumMy' ? cumMy : cumOther;
}
// 显示一条线（从左往右绘制动画）；idx 用于多线错开
function showMonthLine(L, idx){
  const { x, yL, yR, lineG } = monthCtx;
  const vals = getLineVals(L);
  const yfn = L.axis === 'l' ? yL : yR;
  const d = 'M' + vals.map((v, i) => `${x(i).toFixed(1)},${yfn(v).toFixed(1)}`).join(' L');
  const p = sEl('path', { d, fill: 'none', stroke: L.color, 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, lineG);
  sEl('title', {}, p).textContent = L.label;
  monthCtx.paths[L.key] = p;
  const len = p.getTotalLength();
  if (len > 1) {
    p.style.strokeDasharray = len;
    p.style.strokeDashoffset = len;
    setTimeout(() => {
      p.style.transition = 'stroke-dashoffset .9s cubic-bezier(.25,.8,.25,1)';
      p.style.strokeDashoffset = '0';
    }, (idx || 0) * 120);
  }
}
// 隐藏一条线（淡出后移除，不触碰其他线）
function hideMonthLine(L){
  const p = monthCtx.paths[L.key];
  if (!p) return;
  delete monthCtx.paths[L.key];
  p.style.transition = 'opacity .35s ease';
  p.style.opacity = '0';
  setTimeout(() => p.remove(), 360);
}
function buildMonthLegend(legendId){
  const legend = document.getElementById(legendId);
  legend.innerHTML = '';
  MONTH_LINES.forEach(L => {
    const chip = document.createElement('span');
    chip.className = 'lg-chip' + (monthVis[L.key] ? '' : ' off');
    chip.innerHTML = `<i style="background:${L.color}"></i>${L.label}`;
    chip.addEventListener('click', () => {
      monthVis[L.key] = !monthVis[L.key];
      chip.classList.toggle('off', !monthVis[L.key]);
      if (monthVis[L.key]) showMonthLine(L, 0);   // 只绘制这一条
      else hideMonthLine(L);                       // 只淡出这一条
    });
    legend.appendChild(chip);
  });
}

// 时段活跃：柱状图 + 整数参考线（0-23 时，7 点起排，低饱和简约色）
// 动态效果：首次滚动进入视口时，柱子从左到右依次"长"出来
function drawHourChart(id, hourCount){
  const box = document.getElementById(id);
  box.innerHTML = '';   // 清空容器，避免反复进入详情页叠加多幅图
  const arr = hourCount || [];
  if (!arr.length) { box.innerHTML = '<div class="empty">无数据</div>'; return; }
  const W = 680, H = 260, PL = 46, PR = 20, PT = 20, PB = 38;
  const iw = W - PL - PR, ih = H - PT - PB;
  const order = [...Array(24).keys()].map(h => (h + 7) % 24);   // 7,8,...,23,0,...,6
  const { ticks, max } = niceTicks(Math.max(...arr));
  const svg = sEl('svg', { width: '100%', viewBox: `0 0 ${W} ${H}` }, box);
  ticks.forEach(t => {
    sEl('line', { x1: PL, y1: PT + ih - ih * t / max, x2: W - PR, y2: PT + ih - ih * t / max, stroke: '#f0f0f0', 'stroke-width': 1 }, svg);
    sEl('text', { x: PL - 8, y: PT + ih - ih * t / max + 4, 'text-anchor': 'end', 'font-size': 10, fill: '#9ca3af' }, svg).textContent = fmtNum(t);
  });
  const bw = iw / 24;
  const baseY = PT + ih;
  const bars = [];
  order.forEach((h, i) => {
    const v = arr[h] || 0;
    const hh = ih * v / max;
    const x0 = PL + iw * i / 24 + bw * .2, w = bw * .6;
    const r = sEl('rect', { x: x0, y: baseY, width: w, height: 0, rx: 1.5, fill: '#A8D8BC' }, svg);
    sEl('title', {}, r).textContent = `${h} 时：${fmt(v)} 条`;
    if (hh > 0) bars.push({ el: r, target: hh, baseY });
    if (i % 2 === 0 || i === 23) {
      sEl('text', { x: PL + iw * i / 24 + bw / 2, y: H - PB + 20, 'text-anchor': 'middle', 'font-size': 9.5, fill: '#9ca3af' }, svg).textContent = h + '时';
    }
  });
  // 首次进入视口（基本可见）时触发生长动画，只触发一次
  let grown = false;
  const io = new IntersectionObserver(entries => {
    if (entries.some(en => en.isIntersecting) && !grown) {
      grown = true;
      growBars(bars);
      io.disconnect();
    }
  }, { threshold: 0.15, rootMargin: '0px 0px -10% 0px' });
  io.observe(box);
}
// 柱子从左到右依次"长"出来（easeOutCubic 帧动画，每根错开 35ms）
function growBars(bars, dur = 650, stepDelay = 35){
  bars.forEach((b, i) => {
    const t0 = performance.now() + i * stepDelay;
    const baseY = b.baseY, target = b.target;
    (function step(now){
      if (now < t0) { requestAnimationFrame(step); return; }
      const p = Math.min(1, (now - t0) / dur);
      const e = 1 - Math.pow(1 - p, 3);   // easeOutCubic
      b.el.setAttribute('height', (target * e).toFixed(1));
      b.el.setAttribute('y', (baseY - target * e).toFixed(1));
      if (p < 1) requestAnimationFrame(step);
    })(performance.now());
  });
}

// 消息类型：环形图（SVG 弧线绘制，每段独立 path）+ 中心总数 + 图例
function drawTypeDonut(id, typeCount){
  const box = document.getElementById(id);
  box.innerHTML = '';
  const items = TYPE_ORDER.map(k => ({ k, v: typeCount[k] || 0, c: TYPE_COLORS[k] })).filter(it => it.v > 0);
  const sum = items.reduce((a, b) => a + b.v, 0);
  if (!sum) { box.innerHTML = '<div class="empty">无数据</div>'; return; }
  const S = 260, R = 92, SW = 36, CX = S / 2, CY = S / 2;
  const svg = sEl('svg', { width: S, height: S, viewBox: `0 0 ${S} ${S}` }, box);
  // 底色环
  sEl('circle', { cx: CX, cy: CY, r: R, fill: 'none', stroke: '#F0F0F0', 'stroke-width': SW }, svg);
  // 每段一条弧线（从 12 点起顺时针），初始不可见；首次下滑进入视口时"转圈画满整个环"
  let acc = 0;
  const paths = [];
  items.forEach((it, idx) => {
    const frac = it.v / sum;
    const a0 = -Math.PI / 2 + acc * 2 * Math.PI;
    const a1 = a0 + frac * 2 * Math.PI;
    const x0 = CX + R * Math.cos(a0), y0 = CY + R * Math.sin(a0);
    const x1 = CX + R * Math.cos(a1), y1 = CY + R * Math.sin(a1);
    const large = frac > .5 ? 1 : 0;
    const p = sEl('path', {
      d: `M ${x0.toFixed(2)} ${y0.toFixed(2)} A ${R} ${R} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`,
      fill: 'none', stroke: it.c, 'stroke-width': SW,
    }, svg);
    sEl('title', {}, p).textContent = `${it.k}：${fmt(it.v)} 条（${(frac * 100).toFixed(1)}%）`;
    const len = p.getTotalLength();
    if (len > 1) { p.style.strokeDasharray = len; p.style.strokeDashoffset = len; }  // 初始整段隐藏
    paths.push(p);
    acc += frac;
  });
  // 中心总数：环画完后淡入（初始透明）
  const centerT = sEl('text', { x: CX, y: CY - 2, 'text-anchor': 'middle', 'font-size': 30, 'font-weight': 800, fill: '#111827', opacity: 0 }, svg);
  centerT.textContent = fmt(sum);
  centerT.style.transition = 'opacity .4s ease';
  sEl('text', { x: CX, y: CY + 20, 'text-anchor': 'middle', 'font-size': 12, fill: '#9ca3af' }, svg).textContent = '条消息';
  // 首次进入视口（基本可见）时触发转圈动画，只播放一次
  let played = false;
  const io = new IntersectionObserver(entries => {
    if (entries.some(en => en.isIntersecting) && !played) {
      played = true;
      paths.forEach((p, idx) => {
        const len = p.getTotalLength();
        if (len > 1) {
          setTimeout(() => {
            p.style.transition = 'stroke-dashoffset .55s cubic-bezier(.25,.8,.25,1)';
            p.style.strokeDashoffset = '0';
          }, idx * 300);
        }
      });
      setTimeout(() => { centerT.style.opacity = '1'; }, paths.length * 300 + 550);
      io.disconnect();
    }
  }, { threshold: 0.15, rootMargin: '0px 0px -10% 0px' });
  io.observe(box);
  // 图例（色块 + 名称 + 数量 + 百分比）
  const leg = document.createElement('div');
  leg.className = 'donut-legend';
  leg.innerHTML = items.map(it =>
    `<div class="lg-row"><span class="sw" style="background:${it.c}"></span><span>${it.k}</span><span class="lg-n">${fmt(it.v)} · ${(it.v / sum * 100).toFixed(1).replace(/[.]0$/, '')}%</span></div>`).join('');
  box.appendChild(leg);
}

function renderDetail(name){
  const r = DATA_MAP.get(name);
  if (!r) return;
  const d = r.d || {};
  const fmtD = ts => ts ? new Date(ts).toLocaleDateString('zh-CN') : '—';
  const shown = maskName(name);   // 详情页名字按隐私模式脱敏
  const dnEl = document.getElementById('dName');
  dnEl.dataset.real = name;
  dnEl.textContent = shown;
  document.getElementById('dAvatar').textContent = Array.from(shown)[0];
  const pctMy = r.total ? Math.round(r.mySend / r.total * 100) : 0;
  document.getElementById('dSub').textContent = `统计区间 ${fmtD(d.firstTs)} ~ ${fmtD(d.lastTs)}`;
  // 重要数据横幅（无对比性质的数据，单独突出展示）
  const hero = [
    ['总消息', fmt(r.total) + ' 条'],
    ['活跃日均消息', d.avgDaily == null ? '—' : d.avgDaily + ' 条/天'],
    ['活跃天数', d.activeDays == null ? '—' : d.activeDays + ' 天'],
    ['时间跨度', d.spanDays == null ? '—' : d.spanDays + ' 天'],
    ['最长连续聊天', d.bestStreak ? d.bestStreak.len + ' 天' : '—'],
  ];
  document.getElementById('dHero').innerHTML = hero.map(h =>
    `<div class="h-card"><div class="h-v">${h[1]}</div><div class="h-l">${h[0]}</div></div>`).join('');
  // 我 vs 对方 对比表（上下两行，横着是不同对比参数）
  document.getElementById('dCompare').innerHTML =
    `<table class="cmp-table">
      <thead><tr><th></th><th>发送消息</th><th>主动发起天数</th><th>回复间隔中位数</th><th>回复间隔平均值</th><th>一小时内回复率</th></tr></thead>
      <tbody>
        <tr class="me">
          <td><span class="cmp-dot me"></span>我</td>
          <td>${fmt(r.mySend)}（${pctMy}%）</td>
          <td>${d.myIni == null ? '—' : d.myIni + ' 天'}</td>
          <td>${fmtDur(d.replyMedianMy)}</td>
          <td>${fmtDur(d.replyMeanMy)}</td>
          <td>${fmtPct(d.reply1hMy)}</td>
        </tr>
        <tr class="other">
          <td><span class="cmp-dot other"></span>对方</td>
          <td>${fmt(r.otherSend)}（${100 - pctMy}%）</td>
          <td>${d.otherIni == null ? '—' : d.otherIni + ' 天'}</td>
          <td>${fmtDur(d.replyMedianOther)}</td>
          <td>${fmtDur(d.replyMeanOther)}</td>
          <td>${fmtPct(d.reply1hOther)}</td>
        </tr>
      </tbody>
    </table>`;
  drawMonthChart('dMonthChart', d.monthCount || {}, 'dMonthLegend');
  drawHourChart('dHourChart', d.hourCount || []);
  drawTypeDonut('dTypeChart', d.typeCount || {});
  // 互动与内容明细（页面最底部）
  const srows = (l, v) => `<div class="s-row"><span class="s-l">${l}</span><span class="s-v">${v}</span></div>`;
  document.getElementById('dStats').innerHTML =
    `<div class="s-group">互动活跃度</div>` +
    srows('收发占比', `我 ${pctMy}% / 对方 ${100 - pctMy}%`) +
    srows('回复中位数', `我 ${fmtDur(d.replyMedianMy)} · 对方 ${fmtDur(d.replyMedianOther)}`) +
    srows('回复平均值', `我 ${fmtDur(d.replyMeanMy)} · 对方 ${fmtDur(d.replyMeanOther)}`) +
    srows('1小时内回复率', `我 ${fmtPct(d.reply1hMy)} · 对方 ${fmtPct(d.reply1hOther)}`) +
    srows('最长连续聊天', d.bestStreak ? `连续 ${d.bestStreak.len} 天（${d.bestStreak.start} ~ ${d.bestStreak.end}）` : '—') +
    `<div class="s-group">内容结构</div>` +
    srows('文本平均长度', d.textAvg == null ? '—' : d.textAvg + ' 字') +
    srows('最长文本', d.maxTextLen == null ? '—' : d.maxTextLen + ' 字') +
    srows('已缓存图片', d.imgCached == null ? '—' : d.imgCached + ' 张') +
    srows('统计区间', `${fmtD(d.firstTs)} ~ ${fmtD(d.lastTs)}`);
}

// 路由：列表 ⇄ 详情（支持浏览器前进/后退）
let tipTimer;
function flashTip(msg){
  let t = document.getElementById('tip');
  if (!t) {
    t = document.createElement('div'); t.id = 'tip';
    t.style.cssText = 'position:fixed;left:50%;top:46%;transform:translate(-50%,-50%);background:#1f2937;color:#fff;padding:12px 20px;border-radius:10px;font-size:14px;z-index:200;opacity:0;transition:opacity .2s;pointer-events:none;box-shadow:0 8px 24px rgba(0,0,0,.2)';
    document.body.appendChild(t);
  }
  t.textContent = msg; t.style.opacity = '1';
  clearTimeout(tipTimer); tipTimer = setTimeout(() => t.style.opacity = '0', 1500);
}
function showDetail(name){
  document.getElementById('viewList').style.display = 'none';
  document.getElementById('viewDetail').style.display = '';
  window.scrollTo(0, 0);
  renderDetail(name);
  history.pushState({ view: 'detail', name }, '', '#/detail/' + encodeURIComponent(name));
}
function showList(){
  document.getElementById('viewDetail').style.display = 'none';
  document.getElementById('viewList').style.display = '';
  // 显式切到列表视图，不依赖 history.back()（历史栈可能有多条详情记录导致退回上一个详情页）
  history.pushState({ view: 'list' }, '', '#/');
}
window.addEventListener('popstate', e => {
  const st = e.state;
  if (st && st.view === 'detail' && st.name) {
    document.getElementById('viewList').style.display = 'none';
    document.getElementById('viewDetail').style.display = '';
    renderDetail(st.name);
    window.scrollTo(0, 0);
  } else {
    document.getElementById('viewDetail').style.display = 'none';
    document.getElementById('viewList').style.display = '';
  }
});
document.getElementById('backBtn').addEventListener('click', showList);
document.getElementById('chart').addEventListener('click', e => {
  const row = e.target.closest('.row');
  if (row && row.dataset.name) showDetail(row.dataset.name);
});

const syncMetric = initDD('metricBtn', 'metricMenu', METRIC_GROUPS, v => { sortKey = v; render(); syncMetric(); }, () => sortKey);
const syncLimit = initDD('limitBtn', 'limitMenu', [{ items: LIMIT_ITEMS }], v => { limitV = parseInt(v); render(); syncLimit(); }, () => String(limitV));
// 时间区间下拉（按月，联动保证开始 ≤ 结束）
const MONTH_ITEMS = allMonths.map(m => [m, fmtMonth(m)]);
const syncStart = initDD('startBtn', 'startMenu', [{ items: MONTH_ITEMS }],
  v => { startM = v; if (startM > endM) { endM = startM; syncEnd(); } render(); syncStart(); }, () => startM);
const syncEnd = initDD('endBtn', 'endMenu', [{ items: MONTH_ITEMS }],
  v => { endM = v; if (endM < startM) { startM = endM; syncStart(); } render(); syncEnd(); }, () => endM);
document.getElementById('resetTime').addEventListener('click', () => {
  startM = minM; endM = maxM;
  syncStart(); syncEnd(); render();
});
document.getElementById('search').addEventListener('input', render);
document.getElementById('sortDir').addEventListener('click', () => {
  desc = !desc;
  const b = document.getElementById('sortDir');
  b.textContent = desc ? '降序 ▼' : '升序 ▲';
  b.classList.toggle('active', desc);
  render();
});
// 隐私模式下拉（与排序/显示/时间区间同款 dd 组件）
const PRIV_ITEMS = [['0','隐私:关'],['1','保留姓*'],['2','首字母'],['3','第二字']];
const syncPriv = initDD('privBtn', 'privMenu', [{ items: PRIV_ITEMS }], v => {
  privacy = parseInt(v);
  // 直接更新现有行名字（不触发重排动画），悬停提示同步隐藏防泄露
  rowCache.forEach((el, name) => {
    el.querySelector('.name').textContent = listName(name);
    el.querySelector('.name').title = privacy ? '' : name;
  });
  // 若正停留在详情页，同步脱敏/恢复详情页标题与头像
  const dnEl = document.getElementById('dName');
  if (dnEl.dataset.real && document.getElementById('viewDetail').style.display !== 'none') {
    const shown = maskName(dnEl.dataset.real);
    dnEl.textContent = shown;
    document.getElementById('dAvatar').textContent = Array.from(shown)[0];
  }
  syncPriv();
}, () => String(privacy));
// 暴露当前脱敏函数给壳层（刷新完成弹窗使用）
window.__dashMask = n => maskName(n);
document.getElementById('refreshBtn').addEventListener('click', async () => {
  const btn = document.getElementById('refreshBtn'), hint = document.getElementById('refreshHint')
  const modal = document.getElementById('refreshModal'), bar = document.getElementById('mProgBar'), txt = document.getElementById('mProgText'), closeBtn = document.getElementById('mClose')
  const showModal = () => { modal.style.display = 'flex'; bar.style.width = '0%'; txt.textContent = '准备…'; closeBtn.style.display = 'none' }
  const closeModal = () => { modal.style.display = 'none' }
  closeBtn.addEventListener('click', closeModal)

  // 探测服务
  let alive = false
  try { const p = await fetch('http://127.0.0.1:8765/'); alive = p.ok } catch {}
  if (!alive) {
    showModal(); txt.textContent = '正在启动刷新服务…'
    try { location.href = 'wechatdash://start' } catch {}
    await new Promise(r => setTimeout(r, 3500))
    try { const p = await fetch('http://127.0.0.1:8765/'); alive = p.ok } catch {}
    if (!alive) { txt.textContent = '❌ 服务启动失败，请双击「启动看板.bat」'; closeBtn.style.display = 'inline-block'; return }
    txt.textContent = '服务已启动，开始刷新…'
  }
  // 显示模态，后台执行刷新，轮询进度；按钮保持禁用直到完成
  btn.disabled = true; btn.textContent = '⏳ 刷新中…'; hint.textContent = ''
  showModal()
  fetch('http://127.0.0.1:8765/refresh').catch(() => {})
  const timer = setInterval(async () => {
    try {
      const p = await fetch('http://127.0.0.1:8765/progress').then(r => r.json())
      bar.style.width = (p.pct || 0) + '%'
      txt.textContent = p.step || ''
      if (p.step === '完成') {
        clearInterval(timer); bar.style.width = '100%'
        // 拉取本次刷新的增量统计（时间范围 + 新增联系人，名字按隐私设置）
        let statHtml = '✅ 刷新完成！'
        try {
          const st = await fetch('http://127.0.0.1:8765/stats').then(r => r.json())
          const mk = window.__dashMask || (n => n)
          if (st && st.sessions && st.sessions.length) {
            const total = st.sessions.reduce((a, s) => a + s.delta, 0)
            const top = st.sessions.slice(0, 8).map(s => `${mk(s.name)} +${s.delta}`).join('、')
            statHtml = `✅ 已更新 ${st.since} ~ ${st.until}：<br><b>${st.sessions.length}</b> 个联系人新增 <b>${total}</b> 条消息<br>${top}` + (st.sessions.length > 8 ? ` …等 ${st.sessions.length} 人` : '')
          } else if (st && st.since) {
            statHtml = `✅ 已更新 ${st.since} ~ ${st.until}：无新消息`
          }
        } catch {}
        txt.innerHTML = statHtml
        closeBtn.style.display = 'inline-block'; closeBtn.textContent = '查看'
        setTimeout(() => location.reload(), 1500)
      } else if (p.step && p.step.indexOf('失败') === 0) {
        clearInterval(timer); txt.textContent = '❌ ' + p.step; closeBtn.style.display = 'inline-block'
        btn.disabled = false; btn.textContent = '🔄 刷新'
      }
    } catch {}
  }, 400)
});
render();
</script>
<!-- 刷新进度模态弹窗 -->
<div id="refreshModal" style="display:none;position:fixed;inset:0;background:rgba(17,24,39,.45);z-index:9999;align-items:center;justify-content:center">
  <div style="background:#fff;border-radius:14px;padding:24px 28px;width:420px;box-shadow:0 12px 48px rgba(0,0,0,.18)">
    <div style="font-size:16px;font-weight:700;color:#111827;margin-bottom:14px">🔄 正在刷新数据</div>
    <div style="height:8px;background:#E8EBEE;border-radius:4px;overflow:hidden;margin-bottom:10px">
      <div id="mProgBar" style="height:100%;width:0%;background:#07C160;border-radius:4px;transition:width .35s"></div>
    </div>
    <div id="mProgText" style="font-size:13px;color:#374151;line-height:1.7;min-height:20px">准备…</div>
    <div style="margin-top:16px;display:flex;justify-content:flex-end">
      <button id="mClose" class="btn" style="display:none">关闭</button>
    </div>
  </div>
</div>
</body>
</html>
"""

def main():
    rows = build_rows()
    initials = {r['name']: ''.join(p[0].upper() for p in lazy_pinyin(r['name'])) for r in rows}
    html = (HTML_TEMPLATE
        .replace('__GEN_TIME__', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
        .replace('__DATA_JSON__', json.dumps(rows, ensure_ascii=False))
        .replace('__INITIALS__', json.dumps(initials, ensure_ascii=False))
    )
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print('已生成:', OUT, os.path.getsize(OUT) // 1024, 'KB,', len(rows), '联系人')

if __name__ == '__main__':
    main()
