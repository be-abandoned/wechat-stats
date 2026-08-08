# -*- coding: utf-8 -*-
"""合并「数据看板.html」+「聊天频率排行.html」→「微信统计中心.html」（顶部页签切换两大功能页）。
后处理方式：读取两个生成器产出的 HTML，提取 CSS/body/JS，作用域化后拼装。
不改动原两个 HTML 与生成器。"""
import re, os

BASE = os.environ.get('OUTPUT_DIR') or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
DASH = os.environ.get('DASH_SRC') or os.path.join(BASE, 'dashboard.html')
RACE = os.environ.get('RACE_SRC') or os.path.join(BASE, 'race.html')
OUT  = os.path.join(BASE, 'combined.html')


def extract(html):
    css = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
    body = re.search(r'<body>(.*?)</body>', html, re.S).group(1)
    js = re.search(r'<script>(.*?)</script>', html, re.S).group(1)
    # script 在 body 内部：从 body 中剔除（js 单独提取，避免重复）
    body = re.sub(r'<script>.*?</script>', '', body, flags=re.S)
    return css, body, js


def split_top(sels):
    """顶层逗号拆分（忽略 () [] 内逗号）"""
    parts, dp, db, cur = [], 0, 0, ''
    for ch in sels:
        if ch == '(': dp += 1
        elif ch == ')': dp -= 1
        elif ch == '[': db += 1
        elif ch == ']': db -= 1
        if ch == ',' and dp == 0 and db == 0:
            parts.append(cur); cur = ''
        else:
            cur += ch
    if cur.strip(): parts.append(cur)
    return parts


def prefix_css(css, prefix):
    """给每条 CSS 规则的选择器加前缀；丢弃纯 * / body 规则（壳提供共享 reset/body）"""
    blocks, depth, cur = [], 0, ''
    for ch in css:
        cur += ch
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0: blocks.append(cur); cur = ''
    tail = cur.strip()
    out = []
    for blk in blocks:
        m = re.match(r'([^{}]*)\{(.*)\}\s*$', blk, re.S)
        if not m: continue
        sels, body_part = m.group(1).strip(), m.group(2).strip()
        if not sels: continue
        new = []
        for p in split_top(sels):
            s = p.strip()
            if not s: continue
            s = re.sub(r'/\*.*?\*/', '', s, flags=re.S).strip()   # 剥离选择器内注释
            if not s: continue
            if s in ('*', 'body'): continue
            new.append(f'{prefix}{s}')
        if new:
            out.append(f'{", ".join(new)} {{ {body_part} }}')
    if tail: out.append(tail)
    return '\n'.join(out)


def extract_nested_div(body, tag_id):
    """按 id 提取完整 div 块（处理嵌套 div），返回 (block, 剩余 body)"""
    m = re.search(rf'<div id="{tag_id}"[^>]*>', body)
    if not m: return '', body
    start = m.start()
    i = m.end(); depth = 1
    while i < len(body) and depth > 0:
        if body.startswith('<div', i): depth += 1; i += 4
        elif body.startswith('</div>', i): depth -= 1; i += 6
        else: i += 1
    return body[start:i], body[:start] + body[i:]


# ── 1. 读取与提取 ──
dash_css, dash_body, dash_js = extract(open(DASH, encoding='utf-8').read())
race_css, race_body, race_js = extract(open(RACE, encoding='utf-8').read())

# ── 2. 看板 body 处理：抽出 footer / refreshModal / 刷新按钮 ──
# footer
m_foot = re.search(r'<footer>.*?</footer>', dash_body, re.S)
dash_footer = m_foot.group(0) if m_foot else ''
if m_foot: dash_body = dash_body.replace(m_foot.group(0), '')
# refreshModal（提到壳层共享）
modal_html, dash_body = extract_nested_div(dash_body, 'refreshModal')
# 刷新按钮 + 提示（移入页签栏，保留原 id 使看板 JS 绑定不变）
m_btn = re.search(r'\s*<button id="refreshBtn"[^>]*>🔄 刷新</button>', dash_body)
m_hint = re.search(r'\s*<span id="refreshHint"[^>]*></span>', dash_body)
refresh_btn_html = m_btn.group(0).strip() if m_btn else '<button id="refreshBtn" class="btn">🔄 刷新</button>'
refresh_hint_html = m_hint.group(0).strip() if m_hint else '<span id="refreshHint"></span>'
dash_body = dash_body.replace(m_btn.group(0), '').replace(m_hint.group(0), '')

# ── 3. 排行 body/JS 手术 ──
race_body = race_body.replace('id="endBtn"', 'id="raceEndBtn"')          # id 冲突：跳到末尾按钮
race_js = race_js.replace("getElementById('endBtn')", "getElementById('raceEndBtn')")

