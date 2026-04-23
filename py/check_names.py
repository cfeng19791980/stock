# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import pandas as pd

DB_PATH = r'E:\股票\csi500_data\stocks.db'
conn = sqlite3.connect(DB_PATH)

# 检查daily_price表结构
print("daily_price表字段:")
columns = pd.read_sql("PRAGMA table_info(daily_price)", conn)
print(columns['name'].tolist())

# 检查是否有name字段
if 'name' in columns['name'].tolist():
    print("\nname字段存在，检查数据:")
    names = pd.read_sql("SELECT code, name FROM daily_price WHERE code='688028.SH' LIMIT 1", conn)
    print(names)
else:
    print("\nname字段不存在！")
    
conn.close()