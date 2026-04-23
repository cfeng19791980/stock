# -*- coding: utf-8 -*-
"""
修复卖出建议逻辑问题

问题:
  卖出建议显示: "建议卖出！评分仅14分... → ❌暂不买入"
  
原因:
  - 评分很低时base="建议卖出"
  - 但最后又加上" → ❌暂不买入"
  - 逻辑矛盾

正确逻辑:
  - 评分<15 → 建议卖出（不要再加"暂不买入"）
  - 评分15-59 → 暂不买入
  - 评分≥threshold → 建议买入
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("卖出建议逻辑修复")
print("=" * 70)

print("\n【问题分析】")

print("""
原代码逻辑:
  if score < 15:
      base = "建议卖出！评分仅{score}分"
  ...
  if adjusted_score >= threshold:
      return base + " → ✅建议买入"
  else:
      return base + " → ❌暂不买入"

问题:
  评分14分时显示: "建议卖出！... → ❌暂不买入"
  
  这是矛盾的！卖出建议不应该后面加"暂不买入"
""")

print("\n【修复方案】")

new_func = '''def generate_trade_advice(score, market_status, adjusted_score, threshold):
    """生成买卖建议（含大盘调整信息）"""
    
    # 大盘调整说明
    adjustment_info = f"\\n大盘调整: {score}→{adjusted_score} ({market_status}, 阈值{threshold}分)"
    
    # 根据调整后评分给出建议（逻辑清晰）
    if adjusted_score < 15:
        # 低评分：建议卖出
        return f"建议卖出！评分仅{adjusted_score}分，风险较高" + adjustment_info + " → ❌卖出"
    elif adjusted_score < threshold:
        # 中等评分：暂不买入
        if adjusted_score >= 40:
            return f"暂不买入。评分{adjusted_score}分，接近阈值{threshold}" + adjustment_info + " → ⚠️观望"
        elif adjusted_score >= 15:
            return f"观望。评分{adjusted_score}分，中性区间" + adjustment_info + " → ⏸️观望"
        else:
            return f"暂不买入。评分{adjusted_score}分" + adjustment_info + " → ❌观望"
    else:
        # 高评分：建议买入
        if adjusted_score >= 80:
            return f"强烈推荐买入！评分{adjusted_score}分" + adjustment_info + " → ✅买入"
        elif adjusted_score >= 70:
            return f"推荐买入。评分{adjusted_score}分" + adjustment_info + " → ✅买入"
        else:
            return f"可考虑买入。评分{adjusted_score}分，达标{threshold}" + adjustment_info + " → ✅买入"'''

print(new_func)

print("\n" + "=" * 70)
print("修复逻辑")
print("=" * 70)

print("""
修复后逻辑清晰:
  adjusted_score < 15  → ❌卖出（不再加"暂不买入"）
  15 ≤ adjusted_score < threshold → ⏸️观望/暂不买入
  adjusted_score ≥ threshold → ✅买入

示例:
  评分14 → "建议卖出！评分仅14分... → ❌卖出"
  评分25 → "观望。评分25分... → ⏸️观望"
  评分58 → "可考虑买入。评分58分... → ✅买入"
""")

print("\n是否执行修复？请确认")