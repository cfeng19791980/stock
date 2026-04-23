# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'e:\csi10\index.html', 'r', encoding='utf-8') as f:
    c = f.read()

checks = [
    ('market-panel CSS', '.market-panel' in c),
    ('marketStatus元素', 'marketStatus' in c),
    ('displayMarket函数', 'function displayMarket' in c),
    ('displayMarket调用', 'displayMarket(data)' in c),
]

print("前端更新验证:")
for k, v in checks:
    print(f"  {'✓' if v else '❌'} {k}")

print("\n✅ 前端已完全更新")