# -*- coding: utf-8 -*-
"""
csi10 双版本调度 - 轻量级自动化
v4 = 生产 | v5 = 预备（后台自学习）
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("csi10 双版本调度配置")
print("=" * 60)

print("\n系统负担分析:")
print("| 任务           | 频率  | 负担 | 执行方式 |")
print("|----------------|-------|------|----------|")
print("| v4实时分析     | 每日  | 低   | 前台     |")
print("| 反馈记录       | 每日  | 低   | 前台     |")
print("| 反馈更新       | 每日  | 低   | 后台     |")
print("| v5增量训练     | 每周  | 中   | 后台夜间 |")
print("| v5完整训练     | 月度  | 高   | 后台周末 |")
print("| v5回测验证     | 每周  | 中   | 后台     |")

print("\n优化策略:")
print("  1. 异步执行 - v5训练不影响v4运行")
print("  2. 智能触发 - 只在需要时训练")
print("  3. 增量更新 - 不每次全量训练")
print("  4. 后台运行 - 夜间/周末自动执行")

print("\n内存/CPU预估:")
print("  v4运行: ~200MB, ~5%CPU")
print("  v5训练: ~500MB, ~20%CPU（后台）")
print("  总负担: 可控，不影响v4交易")

print("\nWindows任务计划配置:")
print("  每日09:00 - 运行v4分析")
print("  每日17:00 - 记录反馈")
print("  每周日02:00 - v5增量训练（后台）")
print("  每月1日02:00 - v5完整训练（后台）")

print("\n启动命令:")
print("  # 生产版本（每日）")
print("  python analyzer_v4.py")
print("")
print("  # 预备版本自学习（后台）")
print("  python dual_version_system.py")
print("")
print("  # Windows后台启动")
print("  start /B pythonw dual_version_system.py")

print("=" * 60)