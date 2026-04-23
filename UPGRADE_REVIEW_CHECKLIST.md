# -*- coding: utf-8 -*-
"""
升级后Review检查清单 - 强制执行流程
Priority: P0（立即改进）
Created: 2026-04-23 12:55
Lesson: 升级或修复后必须进行整体review
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import sqlite3
from pathlib import Path

# ============================================================
# 升级后Review检查清单（6阶段）
# ============================================================

print("="*70)
print("升级后Review检查清单")
print("执行时机: 每次 upgrade/fix 后立即运行")
print("="*70)

CSI10_DIR = Path('E:/csi10')
DB_PATH = CSI10_DIR / 'stocks.db'
RESULT_JSON = CSI10_DIR / 'result.json'
INDEX_HTML = CSI10_DIR / 'index.html'
ANALYZER_PY = CSI10_DIR / 'analyzer_v4.py'

review_passed = True

# ============================================================
# Phase 1: 后端输出字段完整性
# ============================================================
print("\n[Phase 1: 后端输出字段完整性]")
print("-"*70)

required_backend_fields = [
    'status', 'pct_5d', 'factor', 'buy_threshold',
    'sell_threshold', 'stop_profit', 'stop_loss', 'suggest_position',
    'indices'
]

try:
    with open(ANALYZER_PY, 'r', encoding='utf-8') as f:
        analyzer_content = f.read()

    missing_fields = []
    for field in required_backend_fields:
        if f"'{field}'" not in analyzer_content and f'"{field}"' not in analyzer_content:
            missing_fields.append(field)

    if missing_fields:
        print(f"✗ FAIL: analyzer_v4.py缺少字段: {missing_fields}")
        review_passed = False
    else:
        print(f"✓ PASS: analyzer_v4.py输出字段完整（{len(required_backend_fields)}个）")
except Exception as e:
    print(f"✗ FAIL: 无法读取analyzer_v4.py: {e}")
    review_passed = False

# ============================================================
# Phase 2: 前端元素ID完整性
# ============================================================
print("\n[Phase 2: 前端元素ID完整性]")
print("-"*70)

required_frontend_ids = [
    'marketStatus', 'marketPct', 'marketFactor', 'marketThreshold',
    'sellThreshold', 'stopProfit', 'stopLoss', 'suggestPosition',
    'hs300Pct', 'zz500Pct', 'divergence', 'hs300Latest', 'zz500Latest', 'dominant'
]

try:
    with open(INDEX_HTML, 'r', encoding='utf-8') as f:
        html_content = f.read()

    missing_ids = []
    for id in required_frontend_ids:
        if f"id='{id}'" not in html_content and f'id="{id}"' not in html_content:
            missing_ids.append(id)

    if missing_ids:
        print(f"✗ FAIL: index.html缺少元素ID: {missing_ids}")
        review_passed = False
    else:
        print(f"✓ PASS: index.html元素ID完整（{len(required_frontend_ids)}个）")
except Exception as e:
    print(f"✗ FAIL: 无法读取index.html: {e}")
    review_passed = False

# ============================================================
# Phase 3: 前端逻辑字段读取
# ============================================================
print("\n[Phase 3: 前端逻辑字段读取]")
print("-"*70)

required_js_reads = [
    ('sellThreshold', "getElementById('sellThreshold')"),
    ('stopProfit', "getElementById('stopProfit')"),
    ('stopLoss', "getElementById('stopLoss')"),
    ('suggestPosition', "getElementById('suggestPosition')"),
    ('hs300Pct', "getElementById('hs300Pct')"),
    ('zz500Pct', "getElementById('zz500Pct')"),
    ('divergence', "getElementById('divergence')"),
]

try:
    missing_reads = []
    for field_name, js_code in required_js_reads:
        if js_code not in html_content:
            missing_reads.append(field_name)

    if missing_reads:
        print(f"✗ FAIL: displayMarket函数缺少读取: {missing_reads}")
        review_passed = False
    else:
        print(f"✓ PASS: displayMarket函数字段读取完整（{len(required_js_reads)}个）")
except Exception as e:
    print(f"✗ FAIL: 检查失败: {e}")
    review_passed = False

# ============================================================
# Phase 4: 数据实际值验证
# ============================================================
print("\n[Phase 4: 数据实际值验证]")
print("-"*70)

try:
    data = json.load(open(RESULT_JSON, 'r', encoding='utf-8'))
    market = data.get('market', {})

    # 检查market字段
    for field in ['sell_threshold', 'stop_profit', 'stop_loss', 'suggest_position']:
        value = market.get(field)
        if value is None or value == 0:
            print(f"⚠ WARNING: market.{field} = {value} (可能缺失)")
        else:
            print(f"✓ PASS: market.{field} = {value}")

    # 检查indices字段
    indices = market.get('indices', {})
    for field in ['hs300', 'zz500', 'composite', 'divergence', 'dominant']:
        value = indices.get(field)
        if value:
            print(f"✓ PASS: indices.{field} 存在")
        else:
            print(f"✗ FAIL: indices.{field} 缺失")
            review_passed = False

except Exception as e:
    print(f"✗ FAIL: 无法读取result.json: {e}")
    review_passed = False

# ============================================================
# Phase 5: 数据库数据源完整性
# ============================================================
print("\n[Phase 5: 数据库数据源完整性]")
print("-"*70)

try:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 检查沪深300
    cursor.execute("SELECT COUNT(*) FROM index_daily WHERE code='sh.000300'")
    hs300_count = cursor.fetchone()[0]
    if hs300_count > 0:
        print(f"✓ PASS: 沪深300数据存在（{hs300_count}条）")
    else:
        print(f"✗ FAIL: 沪深300数据缺失")
        review_passed = False

    # 检查中证500
    cursor.execute("SELECT COUNT(*) FROM index_daily WHERE code='sh.000905'")
    zz500_count = cursor.fetchone()[0]
    if zz500_count > 0:
        print(f"✓ PASS: 中证500数据存在（{zz500_count}条）")
    else:
        print(f"✗ FAIL: 中证500数据缺失")
        review_passed = False

    conn.close()
except Exception as e:
    print(f"✗ FAIL: 数据库检查失败: {e}")
    review_passed = False

# ============================================================
# Phase 6: 前端显示测试
# ============================================================
print("\n[Phase 6: 前端显示测试]")
print("-"*70)
print("请手动验证:")
print("1. 刷新浏览器页面")
print("2. 检查'大盘走势信息模块'是否显示8个卡片")
print("3. 检查'多指数对比面板'是否显示沪深300+中证500数据")
print("4. 点击'立即更新'按钮，等待10秒")
print("5. 确认数据自动更新")
print("-"*70)

# ============================================================
# Review结果
# ============================================================
print("\n" + "="*70)
print("Review结果汇总")
print("="*70)

if review_passed:
    print("✓ 全部检查通过")
    print("✓ 系统级Review完成")
    print("✓ 可以结束本次Session")
else:
    print("✗ 存在失败项，需要立即修复")
    print("✗ 不能结束Session，必须修复后再Review")
    print("="*70)
    print("修复优先级: P0")
    print("修复要求: 立即修复，重新运行此Review脚本")
    print("="*70)

print("\n强制执行要求:")
print("⚠️ 每次 upgrade/fix 后必须运行此脚本")
print("⚠️ 所有检查通过后才能结束Session")
print("⚠️ 发现问题立即修复，不能遗留")
print("="*70)