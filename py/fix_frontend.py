# -*- coding: utf-8 -*-
"""修复前端容错"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'e:\csi10\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复displayMarket中的adjusted_score显示
old_code = '''                adjustEl.innerHTML = samples.map(s => {
                    const change = s.adjusted_score - s.score;'''

new_code = '''                adjustEl.innerHTML = samples.map(s => {
                    const adjScore = s.adjusted_score || s.score;  // 容错：无adjusted_score时用原score
                    const change = adjScore - s.score;'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✓ 容错逻辑已添加")
else:
    print("⚠️ 未找到目标代码")

# 写回
with open(r'e:\csi10\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ 前端已修复")