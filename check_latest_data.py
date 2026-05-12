# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import pandas as pd

conn = sqlite3.connect(r'E:\csi10\stocks.db')

# 检查最新数据是否有完整指标
df = pd.read_sql("SELECT * FROM daily_price WHERE date >= '2026-01-01' ORDER BY date DESC LIMIT 5", conn)
print('Latest data (2026):')
for i, row in df.iterrows():
    print(f"\n{row['code']} {row['date']}:")
    print(f"  close: {row['close']}, pct_chg: {row['pct_chg']}")
    print(f"  ma5: {row['ma5']}, ma10: {row['ma10']}, ma20: {row['ma20']}")
    print(f"  rsi6: {row['rsi6']}, k: {row['k']}, d: {row['d']}")
    print(f"  macd: {row['macd']}, boll_upper: {row['boll_upper']}")

# 检查有完整指标的数据比例
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM daily_price WHERE ma5 IS NOT NULL AND rsi6 IS NOT NULL")
complete = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM daily_price")
total = cursor.fetchone()[0]
print(f"\n完整指标数据: {complete}/{total} ({complete/total*100:.1f}%)")

conn.close()