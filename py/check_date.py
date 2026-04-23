# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

DB_PATH = r'E:\股票\csi500_data\stocks.db'
conn = sqlite3.connect(DB_PATH)

# 检查最新数据日期
print("=" * 60)
print("数据库最新数据日期检查")
print("=" * 60)

# 检查daily_price表的最新日期
query = """
SELECT code, MAX(date) as latest_date 
FROM daily_price 
WHERE code IN ('688028.SH', '688233.SH', '002384.SZ', '603986.SH')
GROUP BY code
"""

result = conn.execute(query).fetchall()

print("\n示例股票最新日期:")
for row in result:
    print(f"  {row[0]}: {row[1]}")

# 检查整体最新日期
query2 = "SELECT MAX(date) as max_date FROM daily_price"
max_date = conn.execute(query2).fetchone()[0]
print(f"\n数据库整体最新日期: {max_date}")

# 检查最近5天的数据量
query3 = """
SELECT date, COUNT(*) as count 
FROM daily_price 
WHERE date >= '2026-01-20'
GROUP BY date 
ORDER BY date DESC
LIMIT 10
"""
recent_data = conn.execute(query3).fetchall()

print("\n最近10天数据量:")
for row in recent_data:
    print(f"  {row[0]}: {row[1]}条")

conn.close()