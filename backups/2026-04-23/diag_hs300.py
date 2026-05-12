# -*- coding: utf-8 -*-
"""
腾讯API测试 - 检查沪深300数据
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
import re
from datetime import datetime

print('='*60)
print('沪深300数据诊断')
print('='*60)

# 腾讯实时数据
print('\n[腾讯实时API]')
try:
    url = "http://qt.gtimg.cn/q=sh000300"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = 'gbk'
    
    match = re.search(r'"([^"]+)"', resp.text)
    if match:
        parts = match.group(1).split('~')
        print(f'  原始数据: {parts[:10]}')
        print(f'  名称: {parts[1]}')
        print(f'  代码: {parts[2]}')
        print(f'  当前价: {parts[3]}')
        print(f'  昨收: {parts[4]}')
        print(f'  今开: {parts[5]}')
        print(f'  成交量: {parts[6]}')
        print(f'  时间: {parts[30] if len(parts)>30 else "N/A"}')
        print(f'  涨跌额: {parts[31] if len(parts)>31 else "N/A"}')
        print(f'  涨跌幅: {parts[32] if len(parts)>32 else "N/A"}')
        
        # 计算涨跌幅
        price = float(parts[3])
        prev = float(parts[4])
        calc_pct = (price - prev) / prev * 100
        print(f'  计算涨跌幅: {calc_pct:.2f}%')
except Exception as e:
    print(f'  错误: {e}')

# 当前时间
print(f'\n当前时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

# 数据库对比
import sqlite3
conn = sqlite3.connect(r'E:\csi10\stocks.db')
cursor = conn.cursor()
cursor.execute("SELECT date, close, pct_chg FROM index_daily WHERE code='sh.000300' ORDER BY date DESC LIMIT 3")
db_data = cursor.fetchall()
conn.close()

print('\n[数据库数据]')
for row in db_data:
    print(f'  {row[0]} close={row[1]:.2f} pct={row[2]:.2f}%')

print('\n[问题分析]')
if db_data:
    db_date = db_data[0][0]
    db_close = db_data[0][1]
    today = datetime.now().strftime('%Y-%m-%d')
    
    if db_date == today:
        print(f'  数据库日期正确({today})')
    else:
        print(f'  数据库日期错误: {db_date} (应为{today})')
    
    # 检查价格是否合理
    try:
        current_price = float(parts[3])
        if abs(db_close - current_price) > 50:
            print(f'  价格差异过大: DB={db_close:.2f} vs 当前={current_price:.2f}')
            print(f'  可能原因: 数据库存储的是昨收价格')
        else:
            print(f'  价格接近: DB={db_close:.2f} 当前={current_price:.2f}')
    except:
        pass

print('\n' + '='*60)