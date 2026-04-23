# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'E:\csi10\stocks.db')
cursor = conn.cursor()

# 获取所有表名
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('所有表:')
for t in tables:
    print(f'  {t[0]}')
    cursor.execute(f"PRAGMA table_info({t[0]})")
    cols = cursor.fetchall()
    col_names = [c[1] for c in cols]
    print(f'    列: {col_names}')

conn.close()