# 排行动画暂停/恢复（页签切换用）
# frame 内递归：精确上下文替换
race_js = race_js.replace(
    "  draw(pos, dt);\n  syncRange();\n  requestAnimationFrame(frame);",
    "  draw(pos, dt);\n  syncRange();\n  rafId = requestAnimationFrame(frame);", 1)
# 注入 setActive（放在初始 rAF 前，所有变量已声明）；初始启动改为条件启动（整行精确匹配）
inject = (
    "let active = false, rafId = 0;\n"
    "function setActive(on) {\n"
    "  active = on;\n"
    "  if (on) { lastT = 0; resize(); draw(pos); syncRange(); rafId = requestAnimationFrame(frame); }\n"
    "  else { cancelAnimationFrame(rafId); rafId = 0; }\n"
    "}\n"
    "window.__raceSetActive = setActive;\n\n"
)
race_js = re.sub(r'^requestAnimationFrame\(frame\);$',
                 inject + 'if (active) rafId = requestAnimationFrame(frame);',
                 race_js, count=1, flags=re.M)
# keydown 门禁：排行页激活时才响应（看板搜索框空格不再被拦截）
race_js = race_js.replace(
    "document.addEventListener('keydown', e => {\n  if (e.code === 'Space')",
    "document.addEventListener('keydown', e => {\n  if (!active) return\n  if (e.code === 'Space')", 1)

# ── 4. CSS 作用域化 + JS IIFE ──
dash_css = prefix_css(dash_css, '.pg-dash ')
race_css = prefix_css(race_css, '.pg-race ')
dash_js = f'(function(){{\n{dash_js}\n}})();'
race_js = f'(function(){{\n{race_js}\n}})();'

# ── 5. 拼装壳 ──
shell_css = '''
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#F7F8FA; color:#1f2937; font-family:'Microsoft YaHei',-apple-system,sans-serif; padding:0; }
.pg-bar { display:flex; align-items:center; justify-content:space-between; background:#fff; border-bottom:1px solid #E5E7EB; padding:10px 28px; }
.pg-tabs { display:flex; gap:4px; }
.pg-tabs button { border:none; background:none; padding:8px 18px; font-size:15px; font-weight:600; color:#6b7280; cursor:pointer; border-bottom:2px solid transparent; font-family:inherit; }
.pg-tabs button.on { color:#07C160; border-bottom-color:#07C160; }
.pg-right { display:flex; align-items:center; gap:10px; }
.pg-right .btn { padding:8px 16px; font-size:14px; font-weight:600; color:#fff; border:none; border-radius:8px; cursor:pointer; font-family:inherit; }
.pg-right .btn:disabled { opacity:.6; cursor:default; }
#refreshHint { font-size:12px; color:#9ca3af; }
.content { padding:28px; }
footer { margin-top:16px; color:#9ca3af; font-size:12px; text-align:center; }
#refreshModal .btn { padding:8px 16px; font-size:14px; border:1px solid #E5E7EB; border-radius:8px; background:#fff; cursor:pointer; color:#374151; font-family:inherit; }
'''

shell_js = '''
(function(){
  var tabBtns = document.querySelectorAll('.pg-tabs button');
  function switchPg(pg){
    tabBtns.forEach(function(x){ x.classList.toggle('on', x.dataset.pg === pg); });
    document.getElementById('pg-dash').style.display = pg === 'dash' ? '' : 'none';
    document.getElementById('pg-race').style.display = pg === 'race' ? '' : 'none';
    if (window.__raceSetActive) window.__raceSetActive(pg === 'race');
  }
  tabBtns.forEach(function(b){ b.addEventListener('click', function(){ switchPg(b.dataset.pg); }); });
})();
'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>微信统计中心</title>
<style>
{shell_css}
/* ===== 数据看板（作用域 .pg-dash） ===== */
{dash_css}
/* ===== 聊天频率排行（作用域 .pg-race） ===== */
{race_css}
</style>
</head>
<body>
<div class="pg-bar">
  <div class="pg-tabs">
    <button data-pg="dash" class="on">统计看板</button>
    <button data-pg="race">聊天频率排行</button>
  </div>
  <div class="pg-right">
    {refresh_btn_html}
    {refresh_hint_html}
  </div>
</div>
<div class="content">
  <section id="pg-dash" class="pg-dash">
{dash_body}
  </section>
  <section id="pg-race" class="pg-race" style="display:none">
{race_body}
  </section>
</div>
{dash_footer}
{modal_html}
<script>
{dash_js}
</script>
<script>
{race_js}
</script>
<script>
{shell_js}
</script>
</body>
</html>'''

open(OUT, 'w', encoding='utf-8').write(html)
print(f'已生成: {OUT}  {os.path.getsize(OUT)//1024} KB')
