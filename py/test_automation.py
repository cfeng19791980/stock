# -*- coding: utf-8 -*-
"""
自动化测试脚本 - 波段股票分析系统 v3.0
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
import time

JSON_FILE = r'e:\csi10\result.json'

print("=" * 60)
print("波段股票分析系统 v3.0 - 自动化测试")
print("=" * 60)

# 测试用例清单
test_results = []

def test_case(id, name, condition, expected, actual):
    # 修复判断逻辑
    if expected == "存在":
        status = "PASS" if actual else "FAIL"
    elif expected == "完整" or expected == "有效":
        status = "PASS" if actual == True else "FAIL"
    elif expected == "<100KB":
        # 文件大小判断
        actual_kb = float(actual.replace('KB', ''))
        status = "PASS" if actual_kb < 100 else "FAIL"
    else:
        status = "PASS" if actual == expected else "FAIL"
    
    test_results.append({
        'id': id,
        'name': name,
        'expected': expected,
        'actual': actual,
        'status': status
    })
    print(f"[{status}] {id}: {name} - 预期:{expected}, 实际:{actual}")

# F002: JSON文件存在
test_case("F002", "JSON文件生成", "文件存在", "存在", os.path.exists(JSON_FILE))

# 读取JSON
if os.path.exists(JSON_FILE):
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # F003: 股票数量
    test_case("F003", "股票数量", "stocks字段", 30, len(data.get('stocks', [])))
    
    # F004: 买入信号数量（设计保留前5只）
    test_case("F004", "买入信号", "buy字段（TOP5）", 5, len(data.get('buy', [])))
    
    # F005: 卖出信号数量
    test_case("F005", "卖出信号", "sell字段", 1, len(data.get('sell', [])))
    
    # F006: 买点卖点字段
    first_stock = data['stocks'][0] if data['stocks'] else {}
    has_buy_price = 'buy_price' in first_stock
    has_sell_price = 'sell_price' in first_stock
    test_case("F006", "买点字段", "buy_price存在", "存在", has_buy_price)
    test_case("F007", "卖点字段", "sell_price存在", "存在", has_sell_price)
    
    # F008: 股票名称
    has_chinese_name = any(s['name'] != s['code'] for s in data['stocks'])
    test_case("F008", "股票名称", "中文名称", "存在", has_chinese_name)
    
    # F009: 数据完整性（必填字段）
    required_fields = ['code', 'name', 'price', 'action', 'score', 'accuracy']
    all_fields_present = all(all(f in s for f in required_fields) for s in data['stocks'])
    test_case("F009", "数据完整性", "必填字段", "完整", all_fields_present)
    
    # F010: 数值范围验证
    valid_scores = all(0 <= s['score'] <= 100 for s in data['stocks'])
    test_case("F010", "分数范围", "0-100", "有效", valid_scores)
    
    # P002: 文件大小
    file_size = os.path.getsize(JSON_FILE)
    test_case("P002", "文件大小", "<100KB", "<100KB", f"{file_size/1024:.1f}KB")
    
    # 显示示例数据
    print("\n示例股票数据:")
    for s in data['stocks'][:3]:
        print(f"  {s['code']} {s['name']}: ¥{s['price']} ({s['action']})")
        if 'buy_price' in s:
            print(f"    买点: ¥{s['buy_price']:.2f} ({s['buy_change']:.1f}%)")
            print(f"    卖点: ¥{s['sell_price']:.2f} ({s['sell_change']:.1f}%)")

# 测试总结
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)
passed = sum(1 for r in test_results if r['status'] == 'PASS')
failed = sum(1 for r in test_results if r['status'] == 'FAIL')
print(f"总用例: {len(test_results)}")
print(f"通过: {passed}")
print(f"失败: {failed}")
print(f"通过率: {passed/len(test_results)*100:.1f}%")

if failed > 0:
    print("\n失败用例:")
    for r in test_results:
        if r['status'] == 'FAIL':
            print(f"  [{r['id']}] {r['name']}: 预期{r['expected']}, 实际{r['actual']}")