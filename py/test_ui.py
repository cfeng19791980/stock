# -*- coding: utf-8 -*-
"""
Electron界面测试脚本
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os

JSON_FILE = r'e:\csi10\result.json'
INDEX_HTML = r'e:\csi10\index.html'
PRELOAD_JS = r'e:\csi10\preload.js'
MAIN_JS = r'e:\csi10\main_json.js'

print("=" * 60)
print("Electron界面测试")
print("=" * 60)

test_results = []

# UI001: 前端文件完整性
print("\n[UI001] 前端文件完整性测试:")
required_files = {
    'index.html': INDEX_HTML,
    'preload.js': PRELOAD_JS,
    'main_json.js': MAIN_JS,
    'result.json': JSON_FILE,
    'package.json': r'e:\csi10\package.json'
}

for name, path in required_files.items():
    if os.path.exists(path):
        print(f"  ✓ {name} 存在")
        test_results.append({'id': f'UI001-{name}', 'status': 'PASS'})
    else:
        print(f"  ✗ {name} 缺失")
        test_results.append({'id': f'UI001-{name}', 'status': 'FAIL'})

# UI002: package.json配置
print("\n[UI002] package.json配置测试:")
with open(r'e:\csi10\package.json', 'r', encoding='utf-8') as f:
    pkg = json.load(f)

if pkg['main'] == 'main_json.js':
    print("  ✓ main字段正确")
    test_results.append({'id': 'UI002-main', 'status': 'PASS'})
else:
    print(f"  ✗ main字段错误: {pkg['main']}")
    test_results.append({'id': 'UI002-main', 'status': 'FAIL'})

if pkg['version'] == '3.0.0':
    print("  ✓ version正确")
    test_results.append({'id': 'UI002-version', 'status': 'PASS'})
else:
    print(f"  ✗ version错误: {pkg['version']}")
    test_results.append({'id': 'UI002-version', 'status': 'FAIL'})

# UI003: preload.js IPC接口
print("\n[UI003] preload.js IPC接口测试:")
with open(PRELOAD_JS, 'r', encoding='utf-8') as f:
    preload_content = f.read()

required_apis = ['getAll', 'getBuy', 'getSell', 'refresh', 'getStatus']
for api in required_apis:
    if api in preload_content:
        print(f"  ✓ {api} 接口存在")
        test_results.append({'id': f'UI003-{api}', 'status': 'PASS'})
    else:
        print(f"  ✗ {api} 接口缺失")
        test_results.append({'id': f'UI003-{api}', 'status': 'FAIL'})

# UI004: main_json.js IPC handlers
print("\n[UI004] main_json.js IPC handlers测试:")
with open(MAIN_JS, 'r', encoding='utf-8') as f:
    main_content = f.read()

required_handlers = ['get-all-stocks', 'get-buy-stocks', 'get-sell-stocks', 'refresh-data', 'get-status']
for handler in required_handlers:
    if handler in main_content:
        print(f"  ✓ {handler} handler存在")
        test_results.append({'id': f'UI004-{handler}', 'status': 'PASS'})
    else:
        print(f"  ✗ {handler} handler缺失")
        test_results.append({'id': f'UI004-{handler}', 'status': 'FAIL'})

# UI005: index.html前端显示
print("\n[UI005] index.html前端显示测试:")
with open(INDEX_HTML, 'r', encoding='utf-8') as f:
    html_content = f.read()

required_sections = ['股票池', '买入', '卖出', '刷新']
for section in required_sections:
    if section in html_content:
        print(f"  ✓ {section} 显示区域存在")
        test_results.append({'id': f'UI005-{section}', 'status': 'PASS'})
    else:
        print(f"  ✗ {section} 显示区域缺失")
        test_results.append({'id': f'UI005-{section}', 'status': 'FAIL'})

# UI006: 买点卖点显示
print("\n[UI006] 买点卖点显示测试:")
buy_sell_keywords = ['buy_price', 'sell_price', '买点', '卖点']
found_keywords = []
for kw in buy_sell_keywords:
    if kw in html_content:
        found_keywords.append(kw)
        print(f"  ✓ {kw} 显示逻辑存在")

if len(found_keywords) >= 2:
    test_results.append({'id': 'UI006', 'status': 'PASS', 'note': str(found_keywords)})
else:
    test_results.append({'id': 'UI006', 'status': 'FAIL', 'note': '买点卖点显示缺失'})

# ============ 测试总结 ============
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
            print(f"  [{r['id']}] {r.get('note', '')}")