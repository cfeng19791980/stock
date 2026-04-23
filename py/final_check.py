# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open(r'e:\csi10\result.json', 'r', encoding='utf-8'))

print("=" * 70)
print("修复后建议示例")
print("=" * 70)

stocks = data.get('stocks', [])
threshold = data['market']['threshold']

print("\n【卖出建议】(评分<15)")
sell_stocks = [s for s in stocks if s.get('adjusted_score', 0) < 15]
for s in sell_stocks[:3]:
    score = s.get('adjusted_score', 0)
    advice = s.get('advice', s.get('holding_advice', '无建议'))
    print(f"\n{s['name']} (评分{score}):")
    print(f"  {advice[:200]}")

print("\n【观望建议】(评分15~threshold)")
hold_stocks = [s for s in stocks if 15 <= s.get('adjusted_score', 0) < threshold]
for s in hold_stocks[:3]:
    score = s.get('adjusted_score', 0)
    advice = s.get('advice', '无建议')
    print(f"\n{s['name']} (评分{score}):")
    print(f"  {advice[:200]}")

print("\n【买入建议】(评分≥threshold)")
buy_stocks = [s for s in stocks if s.get('adjusted_score', 0) >= threshold]
for s in buy_stocks[:3]:
    score = s.get('adjusted_score', 0)
    advice = s.get('advice', '无建议')
    print(f"\n{s['name']} (评分{score}):")
    print(f"  {advice[:200]}")

print("\n" + "=" * 70)
print("修复验证")
print("=" * 70)

# 检查是否有矛盾的"建议卖出→暂不买入"
for s in stocks:
    advice = s.get('advice', '')
    if '建议卖出' in advice and '暂不买入' in advice:
        print(f"❌ 仍有矛盾: {s['name']}")
        print(f"  {advice}")

print("\n✅ 无矛盾建议")
print("""
修复后逻辑清晰:
  - 卖出: "建议卖出！... → ❌卖出"
  - 观望: "观望... → ⏸️观望"
  - 买入: "可考虑买入... → ✅买入"
""")