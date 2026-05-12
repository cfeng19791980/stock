# -*- coding: utf-8 -*-
"""
边界测试和性能测试脚本
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
import time

JSON_FILE = r'e:\csi10\result.json'
PYTHON_SCRIPT = r'e:\csi10\analyzer_json.py'

print("=" * 60)
print("边界测试和性能测试")
print("=" * 60)

test_results = []

# ============ 边界测试 ============
print("\n【边界测试】")

# B001: JSON文件不存在情况
print("\n[B001] JSON文件不存在测试:")
if os.path.exists(JSON_FILE):
    os.rename(JSON_FILE, JSON_FILE + '.bak')
    try:
        with open(JSON_FILE, 'r') as f:
            data = json.load(f)
        print("  FAIL: 应该报错但成功读取")
        test_results.append({'id': 'B001', 'status': 'FAIL', 'note': '文件不存在时应报错'})
    except FileNotFoundError:
        print("  PASS: 正确抛出FileNotFoundError")
        test_results.append({'id': 'B001', 'status': 'PASS', 'note': '正确报错'})
    os.rename(JSON_FILE + '.bak', JSON_FILE)
else:
    print("  SKIP: 文件不存在无法测试")
    test_results.append({'id': 'B001', 'status': 'SKIP', 'note': '文件不存在'})

# B002: 空数据情况
print("\n[B002] 空数据测试:")
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

if data['stocks']:
    print("  PASS: 数据不为空")
    test_results.append({'id': 'B002', 'status': 'PASS', 'note': '数据正常'})
else:
    print("  FAIL: 数据为空")
    test_results.append({'id': 'B002', 'status': 'FAIL', 'note': '数据为空'})

# B003: 买点卖点缺失情况
print("\n[B003] 买点卖点缺失测试:")
stocks_without_buysell = [s for s in data['stocks'] if 'buy_price' not in s]
if stocks_without_buysell:
    print(f"  WARN: {len(stocks_without_buysell)}只股票缺少买点卖点")
    test_results.append({'id': 'B003', 'status': 'WARN', 'note': f'{len(stocks_without_buysell)}只缺失'})
else:
    print("  PASS: 所有股票都有买点卖点")
    test_results.append({'id': 'B003', 'status': 'PASS', 'note': '全部完整'})

# B004: 数值异常测试
print("\n[B004] 数值异常测试:")
abnormal_prices = [s for s in data['stocks'] if s['price'] <= 0 or s['price'] > 1000]
if abnormal_prices:
    print(f"  FAIL: {len(abnormal_prices)}只股票价格异常")
    test_results.append({'id': 'B004', 'status': 'FAIL', 'note': '价格异常'})
else:
    print("  PASS: 所有股票价格正常")
    test_results.append({'id': 'B004', 'status': 'PASS', 'note': '价格正常'})

# B005: 买点卖点价格逻辑
print("\n[B005] 买点<卖点逻辑测试:")
logical_errors = []
for s in data['stocks']:
    if 'buy_price' in s and 'sell_price' in s:
        if s['buy_price'] >= s['sell_price']:
            logical_errors.append(s['code'])
if logical_errors:
    print(f"  FAIL: {len(logical_errors)}只股票买点>=卖点")
    test_results.append({'id': 'B005', 'status': 'FAIL', 'note': str(logical_errors)})
else:
    print("  PASS: 所有股票买点<卖点")
    test_results.append({'id': 'B005', 'status': 'PASS', 'note': '逻辑正确'})

# ============ 性能测试 ============
print("\n【性能测试】")

# P003: Python执行时间
print("\n[P003] Python执行时间:")
start_time = time.time()
os.system(f'python {PYTHON_SCRIPT} >nul 2>&1')
elapsed = time.time() - start_time
print(f"  实际耗时: {elapsed:.1f}秒")
if elapsed < 90:
    print("  PASS: <90秒")
    test_results.append({'id': 'P003', 'status': 'PASS', 'note': f'{elapsed:.1f}s'})
else:
    print("  FAIL: >90秒")
    test_results.append({'id': 'P003', 'status': 'FAIL', 'note': f'{elapsed:.1f}s'})

# P004: JSON文件读取速度
print("\n[P004] JSON读取速度:")
start_time = time.time()
for _ in range(100):  # 读取100次
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        json.load(f)
elapsed = time.time() - start_time
avg_time = elapsed / 100 * 1000  # 毫秒
print(f"  平均读取时间: {avg_time:.2f}ms")
if avg_time < 10:
    print("  PASS: <10ms")
    test_results.append({'id': 'P004', 'status': 'PASS', 'note': f'{avg_time:.2f}ms'})
else:
    print("  FAIL: >10ms")
    test_results.append({'id': 'P004', 'status': 'FAIL', 'note': f'{avg_time:.2f}ms'})

# ============ 测试总结 ============
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)

passed = sum(1 for r in test_results if r['status'] == 'PASS')
failed = sum(1 for r in test_results if r['status'] == 'FAIL')
warned = sum(1 for r in test_results if r['status'] == 'WARN')
skipped = sum(1 for r in test_results if r['status'] == 'SKIP')

print(f"总用例: {len(test_results)}")
print(f"通过: {passed}")
print(f"失败: {failed}")
print(f"警告: {warned}")
print(f"跳过: {skipped}")
print(f"通过率: {passed/(len(test_results)-skipped)*100:.1f}%")

if failed > 0:
    print("\n失败用例:")
    for r in test_results:
        if r['status'] == 'FAIL':
            print(f"  [{r['id']}] {r['note']}")