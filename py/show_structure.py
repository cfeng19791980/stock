# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

base = r'e:\csi10'

# 删除临时脚本
tmp = os.path.join(base, 'move_files.py')
if os.path.exists(tmp):
    os.remove(tmp)
    print('Deleted: move_files.py')

print("=" * 70)
print("最终文件结构")
print("=" * 70)

print("\n根目录 (核心文件):")
for f in sorted(os.listdir(base)):
    if os.path.isfile(os.path.join(base, f)):
        size = os.path.getsize(os.path.join(base, f))
        print(f"  {f:<35} {size:>8} bytes")

print("\n" + "=" * 70)
print("核心文件确认")
print("=" * 70)

core = [
    'analyzer_v5_market.py',
    'analyzer_v4.py',
    'data_fetcher.py',
    'market_index_fetcher.py',
    'index.html',
    'result.json',
    'holdings.json',
    '波段股票Top30.csv',
]

for name in core:
    path = os.path.join(base, name)
    exists = os.path.exists(path)
    print(f"  {'YES' if exists else 'NO'} {name}")

print("\n" + "=" * 70)
print("Electron运行环境")
print("=" * 70)

print("""
架构: Electron → Python → result.json → 前端

核心脚本 (必须保持正确):
  analyzer_v5_market.py    - v5.0大盘权重版
  data_fetcher.py          - 数据获取
  market_index_fetcher.py  - 大盘数据

前端文件:
  index.html               - Electron渲染界面

数据库:
  E:\\股票\\csi500_data\\stocks.db

输出:
  result.json              - v5格式（含market字段）

规则:
  1. 核心脚本永远放在根目录
  2. 测试脚本放入py文件夹
  3. 更新后必须测试Electron完整流程
""")