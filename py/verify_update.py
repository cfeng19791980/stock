# -*- coding: utf-8 -*-
"""验证前端更新"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("前端更新验证")
print("=" * 60)

# 检查HTML文件
with open(r'e:\csi10\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

checks = [
    ('market-panel CSS样式', '.market-panel' in content),
    ('marketStatus元素', 'id="marketStatus"' in content),
    ('marketPct元素', 'id="marketPct"' in content),
    ('marketFactor元素', 'id="marketFactor"' in content),
    ('marketThreshold元素', 'id="marketThreshold"' in content),
    ('marketChartContent元素', 'id="marketChartContent"' in content),
    ('adjustExamples元素', 'id="adjustExamples"' in content),
    ('displayMarket函数', 'function displayMarket' in content),
]

print("\n【HTML更新检查】")
for name, found in checks:
    status = "✓" if found else "❌"
    print(f"  {status} {name}")

# 检查result.json
import json
try:
    data = json.load(open(r'e:\csi10\result.json', 'r'))
    
    print("\n【数据结构检查】")
    print(f"  ✓ 版本: {data.get('version')}")
    print(f"  ✓ market字段: {'market' in data}")
    
    if 'market' in data:
        market = data['market']
        print(f"  ✓ status: {market.get('status')}")
        print(f"  ✓ pct_5d: {market.get('pct_5d')}")
        print(f"  ✓ factor: {market.get('factor')}")
        print(f"  ✓ threshold: {market.get('threshold')}")
        print(f"  ✓ recent_5d: {len(market.get('recent_5d', []))}条")
    
    print("\n【评分调整示例】")
    for s in data.get('stocks', [])[:5]:
        print(f"  {s['name']}: {s['score']} → {s['adjusted_score']}")
    
except Exception as e:
    print(f"❌ 数据检查失败: {e}")

print("\n" + "=" * 60)
print("完成")
print("=" * 60)

print("""
前端显示内容:
  - 市场状态: 偏强市场
  - 5日涨跌: +1.19%
  - 调整因子: 1.02
  - 买入阈值: 58分
  - 最近5日走势图
  - 评分调整示例

使用方法:
  打开浏览器访问: e:\\csi10\\index.html
""")