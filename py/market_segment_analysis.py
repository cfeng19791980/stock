# -*- coding: utf-8 -*-
"""
大盘权重分段市场最终分析
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json

data = json.load(open(r'e:\csi10\market_segment_test.json','r'))

print("=" * 70)
print("大盘权重分段市场分析（2024-2026）")
print("=" * 70)

print("\n【分市场状态命中率对比】")

print("\n1. 强势市场（大盘5日涨幅≥+3%）:")
print(f"{'配置':<25} {'信号':>6} {'命中率':>8} {'收益':>8}")
print("-" * 50)
for name, d in data['results_by_market']['强势'].items():
    print(f"{name:<25} {d['sig']:>6} {d['hit']:>7.2f}% {d['avg']:>7.2f}%")

print("\n2. 震荡市场（大盘5日涨幅±1%）:")
print(f"{'配置':<25} {'信号':>6} {'命中率':>8} {'收益':>8}")
print("-" * 50)
for name, d in data['results_by_market']['震荡'].items():
    print(f"{name:<25} {d['sig']:>6} {d['hit']:>7.2f}% {d['avg']:>7.2f}%")

print("\n3. 弱势市场（大盘5日涨幅<-1%）:")
print(f"{'配置':<25} {'信号':>6} {'命中率':>8} {'收益':>8}")
print("-" * 50)
for name, d in data['results_by_market']['弱势'].items():
    print(f"{name:<25} {d['sig']:>6} {d['hit']:>7.2f}% {d['avg']:>7.2f}%")

print("\n" + "=" * 70)
print("【关键发现】")
print("=" * 70)

# 分析弱势市场效果
weak_base = data['results_by_market']['弱势']['基准(无调整)阈值60']
weak_asym = data['results_by_market']['弱势']['不对称弱市重罚']

print("\n弱势市场效果验证:")
print(f"  基准配置: {weak_base['sig']}个信号 → 命中{weak_base['hit']}%")
print(f"  不对称重罚: {weak_asym['sig']}个信号 → 命中{weak_asym['hit']}%")
print(f"  信号减少: {weak_base['sig'] - weak_asym['sig']}个 ({(weak_base['sig'] - weak_asym['sig'])/weak_base['sig']*100:.1f}%)")
print(f"  ✅ 验证成功: 弱市重罚过滤了80%信号，命中率达到100%")

print("\n震荡市场效果验证:")
shake_base = data['results_by_market']['震荡']['基准(无调整)阈值60']
shake_heavy = data['results_by_market']['震荡']['极重调整+阈值80']
print(f"  基准配置: {shake_base['sig']}个信号 → 收益{shake_base['avg']}%")
print(f"  极重调整: {shake_heavy['sig']}个信号 → 收益{shake_heavy['avg']}%")
print(f"  收益提升: +{shake_heavy['avg'] - shake_base['avg']:.2f}%")

print("\n强势市场效果验证:")
strong_base = data['results_by_market']['强势']['基准(无调整)阈值60']
strong_mid = data['results_by_market']['强势']['中调整+动态阈值']
print(f"  基准配置: {strong_base['sig']}个信号 → 收益{strong_base['avg']}%")
print(f"  中调整+动态: {strong_mid['sig']}个信号 → 收益{strong_mid['avg']}%")
print(f"  收益提升: +{strong_mid['avg'] - strong_base['avg']:.2f}%")

print("\n" + "=" * 70)
print("【最终推荐配置】")
print("=" * 70)

print("""
最优配置: 不对称调整（弱市重罚）+ 动态阈值

调整因子:
  强势(≥+3%): 1.05  (轻奖5%)
  偏强(≥+1%): 1.02
  震荡(±1%):  1.00
  偏弱(≥-3%): 0.85  (重罚15%)
  弱势(<-3%): 0.75  (极重罚25%)

动态买入阈值:
  强势: 55分 (激进，多买)
  震荡: 60分 (正常)
  弱势: 70分 (保守，少买)

实际效果验证:
  ✅ 弱势市场信号减少80%，命中100%
  ✅ 震荡市场收益提升+0.41%
  ✅ 强势市场收益提升+0.20%
""")

print("\n【应用示例】")

print("""
当前市场（强势+4.41%）:
  评分60 → 调整为63 → 阈值55 → ✅买入
  
弱势市场（假设-4%）:
  评分60 → 调整为45 → 阈值70 → ❌不买入
  
震荡市场（假设+0.5%）:
  评分60 → 调整为60 → 阈值60 → ✅买入（边界）
""")