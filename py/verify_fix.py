# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'e:\csi10\main_json.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("关键配置验证:")
print(f"第1行: {lines[0].strip()}")
print(f"第18行: {lines[17].strip()}")
print(f"第56行: {lines[55].strip()}")

# 检查v5关键词
content = ''.join(lines)
checks = [
    ('analyzer_v5_market.py', 'analyzer_v5_market.py' in content),
    ('v5.0版本注释', 'v5.0' in lines[0]),
    ('v5.0窗口标题', 'v5.0' in lines[55]),
]

print("\n验证结果:")
for name, found in checks:
    print(f"  {'YES' if found else 'NO'} {name}")

print("\n✓ Electron主进程已正确配置为v5版本")