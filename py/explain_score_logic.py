# -*- coding: utf-8 -*-
"""
评分逻辑详解
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open(r'e:\csi10\result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 70)
print("评分逻辑详解")
print("=" * 70)

print("\n【评分计算公式】")
print("  买入时: score = int(pred[1] * 100)")
print("  pred[1] = XGBoost预测的'未来3日涨幅>=3%'概率")
print("  ")
print("  举例:")
print("    pred[1] = 0.98 → score = 98（涨幅>=3%概率98%）")
print("    pred[1] = 0.95 → score = 95（涨幅>=3%概率95%）")
print("    pred[1] = 0.70 → score = 70（涨幅>=3%概率70%）")

print("\n【评分98分的含义】")
print("  评分98 = 未来3日涨幅>=3%的概率是98%")
print("  ")
print("  ⚠️ 重要区别:")
print("    - '上涨概率' ≠ '涨幅>=3%概率'")
print("    - 目标是rise_3d >= 0.03（涨幅>=3%）")
print("    - 不是简单的'上涨或下跌'")

print("\n【买入推荐逻辑】")
print("  条件: pred[1] > 0.6（涨幅>=3%概率>60%）")
print("  评分范围: 60-100")
print("  筛选: action == '买入' and score >= 60")

print("\n【当前数据验证】")

# 获取所有买入信号股票
buy_stocks = [s for s in data['stocks'] if s['action'] == '买入']
buy_stocks_sorted = sorted(buy_stocks, key=lambda s: -s['score'])

print(f"\n买入信号总数: {len(buy_stocks)}只")
print("\n评分分布:")
for s in buy_stocks_sorted[:10]:
    prob = s['score'] / 100.0  # pred[1] = score/100
    print(f"  {s['name']:12s} | 评分:{s['score']:3d} → 涨幅>=3%概率:{prob:.0%}")

print("\n【为什么买入推荐TOP 5不是评分最高？】")

# 对比股票池前10和买入推荐TOP 5
all_sorted = sorted(data['stocks'], key=lambda s: -s['score'] if s['action'] == '买入' else 0)

print("\n股票池前10（按评分降序）:")
for i, s in enumerate(all_sorted[:10], 1):
    print(f"  #{i} {s['name']:12s} | {s['action']:4s} | 评分:{s['score']:3d}")

print("\n买入推荐（JSON中的buy字段）:")
for i, s in enumerate(data['buy'], 1):
    print(f"  #{i} {s['name']:12s} | 评分:{s['score']:3d}")

print("\n【发现问题】")
if len(data['buy']) > 0:
    buy_max_score = max(s['score'] for s in data['buy'])
    pool_buy_max = max(s['score'] for s in buy_stocks)
    
    if buy_max_score != pool_buy_max:
        print(f"  ❌ 买入推荐最高评分: {buy_max_score}")
        print(f"  ❌ 股票池买入最高评分: {pool_buy_max}")
        print(f"  ❌ 问题: 买入推荐筛选逻辑有问题！")
    else:
        print(f"  ✅ 买入推荐最高评分: {buy_max_score}")
        print(f"  ✅ 与股票池买入最高评分一致")

print("\n" + "=" * 70)
print("评分逻辑说明完成")
print("=" * 70)