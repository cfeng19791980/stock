# -*- coding: utf-8 -*-
"""
沪深300历史数据对比 - 找出问题
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
from datetime import datetime, timedelta

print('='*60)
print('沪深300历史数据对比')
print('='*60)

# 数据库数据
conn = sqlite3.connect(r'E:\csi10\stocks.db')
cursor = conn.cursor()
cursor.execute("SELECT date, close, pct_chg FROM index_daily WHERE code='sh.000300' ORDER BY date DESC LIMIT 10")
db_data = cursor.fetchall()
conn.close()

print('\n[数据库数据 - 最近10天]')
for row in db_data:
    print(f'  {row[0]} close={row[1]:.2f} pct={row[2]:.2f}%')

# 计算数据库中的累计涨跌
print('\n[数据库涨跌计算]')
if len(db_data) >= 2:
    db_today_close = db_data[0][1]  # 最新
    db_yesterday_close = db_data[1][1]  # 昨天
    db_calc_pct = (db_today_close - db_yesterday_close) / db_yesterday_close * 100
    print(f'  今日收盘: {db_today_close:.2f}')
    print(f'  昨日收盘: {db_yesterday_close:.2f}')
    print(f'  计算涨跌幅: {db_calc_pct:.2f}%')
    print(f'  数据库涨跌幅: {db_data[0][2]:.2f}%')
    
    if abs(db_calc_pct - db_data[0][2]) > 0.5:
        print(f'  ❌ 涨跌幅不一致!')

# 腾讯数据显示昨收是4799.63
print('\n[问题分析]')
print('  腾讯API显示:')
print('    昨收(昨日收盘价): 4799.63')
print('    当前价: 4761.57')
print('    涨跌幅: -0.79%')
print('')
print('  数据库显示:')
print('    2026-04-23 close=4799.63 pct=0.66%')
print('    2026-04-22 close=4782.18 pct=0.30%')
print('')
print('  ❌ 错误分析:')
print('    1. 4799.63是昨日收盘价,被错误标记为今日数据')
print('    2. 数据库涨跌幅计算错误(+0.66%实际应为-0.79%)')
print('    3. 数据日期可能整体错位了')

# 检查连续性问题
print('\n[连续性检查]')
prev_close = None
for i, row in enumerate(db_data):
    date, close, pct = row
    if prev_close:
        calc_pct = (close - prev_close) / prev_close * 100
        if abs(calc_pct - pct) > 1:
            print(f'  {date}: 数据库pct={pct:.2f}%, 计算pct={calc_pct:.2f}% ❌')
        else:
            print(f'  {date}: pct一致 ✓')
    prev_close = close

print('\n' + '='*60)