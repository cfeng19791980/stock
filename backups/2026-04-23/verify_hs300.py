# -*- coding: utf-8 -*-
"""
沪深300数据验证脚本
对比数据库数据与实时API数据
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import requests
import re
from datetime import datetime

DB_PATH = r'E:\csi10\stocks.db'

print('='*60)
print('沪深300数据验证')
print('='*60)

# 1. 数据库数据
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT date, close, pct_chg FROM index_daily WHERE code='sh.000300' ORDER BY date DESC LIMIT 5")
db_data = cursor.fetchall()
conn.close()

print('\n[数据库数据]')
for row in db_data:
    print(f'  {row[0]} close={row[1]:.2f} pct={row[2]:.2f}%')

# 2. 东方财富实时API
print('\n[东方财富实时API]')
try:
    url = "http://push2.eastmoney.com/api/qt/stock/get"
    params = {
        'secid': '1.000300',
        'fields': 'f43,f44,f47,f49,f50,f51',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
    }
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://quote.eastmoney.com/'}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    data = resp.json()
    
    if data.get('data'):
        d = data['data']
        close = d.get('f47', 0) / 100 if d.get('f47') else 0
        prev_close = d.get('f44', 0) / 100 if d.get('f44') else 0
        pct_chg = d.get('f49', 0) / 100 if d.get('f49') else 0
        print(f'  close={close:.2f} prev={prev_close:.2f} pct={pct_chg:.2f}%')
    else:
        print('  API无数据')
except Exception as e:
    print(f'  API错误: {e}')

# 3. 腾讯实时API
print('\n[腾讯实时API]')
try:
    url = "http://qt.gtimg.cn/q=sh000300"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = 'gbk'
    
    match = re.search(r'"([^"]+)"', resp.text)
    if match:
        parts = match.group(1).split('~')
        if len(parts) >= 5:
            name = parts[1]
            price = float(parts[3]) if parts[3] else 0
            prev_close = float(parts[4]) if parts[4] else 0
            pct_chg = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            print(f'  {name} close={price:.2f} prev={prev_close:.2f} pct={pct_chg:.2f}%')
except Exception as e:
    print(f'  API错误: {e}')

# 4. 对比分析
print('\n[对比分析]')
if db_data:
    db_close = db_data[0][1]
    db_date = db_data[0][0]
    today = datetime.now().strftime('%Y-%m-%d')
    
    if db_date == today:
        print(f'  数据库日期: {db_date} (今日最新)')
    else:
        print(f'  数据库日期: {db_date} (非今日，需更新)')
        print(f'  当前日期: {today}')
    
    print(f'  数据库收盘价: {db_close:.2f}')
    
    # 东方财富对比
    try:
        resp2 = requests.get(url, params=params, headers=headers, timeout=10)
        data2 = resp2.json()
        if data2.get('data'):
            api_close = data2['data'].get('f47', 0) / 100
            diff = abs(db_close - api_close)
            if diff < 0.1:
                print(f'  东方财富收盘价: {api_close:.2f} ✓ 一致')
            else:
                print(f'  东方财富收盘价: {api_close:.2f} ✗ 差异={diff:.2f}')
    except:
        pass

print('\n' + '='*60)