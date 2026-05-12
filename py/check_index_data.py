# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3

DB_PATH = r'E:\股票\csi500_data\stocks.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 60)
print("index_daily表检查（大盘指数数据）")
print("=" * 60)

# 1. 表结构
cursor.execute("PRAGMA table_info(index_daily)")
columns = cursor.fetchall()
print(f"\nindex_daily表字段:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# 2. 查看有哪些指数
cursor.execute("SELECT DISTINCT code FROM index_daily")
indices = cursor.fetchall()
print(f"\n可用指数代码:")
for idx in indices:
    print(f"  {idx[0]}")

# 3. 查看上证指数最近数据
cursor.execute("SELECT * FROM index_daily WHERE code='000001.SH' ORDER BY date DESC LIMIT 10")
sh_data = cursor.fetchall()
print(f"\n上证指数最近10天:")
if sh_data:
    for row in sh_data:
        print(f"  {row[0]} {row[1]} 收盘:{row[5]} 涨跌:{row[9]}%")
else:
    print("  ❌ 无数据")

# 4. 查看中证500最近数据
cursor.execute("SELECT * FROM index_daily WHERE code='000905.SH' ORDER BY date DESC LIMIT 10")
csi_data = cursor.fetchall()
print(f"\n中证500最近10天:")
if csi_data:
    for row in csi_data:
        print(f"  {row[0]} {row[1]} 收盘:{row[5]} 涨跌:{row[9]}%")
else:
    print("  ❌ 无数据")

conn.close()

print("\n" + "=" * 60)
print("大盘走势处理方案")
print("=" * 60)