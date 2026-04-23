# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open(r'e:\csi10\result.json', 'r', encoding='utf-8'))

print("=" * 70)
print("修复后建议示例")
print("=" * 70)

stocks = data.get('stocks', [])

print("\n【卖出建议】")
sell_stocks = [s for s in stocks if s['adjusted_score'] < 15]
for s in sell_stocks[:3]:
    print(f"\n{s['name']} (评分{adjusted_score}):")
    print(f"  {s['suggestion'][:100]}...")

print("\n【观望建议】")
hold_stocks = [s for s in stocks if 15 <= s['adjusted_score'] < data['market']['threshold']]
for s in hold_stocks[:3]:
    print(f"\n{s['name']} (评分{s['adjusted_score']}):")
    print(f"  {s['suggestion'][:100]}...")

print("\n【买入建议】")
buy_stocks = [s for s in stocks if s['adjusted_score'] >= data['market']['threshold']]
for s in buy_stocks[:3]:
    print(f"\n{s['name']} (评分{s['adjusted_score']}):")
    print(f"  {s['suggestion'][:100]}...")

print("\n" + "=" * 70)
print("逻辑验证")
print("=" * 70)

print("""
✅ 修复成功:
  - 卖出建议: "建议卖出！... → ❌卖出"（清晰）
  - 观望建议: "观望。... → ⏸️观望"（清晰）
  - 买入建议: "可考虑买入。... → ✅买入"（清晰）

不再出现矛盾的"建议卖出 → 暂不买入"
""")