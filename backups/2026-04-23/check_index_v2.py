# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'E:\csi10\stocks.db')
cursor = conn.cursor()

print('='*60)
print('指数数据检查 - 使用正确格式')
print('='*60)

# 使用实际的代码格式 sh.000300
print('\n[1] 沪深300 (sh.000300)')
cursor.execute("SELECT code, date, close, pct_chg FROM index_daily WHERE code='sh.000300' ORDER BY date DESC LIMIT 10")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f'  {row[0]} {row[1]} close={row[2]} pct={row[3]}%')
else:
    print('  无数据!')

print('\n[2] 上证指数 (sh.000001)')
cursor.execute("SELECT code, date, close, pct_chg FROM index_daily WHERE code='sh.000001' ORDER BY date DESC LIMIT 5")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f'  {row[0]} {row[1]} close={row[2]} pct={row[3]}%')

print('\n[3] 深证成指 (sz.399001)')
cursor.execute("SELECT code, date, close, pct_chg FROM index_daily WHERE code='sz.399001' ORDER BY date DESC LIMIT 5")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f'  {row[0]} {row[1]} close={row[2]} pct={row[3]}%')

# 对比最新沪深300真实数据 (2026-04-23)
print('\n[4] 对比验证')
print('  数据库最新沪深300收盘价: 见上方')
print('  真实数据请从东方财富/同花顺查询对比')

conn.close()