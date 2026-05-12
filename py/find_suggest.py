# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'e:\csi10\analyzer_v5_market.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("查找建议相关代码:")
for i, line in enumerate(lines, 1):
    if '建议' in line or '暂不' in line or '卖出' in line or '买入' in line:
        print(f"{i}: {line.rstrip()}")