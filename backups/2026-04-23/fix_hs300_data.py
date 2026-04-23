# -*- coding: utf-8 -*-
"""
修复index_daily表结构并更新数据
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import requests
import re
from datetime import datetime

DB_PATH = r'E:\csi10\stocks.db'

print('='*60)
print('修复沪深300数据')
print('='*60)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. 检查表结构
print('\n[Step 1] 检查表结构')
cursor.execute("PRAGMA table_info(index_daily)")
cols = cursor.fetchall()
col_names = [c[1] for c in cols]
print(f'  当前列: {col_names}')

# 2. 添加缺失列
if 'amount' not in col_names:
    cursor.execute("ALTER TABLE index_daily ADD COLUMN amount REAL")
    print('  ✓ 添加amount列')
if 'turnover' not in col_names:
    cursor.execute("ALTER TABLE index_daily ADD COLUMN turnover REAL")
    print('  ✓ 添加turnover列')
if 'prev_close' not in col_names:
    cursor.execute("ALTER TABLE index_daily ADD COLUMN prev_close REAL")
    print('  ✓ 添加prev_close列')

conn.commit()

# 3. 获取腾讯实时数据
print('\n[Step 2] 获取腾讯实时数据')
url = "http://qt.gtimg.cn/q=sh000300"
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers, timeout=10)
resp.encoding = 'gbk'

match = re.search(r'"([^"]+)"', resp.text)
if match:
    parts = match.group(1).split('~')
    price = float(parts[3])
    prev_close = float(parts[4])
    open_price = float(parts[5]) if parts[5] else price
    high = float(parts[33]) if len(parts)>33 and parts[33] else price
    low = float(parts[34]) if len(parts)>34 and parts[34] else price
    volume = float(parts[36]) * 100 if len(parts)>36 and parts[36] else 0
    amount = float(parts[37]) * 10000 if len(parts)>37 and parts[37] else 0
    pct_chg = (price - prev_close) / prev_close * 100
    
    print(f'  当前价: {price:.2f}')
    print(f'  昨收: {prev_close:.2f}')
    print(f'  涨跌幅: {pct_chg:.2f}%')

# 4. 更新今日数据
print('\n[Step 3] 更新今日数据')
today = datetime.now().strftime('%Y-%m-%d')
cursor.execute('SELECT COUNT(*) FROM index_daily WHERE code="sh.000300" AND date=?', (today,))
exists = cursor.fetchone()[0]

if exists > 0:
    cursor.execute('''
        UPDATE index_daily SET 
            open=?, close=?, high=?, low=?, volume=?, amount=?, pct_chg=?, prev_close=?
        WHERE code="sh.000300" AND date=?
    ''', (open_price, price, high, low, volume, amount, pct_chg, prev_close, today))
    print(f'  ✓ 更新今日数据: {today}')
else:
    cursor.execute('''
        INSERT INTO index_daily (code, date, open, close, high, low, volume, amount, pct_chg, prev_close)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('sh.000300', today, open_price, price, high, low, volume, amount, pct_chg, prev_close))
    print(f'  ✓ 新增今日数据: {today}')

conn.commit()

# 5. 验证更新后的数据
print('\n[Step 4] 验证更新后数据')
cursor.execute('SELECT date, close, pct_chg, prev_close FROM index_daily WHERE code="sh.000300" ORDER BY date DESC LIMIT 5')
rows = cursor.fetchall()
for row in rows:
    print(f'  {row[0]} close={row[1]:.2f} pct={row[2]:.2f}% prev={row[3] if row[3] else "N/A"}')

conn.close()
print('\n' + '='*60)
print('修复完成!')
print('='*60)