# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open(r'e:\csi10\result.json', 'r', encoding='utf-8'))

print("=" * 70)
print("修复后建议示例")
print("=" * 70)

stocks = data.get('stocks', [])
threshold = data['market']['threshold']

# 查看字段名
sample = stocks[0] if stocks else {}
print(f"数据字段: {list(sample.keys())}")

# 使用正确的字段名
suggest_field = 'suggest' if 'suggest' in sample else 'suggestion' if 'suggestion' in sample else 'recommendation'

print("\n【卖出建议】(评分<15)")
sell_stocks = [s for s in stocks if s.get('adjusted_score', s.get('score', 0)) < 15]
for s in sell_stocks[:3]:
    score = s.get('adjusted_score', s.get('score', 0))
    suggest = s.get(suggest_field, s.get('holding_advice', '无建议'))
    print(f"\n{s['name']} (评分{score}):")
    print(f"  {suggest[:150] if suggest else '无建议'}")

print("\n【观望建议】(评分15~threshold)")
hold_stocks = [s for s in stocks if 15 <= s.get('adjusted_score', s.get('score', 0)) < threshold]
for s in hold_stocks[:3]:
    score = s.get('adjusted_score', s.get('score', 0))
    suggest = s.get(suggest_field, s.get('holding_advice', '无建议'))
    print(f"\n{s['name']} (评分{score}):")
    print(f"  {suggest[:150] if suggest else '无建议'}")

print("\n【买入建议】(评分≥threshold)")
buy_stocks = [s for s in stocks if s.get('adjusted_score', s.get('score', 0)) >= threshold]
for s in buy_stocks[:3]:
    score = s.get('adjusted_score', s.get('score', 0))
    suggest = s.get(suggest_field, s.get('holding_advice', '无建议'))
    print(f"\n{s['name']} (评分{score}):")
    print(f"  {suggest[:150] if suggest else '无建议'}")

print("\n" + "=" * 70)
print("修复验证")
print("=" * 70)

print("""
修复后的逻辑:
  adjusted_score < 15  → ❌卖出
  15 ≤ adjusted_score < threshold → ⚠️观望
  adjusted_score ≥ threshold → ✅买入
""")