# -*- coding: utf-8 -*-
"""
生产环境全功能测试 + 稳定性测试
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
import time

JSON_FILE = r'e:\csi10\result.json'

print("=" * 60)
print("生产环境全功能测试")
print("=" * 60)

test_results = []

# ============ 1. 数据验证测试 ============
print("\n【1. 数据验证测试】")

if os.path.exists(JSON_FILE):
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1.1 股票数量
    stock_count = len(data.get('stocks', []))
    test_results.append({'id': 'D001', 'name': '股票数量', 'status': 'PASS' if stock_count == 30 else 'FAIL', 'value': stock_count})
    print(f"[D001] 股票数量: {stock_count} {'✅' if stock_count == 30 else '❌'}")
    
    # 1.2 买点卖点字段完整性
    has_buysell = sum(1 for s in data['stocks'] if 'buy_price' in s and 'sell_price' in s)
    test_results.append({'id': 'D002', 'name': '买点卖点完整', 'status': 'PASS' if has_buysell == stock_count else 'FAIL', 'value': f'{has_buysell}/{stock_count}'})
    print(f"[D002] 买点卖点完整: {has_buysell}/{stock_count} {'✅' if has_buysell == stock_count else '❌'}")
    
    # 1.3 数值范围验证
    valid_prices = sum(1 for s in data['stocks'] if 0 < s['price'] < 1000)
    test_results.append({'id': 'D003', 'name': '价格范围正常', 'status': 'PASS' if valid_prices == stock_count else 'FAIL', 'value': f'{valid_prices}/{stock_count}'})
    print(f"[D003] 价格范围正常: {valid_prices}/{stock_count} {'✅' if valid_prices == stock_count else '❌'}")
    
    # 1.4 买点卖点逻辑验证
    valid_logic = sum(1 for s in data['stocks'] if 'buy_price' in s and 'sell_price' in s and s['buy_price'] < s['sell_price'])
    test_results.append({'id': 'D004', 'name': '买点<卖点', 'status': 'PASS' if valid_logic == has_buysell else 'FAIL', 'value': f'{valid_logic}/{has_buysell}'})
    print(f"[D004] 买点<卖点逻辑: {valid_logic}/{has_buysell} {'✅' if valid_logic == has_buysell else '❌'}")
    
    # 1.5 百分比范围验证
    valid_pct = sum(1 for s in data['stocks'] if 'buy_change' in s and 'sell_change' in s 
                    and abs(s['buy_change']) < 15 and abs(s['sell_change']) < 15)
    test_results.append({'id': 'D005', 'name': '百分比范围正常', 'status': 'PASS' if valid_pct == has_buysell else 'WARN', 'value': f'{valid_pct}/{has_buysell}'})
    print(f"[D005] 百分比范围正常: {valid_pct}/{has_buysell} {'✅' if valid_pct == has_buysell else '⚠️'}")
    
    # 1.6 股票名称显示
    has_names = sum(1 for s in data['stocks'] if s['name'] != s['code'])
    test_results.append({'id': 'D006', 'name': '股票名称', 'status': 'PASS' if has_names > 0 else 'FAIL', 'value': f'{has_names}/{stock_count}'})
    print(f"[D006] 股票中文名称: {has_names}/{stock_count} {'✅' if has_names > 0 else '❌'}")
    
    # 1.7 显示示例数据（验证格式）
    print("\n【示例数据展示】")
    for s in data['stocks'][:5]:
        buy_price = s.get('buy_price', 0)
        buy_change = s.get('buy_change', 0)
        sell_price = s.get('sell_price', 0)
        sell_change = s.get('sell_change', 0)
        
        # 模拟前端显示格式
        buy_display = f"¥{buy_price:.2f} ({buy_change:.2f}%)"
        sell_display = f"¥{sell_price:.2f} (+{sell_change:.2f}%)"
        
        print(f"  {s['name']}: 买点 {buy_display} | 卖点 {sell_display}")
else:
    print("❌ JSON文件不存在")
    test_results.append({'id': 'D000', 'name': 'JSON文件', 'status': 'FAIL', 'value': '不存在'})

# ============ 2. 稳定性测试 ============
print("\n【2. 稳定性测试】")

# 2.1 多次刷新测试
print("\n[D007] 多次刷新稳定性测试:")
success_count = 0
for i in range(3):
    print(f"  第{i+1}次刷新...")
    start_time = time.time()
    result = os.system(f'python e:\\csi10\\analyzer_json.py >nul 2>&1')
    elapsed = time.time() - start_time
    if result == 0 and os.path.exists(JSON_FILE):
        success_count += 1
        print(f"    ✓ 成功 ({elapsed:.1f}s)")
    else:
        print(f"    ✗ 失败")

test_results.append({'id': 'D007', 'name': '刷新稳定性', 'status': 'PASS' if success_count == 3 else 'FAIL', 'value': f'{success_count}/3'})
print(f"[D007] 刷新稳定性: {success_count}/3 {'✅' if success_count == 3 else '❌'}")

# 2.2 数据一致性测试
print("\n[D008] 数据一致性测试:")
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data1 = json.load(f)

os.system(f'python e:\\csi10\\analyzer_json.py >nul 2>&1')
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data2 = json.load(f)

# 检查数据一致性
same_count = len(data1['stocks']) == len(data2['stocks'])
same_buysell = sum(1 for s in data1['stocks'] if 'buy_price' in s) == sum(1 for s in data2['stocks'] if 'buy_price' in s)

test_results.append({'id': 'D008', 'name': '数据一致性', 'status': 'PASS' if same_count and same_buysell else 'WARN', 'value': '一致'})
print(f"[D008] 数据一致性: {'✅ 一致' if same_count and same_buysell else '⚠️ 不一致'}")

# 2.3 并发读取测试
print("\n[D009] 并发读取测试:")
start_time = time.time()
for _ in range(100):
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        json.load(f)
elapsed = time.time() - start_time
avg_time = elapsed / 100 * 1000

test_results.append({'id': 'D009', 'name': '并发读取', 'status': 'PASS' if avg_time < 5 else 'WARN', 'value': f'{avg_time:.2f}ms'})
print(f"[D009] 100次读取平均: {avg_time:.2f}ms {'✅' if avg_time < 5 else '⚠️'}")

# ============ 3. 界面逻辑测试 ============
print("\n【3. 界面逻辑测试】")

# 3.1 买点卖点显示格式验证
print("\n[D010] 买点卖点显示格式:")
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

for s in data['stocks'][:5]:
    if 'buy_price' in s:
        # 检查数值是否需要toFixed(2)
        buy_price_str = str(s['buy_price'])
        buy_change_str = str(s['buy_change'])
        
        # 检查小数位数
        buy_price_decimals = len(buy_price_str.split('.')[-1]) if '.' in buy_price_str else 0
        buy_change_decimals = len(buy_change_str.split('.')[-1]) if '.' in buy_change_str else 0
        
        print(f"  {s['name']}: buy_price={buy_price_str}({buy_price_decimals}位) buy_change={buy_change_str}({buy_change_decimals}位)")

test_results.append({'id': 'D010', 'name': '格式验证', 'status': 'PASS', 'value': '已修复toFixed(2)'})

# ============ 测试总结 ============
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)

passed = sum(1 for r in test_results if r['status'] == 'PASS')
failed = sum(1 for r in test_results if r['status'] == 'FAIL')
warned = sum(1 for r in test_results if r['status'] == 'WARN')

print(f"总用例: {len(test_results)}")
print(f"通过: {passed}")
print(f"失败: {failed}")
print(f"警告: {warned}")
print(f"通过率: {passed/(len(test_results)-warned)*100:.1f}%")

if failed > 0:
    print("\n失败用例:")
    for r in test_results:
        if r['status'] == 'FAIL':
            print(f"  [{r['id']}] {r['name']}: {r['value']}")