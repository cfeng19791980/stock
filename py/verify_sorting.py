# -*- coding: utf-8 -*-
"""
验证排序功能
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

# 加载result.json
with open(r'e:\csi10\result.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 70)
print("排序功能验证")
print("=" * 70)

# 1. 股票池排序验证
print("\n【股票池排序】（买入信号优先 → 评分降序）")
stocks = data['stocks']

# 模拟前端排序逻辑
def sort_stock_pool(stocks):
    return sorted(stocks, key=lambda s: (
        0 if s['action'] == '买入' else 1 if s['action'] == '卖出' else 2,
        -s['score']
    ))

sorted_pool = sort_stock_pool(stocks)
print("\n前10只股票排序结果:")
for i, s in enumerate(sorted_pool[:10], 1):
    print(f"  #{i} {s['name']:12s} | {s['action']:4s} | 评分:{s['score']:3d} | ¥{s['price']:.2f} ({s['change_pct']:+.2f}%)")

# 2. 买入推荐排序验证
print("\n【买入推荐排序】（按评分降序）")
buy_stocks = [s for s in stocks if s['action'] == '买入']
sorted_buy = sorted(buy_stocks, key=lambda s: -s['score'])
print(f"\n买入推荐 TOP 5（共{len(buy_stocks)}只）:")
for i, s in enumerate(sorted_buy[:5], 1):
    print(f"  #{i} {s['name']:12s} | 评分:{s['score']:3d} | 准确率:{s['accuracy']*100:.1f}% | ¥{s['price']:.2f}")

# 3. 卖出推荐排序验证
print("\n【卖出推荐排序】（按评分降序，跌幅置信度高的排前面）")
sell_stocks = [s for s in stocks if s['action'] == '卖出']
sorted_sell = sorted(sell_stocks, key=lambda s: -s['score'])
print(f"\n卖出推荐（共{len(sell_stocks)}只，按跌幅置信度排序）:")
for i, s in enumerate(sorted_sell, 1):
    print(f"  #{i} {s['name']:12s} | 评分:{s['score']:3d} | 跌幅置信度:{s['score']}% | ¥{s['price']:.2f} ({s['change_pct']:+.2f}%)")

print("\n" + "=" * 70)
print("排序验证完成！")
print("=" * 70)

print("\n✅ 排序规则:")
print("  1. 股票池: 买入信号优先 → 卖出信号 → 持有信号 → 按评分降序")
print("  2. 买入推荐: 评分降序（评分越高，买入置信度越高）")
print("  3. 卖出推荐: 评分降序（评分越高，跌幅置信度越高）")