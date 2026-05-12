# -*- coding: utf-8 -*-
"""整理csi10文件夹"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import shutil

base = r'e:\csi10'
py_dir = os.path.join(base, 'py')

# 创建py文件夹
if not os.path.exists(py_dir):
    os.makedirs(py_dir)
    print(f"✓ 创建文件夹: {py_dir}")

print("=" * 60)
print("文件整理")
print("=" * 60)

# 核心文件（保留在根目录）
core_files = [
    'analyzer_v5_market.py',   # 主分析引擎v5（核心）
    'analyzer_v4.py',          # v4备用版本
    'data_fetcher.py',         # 数据获取模块
    'market_index_fetcher.py', # 大盘数据获取
    'result.json',             # 分析结果
    'holdings.json',           # 持仓数据
    'index.html',              # 前端页面
    '波段股票Top30.csv',       # 股票池
]

# 测试/调试文件（移入py文件夹）
test_files = [
    'market_backtest.py',
    'quick_backtest.py',
    'full_backtest.py',
    'market_segment_test.py',
    'check_db_structure.py',
    'check_index_data.py',
    'market_adjustment.py',
    'market_segment_analysis.py',
    'final_analysis_report.py',
    'verify_v5_data.py',
    'check_data_version.py',
    'verify_update.py',
    'update_index_html.py',
    'add_displayMarket.py',
    'fix_frontend.py',
    'fix_index_table.py',
    'check_html.py',
]

# 辅助脚本（移入py文件夹）
helper_files = [
    'backtest_simulation.py',
    'backtest_real.py',
    'analyzer_json_v3.1.py',
    'analyzer_json_v3.2.py',
    'analyzer_v4.py.bak',
    'threshold_analysis.py',
    'param_optimizer.py',
    'generate_full_report.py',
    'generate_summary_report.py',
]

# 移动文件
moved_count = 0
for f in test_files + helper_files:
    src = os.path.join(base, f)
    dst = os.path.join(py_dir, f)
    
    if os.path.exists(src):
        shutil.move(src, dst)
        moved_count += 1
        print(f"  ✓ 移动: {f} → py/")
    else:
        print(f"  - 未找到: {f}")

print(f"\n共移动 {moved_count} 个文件")

# 列出根目录剩余文件
print("\n" + "=" * 60)
print("根目录文件（核心文件）")
print("=" * 60)

for f in os.listdir(base):
    if os.path.isfile(os.path.join(base, f)):
        marker = "★" if f in core_files else " "
        print(f"{marker} {f}")

print("\n" + "=" * 60)
print("py文件夹内容")
print("=" * 60)

for f in os.listdir(py_dir):
    print(f"  {f}")

print("\n" + "=" * 60)
print("Electron运行环境注意事项")
print("=" * 60)

print("""
⚠️ 重要提醒:
  1. 主程序运行在Electron环境
  2. Python脚本由Electron调用执行
  3. 必须确保调用的脚本版本正确

核心文件位置（Electron调用）:
  ✓ analyzer_v5_market.py - 主分析引擎
  ✓ data_fetcher.py - 数据获取
  ✓ market_index_fetcher.py - 大盘数据

Electron调用流程:
  index.html → Electron → Python脚本 → result.json

必须保证:
  1. analyzer_v5_market.py是最新版本
  2. 所有依赖模块在正确位置
  3. 数据库路径正确（E:\\股票\\csi500_data\\stocks.db）
""")