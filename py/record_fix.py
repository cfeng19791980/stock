# -*- coding: utf-8 -*-
"""
更新文档记录修复
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("卖出建议逻辑修复完成")
print("=" * 70)

print("\n【问题】")
print("""
用户发现: 卖出建议显示"暂不买入"，逻辑矛盾
  
原代码:
  if score < 15:
      base = "建议卖出！..."
  ...
  return base + " → ❌暂不买入"

导致: "建议卖出！评分14分 → ❌暂不买入"
""")

print("\n【修复】")
print("""
备份: analyzer_v5_market.py → py/analyzer_v5_market_backup_20260420.py
修改: generate_trade_advice函数逻辑

新逻辑:
  adjusted_score < 15  → "建议卖出！... → ❌卖出"
  15 ≤ adjusted_score < threshold → "观望... → ⏸️观望"
  adjusted_score ≥ threshold → "可考虑买入... → ✅买入"
""")

print("\n【验证】")
print("""
天奈科技(14分): "建议卖出！... → ❌卖出" ✓
生益科技(6分): "建议卖出！... → ❌卖出" ✓
铂力特(25分): "观望... → ⏸️观望" ✓
华通线缆(63分): "可考虑买入... → ✅买入" ✓

✅ 无矛盾建议
""")

print("\n【最佳实践】")
print("""
遵循用户建议:
  1. 备份原文件到py文件夹
  2. 在原文件内修改（保持文件名不变）
  3. main_json.js无需修改
  4. 降低维护成本
""")

print("\n✅ 修复完成，逻辑清晰")