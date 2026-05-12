# -*- coding: utf-8 -*-
"""
文件夹整理脚本
1. 创建py文件夹
2. 移动废弃脚本到py文件夹
3. 保留必要文件
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import shutil
from pathlib import Path

BASE_DIR = r'e:\csi10'
PY_DIR = r'e:\csi10\py'

print("=" * 70)
print("文件夹整理")
print("=" * 70)

# 创建py文件夹
os.makedirs(PY_DIR, exist_ok=True)
print(f"✓ 创建py文件夹: {PY_DIR}")

# 必要文件（保留在主目录）
KEEP_FILES = [
    'analyzer_json_v3.1.py',  # 当前分析引擎
    'data_fetcher.py',        # 数据更新脚本
    'stock_names.py',         # 股票名称映射
    'buysell_predictor_v5.py',# 买点卖点预测
    'data_check_and_update.py',# 数据完整性检查
]

# 移动文件列表
MOVE_FILES = [
    # 旧版本分析引擎
    'analyzer_json.py',
    'analyzer_json_full.py',
    'final_v2_clean.py',
    
    # 测试脚本
    'test_automation.py',
    'test_boundary.py',
    'test_buysell.py',
    'test_production.py',
    'test_stability.py',
    'test_ui.py',
    'test_*.py',
    
    # 检查脚本
    'check_date.py',
    'check_names.py',
    
    # 回测脚本
    'buysell_backtest.py',
    'buysell_backtest_v5.py',
    'price_range_backtest.py',
    
    # 预测器旧版本
    'buysell_ml_predictor.py',
    'price_range_predictor.py',
    
    # 辅助脚本
    'add_sorting.py',
    'buy_sell_logic_review.py',
    'explain_score_logic.py',
    'final_review_report.py',
    'project_review.py',
    'verify_sorting.py',
    'version_compare.py',
]

print("\n必要文件（保留在主目录）:")
for f in KEEP_FILES:
    print(f"  ✓ {f}")

print("\n移动文件到py文件夹:")
moved_count = 0
for filename in MOVE_FILES:
    # 处理通配符
    if '*' in filename:
        pattern = filename.replace('*', '')
        for f in os.listdir(BASE_DIR):
            if f.endswith('.py') and pattern in f and f not in KEEP_FILES:
                src = os.path.join(BASE_DIR, f)
                dst = os.path.join(PY_DIR, f)
                if os.path.exists(src):
                    shutil.move(src, dst)
                    print(f"  → {f}")
                    moved_count += 1
    else:
        src = os.path.join(BASE_DIR, filename)
        dst = os.path.join(PY_DIR, filename)
        if os.path.exists(src):
            shutil.move(src, dst)
            print(f"  → {filename}")
            moved_count += 1

print(f"\n✓ 移动了 {moved_count} 个文件到py文件夹")

# 检查主目录剩余文件
print("\n主目录剩余Python脚本:")
remaining = [f for f in os.listdir(BASE_DIR) if f.endswith('.py')]
for f in remaining:
    status = "✓ 保留" if f in KEEP_FILES else "⚠️ 未分类"
    print(f"  {status} {f}")

# 移动JS备份文件
js_backup = 'main_json_v3.1_backup.js'
if os.path.exists(os.path.join(BASE_DIR, js_backup)):
    shutil.move(os.path.join(BASE_DIR, js_backup), os.path.join(PY_DIR, js_backup))
    print(f"\n→ {js_backup}（JS备份）")

# 移动其他辅助文件
other_files = [
    'find_functions.ps1',
    'find_render_funcs.ps1',
]
for f in other_files:
    src = os.path.join(BASE_DIR, f)
    if os.path.exists(src):
        dst = os.path.join(PY_DIR, f)
        shutil.move(src, dst)
        print(f"  → {f}")

print("\n" + "=" * 70)
print("文件夹整理完成")
print("=" * 70)

print("\n主目录保留的必要文件:")
print("  - analyzer_json_v3.1.py（分析引擎）")
print("  - data_fetcher.py（数据更新）")
print("  - stock_names.py（股票名称）")
print("  - buysell_predictor_v5.py（买点卖点）")
print("  - data_check_and_update.py（数据检查）")
print("\npy文件夹存放:")
print("  - 旧版本脚本")
print("  - 测试脚本")
print("  - 回测脚本")
print("  - 辅助脚本")