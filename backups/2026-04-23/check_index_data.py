# -*- coding: utf-8 -*-
import sqlite3
import os

db_path = r'E:\csi10\stocks.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查沪深300数据
    cursor.execute('SELECT code, name, date, close FROM stocks WHERE code = "sh000300" ORDER BY date DESC LIMIT 10')
    rows = cursor.fetchall()
    print('沪深300 (sh000300) 最近10条:')
    for row in rows:
        print(f'  {row[0]} {row[1]} {row[2]} close={row[3]}')
    
    # 检查所有指数
    cursor.execute('SELECT DISTINCT code, name FROM stocks WHERE code LIKE "sh%" AND (code LIKE "000%" OR code LIKE "9%")')
    indices = cursor.fetchall()
    print(f'\n上证指数列表: {len(indices)}')
    for idx in indices[:10]:
        print(f'  {idx[0]} {idx[1]}')
    
    # 检查深证指数
    cursor.execute('SELECT DISTINCT code, name FROM stocks WHERE code LIKE "sz%" AND (code LIKE "399%" OR code LIKE "001%")')
    indices2 = cursor.fetchall()
    print(f'\n深证指数列表: {len(indices2)}')
    for idx in indices2[:10]:
        print(f'  {idx[0]} {idx[1]}')
    
    conn.close()
else:
    print('数据库不存在')