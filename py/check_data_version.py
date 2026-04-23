# -*- coding: utf-8 -*-
"""检查数据版本和修复问题"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json

print("=" * 60)
print("数据版本检查")
print("=" * 60)

# 1. 检查result.json版本
try:
    data = json.load(open(r'e:\csi10\result.json', 'r'))
    version = data.get('version', 'unknown')
    print(f"\n当前数据版本: {version}")
    
    # 检查数据结构
    has_market = 'market' in data
    has_adjusted = any('adjusted_score' in s for s in data.get('stocks', []))
    
    print(f"market字段: {'✓存在' if has_market else '❌缺失'}")
    print(f"adjusted_score字段: {'✓存在' if has_adjusted else '❌缺失'}")
    
    # 显示股票示例
    sample = data.get('stocks', [])[:3]
    print(f"\n股票数据示例:")
    for s in sample:
        print(f"  {s['name']}: score={s.get('score')}, adjusted_score={s.get('adjusted_score', 'undefined')}")
    
except Exception as e:
    print(f"❌ 数据检查失败: {e}")

print("\n" + "=" * 60)
print("问题分析")
print("=" * 60)

print("""
问题1: 数据版本
  - 当前: v4.0 (无大盘调整)
  - 需要: v5.0 (有大盘调整)
  
问题2: adjusted_score显示undefined
  - 原因: v4版本没有生成adjusted_score字段
  - 解决: 运行v5版本生成新数据
""")

print("\n" + "=" * 60)
print("解决方案")
print("=" * 60)

print("""
正确流程:
  1. 运行v5分析引擎
  2. v5会生成adjusted_score字段
  3. 前端显示正确数据

推荐版本: v5.0 (大盘走势权重版)
  - 包含大盘调整因子
  - 包含动态阈值
  - 包含adjusted_score
""")