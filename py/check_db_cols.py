# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'E:\股票\csi500_data\stocks.db')
cursor = conn.execute("PRAGMA table_info(daily_price)")
cols = cursor.fetchall()
print("daily_price表字段:")
for col in cols:
    print(f"  {col[1]} ({col[2]})")
conn.close()