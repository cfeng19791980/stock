# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import pandas as pd

conn = sqlite3.connect(r'E:\csi10\stocks.db')
df = pd.read_sql('SELECT * FROM daily_price LIMIT 1', conn)
print('Columns:', list(df.columns))
print('\nSample row:')
for col in df.columns:
    val = df.iloc[0][col]
    print(f'  {col}: {val}')

# 检查数据范围
cursor = conn.cursor()
cursor.execute("SELECT MIN(date), MAX(date), COUNT(*) FROM daily_price")
print('\nData stats:', cursor.fetchone())

conn.close()