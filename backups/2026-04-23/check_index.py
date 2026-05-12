# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'E:\csi10\stocks.db')
cursor = conn.cursor()

print('='*60)
print('指数数据检查')
print('='*60)

# 1. 检查沪深300数据
print('\n[1] 沪深300 (sh000300)')
cursor.execute("SELECT code, date, close, pct_chg FROM index_daily WHERE code='sh000300' ORDER BY date DESC LIMIT 10")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f'  {row[0]} {row[1]} close={row[2]} pct={row[3]}')
else:
    print('  无数据!')

# 2. 检查所有指数代码
print('\n[2] 所有指数代码')
cursor.execute("SELECT DISTINCT code FROM index_daily ORDER BY code")
codes = cursor.fetchall()
for code in codes:
    print(f'  {code[0]}')

# 3. 检查上证指数
print('\n[3] 上证指数 (sh000001)')
cursor.execute("SELECT code, date, close, pct_chg FROM index_daily WHERE code='sh000001' ORDER BY date DESC LIMIT 5")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f'  {row[0]} {row[1]} close={row[2]} pct={row[3]}')
else:
    print('  无数据!')

# 4. 检查深证成指
print('\n[4] 深证成指 (sz399001)')
cursor.execute("SELECT code, date, close, pct_chg FROM index_daily WHERE code='sz399001' ORDER BY date DESC LIMIT 5")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f'  {row[0]} {row[1]} close={row[2]} pct={row[3]}')
else:
    print('  无数据!')

conn.close()