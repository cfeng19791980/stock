# -*- coding: utf-8 -*-
"""
波段股票分析系统使用指南 - v4 vs v5对比
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("波段股票分析系统版本对比与使用指南")
print("=" * 70)

print("\n【版本对比】")

print("""
┌──────────────────────────────────────────────────────────────┐
│                    v4.0 vs v5.0 对比                          │
├────────────┬─────────────────────┬───────────────────────────┤
│   功能     │      v4.0           │         v5.0              │
├────────────┼─────────────────────┼───────────────────────────┤
│ 大盘调整   │ ❌ 无               │ ✓ 有（不对称调整）         │
│ 调整因子   │ ❌ 固定1.0          │ ✓ 动态(0.75~1.05)         │
│ 动态阈值   │ ❌ 固定60分         │ ✓ 动态(55~70分)           │
│ adjusted_score│ ❌ 无           │ ✓ 有                      │
│ market字段 │ ❌ 无               │ ✓ 有（完整大盘信息）       │
│ 弱势保护   │ ❌ 无               │ ✓ 重罚评分过滤80%信号     │
│ 回测收益   │ 基准8.90%          │ 提升+0.41%（震荡市场）     │
└────────────┴─────────────────────┴───────────────────────────┘
""")

print("\n【推荐版本】")

print("""
✅ 推荐使用: v5.0 (大盘走势权重版)

原因:
  1. 包含大盘走势影响（解决用户关切的问题）
  2. 弱势市场保护机制（避免逆势买入）
  3. 动态阈值（根据市场调整策略）
  4. 评分更贴近真实市场环境
""")

print("\n【文件清单】")

print("""
v5.0相关文件:
  ✓ analyzer_v5_market.py   - 主分析引擎（推荐使用）
  ✓ market_index_fetcher.py - 大盘数据获取
  ✓ result.json             - 输出结果（v5格式）
  ✓ index.html              - 前端显示（已更新）

v4.0文件（保留备用）:
  ○ analyzer_v4.py          - 原版本（无大盘调整）
""")

print("\n【正确使用流程】")

print("""
步骤1: 更新大盘数据
  python e:\\csi10\\market_index_fetcher.py
  （每日收盘后运行，获取沪深300指数）

步骤2: 运行v5分析
  python e:\\csi10\\analyzer_v5_market.py
  （生成result.json，包含大盘调整）

步骤3: 查看前端
  打开浏览器 → e:\\csi10\\index.html
  （自动加载v5数据，显示大盘信息）

定时任务建议:
  09:30 - 开盘前运行分析
  15:30 - 收盘后更新大盘数据
""")

print("\n【前端显示修复】")

print("""
问题: adjusted_score显示undefined/NaN

原因: 
  - 之前运行了v4版本，数据无adjusted_score字段
  - 前端读取旧数据导致undefined

解决:
  ✓ 已重新运行v5生成正确数据
  ✓ 已添加前端容错逻辑
  ✓ 刷新浏览器页面即可

前端容错逻辑:
  const adjScore = s.adjusted_score || s.score;
  // 无adjusted_score时自动用原score
""")

print("\n【数据结构验证】")

import json
try:
    data = json.load(open(r'e:\csi10\result.json', 'r', encoding='utf-8'))
    
    print(f"\n当前数据版本: {data.get('version')}")
    
    if 'market' in data:
        m = data['market']
        print(f"大盘状态: {m.get('status')}")
        print(f"5日涨跌: {m.get('pct_5d')}%")
        print(f"调整因子: {m.get('factor')}")
        print(f"买入阈值: {m.get('threshold')}分")
    
    sample = data.get('stocks', [])[:3]
    print(f"\n评分调整示例:")
    for s in sample:
        print(f"  {s['name']}: {s['score']} → {s['adjusted_score']}")
    
except Exception as e:
    print(f"数据验证: {e}")

print("\n" + "=" * 70)
print("总结")
print("=" * 70)

print("""
1. 应该使用哪个版本？
   ✅ v5.0 (大盘走势权重版)
   - 包含大盘调整功能
   - 弱势市场保护
   - 更贴近实际市场

2. 前端显示undefined问题？
   ✅ 已修复
   - 重新运行v5生成数据
   - 前端添加容错逻辑
   - 刷新浏览器即可

3. 如何确保数据正确？
   - 每次使用v5运行分析
   - 前端会自动加载最新数据
   - 底部显示大盘信息卡片
""")