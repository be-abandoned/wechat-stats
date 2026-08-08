# -*- coding: utf-8 -*-
"""HTML 生成桥接 —— 适配现有生成器到整合包输出目录"""

import os, sys, shutil, json, subprocess

PACK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN_SRC = os.path.join(PACK_DIR, 'scripts')  # 本地生成器副本
STATS_DIR = os.path.join(PACK_DIR, 'output', 'stats_data')
OUTPUT_DIR = os.path.join(PACK_DIR, 'output')
WXID_NAMES_SRC = os.path.join(GEN_SRC, 'wxid_names.json')

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
os.makedirs(OUTPUT_DIR, exist_ok=True)

TMP_GEN = os.path.join(PACK_DIR, 'output', '_gen_tmp')
# Skip rmtree due to sandbox restrictions — just overwrite
os.makedirs(TMP_GEN, exist_ok=True)

# Copy wxid_names
wxid_names_dst = os.path.join(TMP_GEN, 'wxid_names.json')
if os.path.exists(WXID_NAMES_SRC):
    shutil.copy(WXID_NAMES_SRC, wxid_names_dst)

# Build adapted scripts
for script in ['gen_dashboard_html.py', 'gen_race_html.py', 'gen_combined.py']:
    src = os.path.join(GEN_SRC, script)
    dst = os.path.join(TMP_GEN, script)
    content = open(src, encoding='utf-8').read()

    # Replace BASE = r'...'
    content = content.replace(
        "r'D:\\WorkBuddy\\微信聊天记录库-私聊'",
        "r'" + STATS_DIR + "'"
    )
    # Replace wxid_names path
    content = content.replace(
        "r'D:\\WorkBuddy\\.workbuddy\\wxid_names.json'",
        "r'" + wxid_names_dst + "'"
    )
    # Replace all os.path.join(BASE, ...) with English output paths
    content = content.replace(
        "os.path.join(BASE, '数据看板.html')",
        "r'" + os.path.join(OUTPUT_DIR, 'dashboard.html') + "'"
    )
    content = content.replace(
        "os.path.join(BASE, '聊天频率排行.html')",
        "r'" + os.path.join(OUTPUT_DIR, 'race.html') + "'"
    )
    content = content.replace(
        "os.path.join(BASE, '微信统计中心.html')",
        "r'" + os.path.join(OUTPUT_DIR, 'combined.html') + "'"
    )

    open(dst, 'w', encoding='utf-8').write(content)
    print(f'Adapted: {script}')

# Run generators
python = sys.executable

for i, (script, label) in enumerate([
    ('gen_dashboard_html.py', '数据看板'),
    ('gen_race_html.py', '排行动画'),
    ('gen_combined.py', '合并统计中心'),
], 1):
    print(f'[{i}/3] 生成{label}...')
    result = subprocess.run(
        [python, os.path.join(TMP_GEN, script)],
        cwd=TMP_GEN,
        capture_output=True, text=True,
        env={**os.environ,
             'OUTPUT_DIR': OUTPUT_DIR,
             'DASH_TMP': os.path.join(OUTPUT_DIR, 'dashboard.html'),
             'DASH_SRC': os.path.join(OUTPUT_DIR, 'dashboard.html'),
             'RACE_TMP': os.path.join(OUTPUT_DIR, 'race.html'),
             'RACE_SRC': os.path.join(OUTPUT_DIR, 'race.html'),
        }
    )
    if result.returncode != 0:
        print(f'  [ERROR] {label}生成失败:')
        print(f'  stdout: {result.stdout[-500:]}')
        print(f'  stderr: {result.stderr[-500:]}')
        sys.exit(1)
    print(f'  [OK] {label}')

# Skip cleanup (sandbox restriction)

# Verify
print('\n=== 验证输出 ===')
for f in ['dashboard.html', 'race.html', 'combined.html']:
    p = os.path.join(OUTPUT_DIR, f)
    if os.path.exists(p):
        print(f'  [OK] {f} ({os.path.getsize(p)/1024:.0f} KB)')
    else:
        print(f'  [MISSING] {f}')

print('\nHTML 生成完成！')
