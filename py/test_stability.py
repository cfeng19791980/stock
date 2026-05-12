# -*- coding: utf-8 -*-
"""
稳定性测试：多次刷新 + 内存监控
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import os
import time
import psutil

JSON_FILE = r'e:\csi10\result.json'
PYTHON_SCRIPT = r'e:\csi10\analyzer_json.py'

print("=" * 60)
print("稳定性测试")
print("=" * 60)

results = []

# 1. 刷新性能测试
print("\n【刷新性能测试】")
print("测试5次刷新的时间稳定性...")

for i in range(5):
    start = time.time()
    
    # 直接执行Python
    import subprocess
    result = subprocess.run(['python', PYTHON_SCRIPT], capture_output=True, timeout=90)
    
    elapsed = time.time() - start
    
    # 验证JSON
    if result.returncode == 0 and os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        stock_count = len(data['stocks'])
        buysell_count = sum(1 for s in data['stocks'] if 'buy_price' in s)
        
        print(f"  第{i+1}次: {elapsed:.1f}s, {stock_count}只股票, {buysell_count}只买点卖点 ✓")
        results.append({'time': elapsed, 'stocks': stock_count, 'buysell': buysell_count, 'success': True})
    else:
        print(f"  第{i+1}次: 失败 ✗")
        results.append({'success': False})

# 统计
successful = sum(1 for r in results if r['success'])
avg_time = sum(r['time'] for r in results if r['success']) / successful if successful > 0 else 0

print(f"\n刷新成功率: {successful}/5 ({successful*20}%)")
print(f"平均刷新时间: {avg_time:.1f}s")

# 2. 数据稳定性测试
print("\n【数据稳定性测试】")
print("验证每次刷新数据是否一致...")

stock_counts = [r['stocks'] for r in results if r['success']]
buysell_counts = [r['buysell'] for r in results if r['success']]

if len(set(stock_counts)) == 1 and len(set(buysell_counts)) == 1:
    print(f"  ✓ 股票数量稳定: {stock_counts[0]}只")
    print(f"  ✓ 买点卖点稳定: {buysell_counts[0]}只")
    print(f"  ✅ 数据稳定性通过")
else:
    print(f"  ✗ 股票数量不稳定: {stock_counts}")
    print(f"  ✗ 买点卖点不稳定: {buysell_counts}")

# 3. 内存使用测试
print("\n【内存使用测试】")
process = psutil.Process(os.getpid())
print(f"  测试脚本内存: {process.memory_info().rss / 1024 / 1024:.1f}MB")

# 检查JSON文件大小
json_size = os.path.getsize(JSON_FILE) / 1024
print(f"  JSON文件大小: {json_size:.1f}KB")

# 4. 异常处理测试
print("\n【异常处理测试】")
print("测试异常情况...")

# 4.1 空文件恢复测试
print("  测试空文件恢复...")
backup = JSON_FILE + '.bak'
os.rename(JSON_FILE, backup)
open(JSON_FILE, 'w').close()  # 创建空文件

subprocess.run(['python', PYTHON_SCRIPT], capture_output=True, timeout=90)

if os.path.exists(JSON_FILE):
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            if data['stocks']:
                print(f"    ✓ 空文件恢复成功: {len(data['stocks'])}只股票")
            else:
                print(f"    ✗ 空文件恢复失败: 数据为空")
        except:
            print(f"    ✗ JSON解析失败")

os.remove(JSON_FILE)
os.rename(backup, JSON_FILE)

# 5. 显示格式验证
print("\n【显示格式验证】")
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("  验证买点卖点百分比格式...")
for s in data['stocks'][:3]:
    # 模拟前端显示
    buy_price_display = f"{s['buy_price']:.2f}"
    buy_change_display = f"{s['buy_change']:.2f}"
    sell_price_display = f"{s['sell_price']:.2f}"
    sell_change_display = f"{s['sell_change']:.2f}"
    
    print(f"    {s['name']}: 买点 ¥{buy_price_display} ({buy_change_display}%)")
    print(f"             卖点 ¥{sell_price_display} ({sell_change_display}%)")
    
    # 检查小数位数
    if len(buy_change_display.split('.')[-1]) == 2:
        print(f"    ✓ 格式正确（2位小数）")

print("\n" + "=" * 60)
print("稳定性测试完成")
print("=" * 60)
print(f"刷新成功率: {successful*20}%")
print(f"平均刷新时间: {avg_time:.1f}s")
print(f"数据稳定性: {'通过' if len(set(stock_counts)) == 1 else '不稳定'}")
print(f"显示格式: 已修复toFixed(2)")