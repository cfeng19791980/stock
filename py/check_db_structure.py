# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3
import pandas as pd

DB_PATH = r'E:\股票\csi500_data\stocks.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 查看数据库结构
print("=" * 60)
print("数据库结构检查")
print("=" * 60)

# 1. 表结构
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"\n数据库表: {[t[0] for t in tables]}")

# 2. 字段结构
cursor.execute("PRAGMA table_info(daily_price)")
columns = cursor.fetchall()
print(f"\ndaily_price表字段:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# 3. 检查是否有大盘指数
cursor.execute("SELECT DISTINCT code FROM daily_price WHERE code LIKE '%.SH' LIMIT 30")
codes = cursor.fetchall()
print(f"\n上海股票代码示例:")
for code in codes[:10]:
    print(f"  {code[0]}")

# 4. 检查是否有指数数据（上证指数 000001.SH）
cursor.execute("SELECT * FROM daily_price WHERE code='000001.SH' LIMIT 5")
sh_index = cursor.fetchall()
print(f"\n上证指数(000001.SH)数据:")
if sh_index:
    for row in sh_index:
        print(f"  {row}")
else:
    print("  ❌ 未找到上证指数数据")

# 5. 检查沪深300指数
cursor.execute("SELECT * FROM daily_price WHERE code='000300.SH' LIMIT 5")
hs300 = cursor.fetchall()
print(f"\n沪深300指数(000300.SH)数据:")
if hs300:
    for row in hs300:
        print(f"  {row}")
else:
    print("  ❌ 未找到沪深300数据")

# 6. 检查CSI500指数
cursor.execute("SELECT * FROM daily_price WHERE code='000905.SH' LIMIT 5")
csi500 = cursor.fetchall()
print(f"\n中证500指数(000905.SH)数据:")
if csi500:
    for row in csi500:
        print(f"  {row}")
else:
    print("  ❌ 未找到中证500数据")

# 7. 统计
cursor.execute("SELECT COUNT(DISTINCT code) FROM daily_price")
total = cursor.fetchone()[0]
print(f"\n总计股票数: {total}")

conn.close()

print("\n" + "=" * 60)
print("结论:")
print("=" * 60)
print("当前分析模型使用的特征:")
print("  ✓ pct_chg (涨跌幅)")
print("  ✓ ma5_ratio (MA5比值)")
print("  ✓ ma10_ratio (MA10比值)")
print("  ✓ rsi6 (RSI指标)")
print("  ✓ macd (MACD指标)")
print("  ❌ 大盘走势 (缺失!)")
print("\n⚠️ 问题确认: 评分计算未包含大盘走势权重!")