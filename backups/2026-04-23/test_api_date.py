# -*- coding: utf-8 -*-
"""
测试东方财富K线API - 检查数据日期
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime

print('='*60)
print('东方财富K线API测试')
print('='*60)

url = "http://push2.eastmoney.com/api/qt/stock/kline/get"
params = {
    'secid': '1.000300',  # 沪深300
    'fields1': 'f1,f2,f3,f4,f5,f6',
    'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
    'klt': '101',  # 日K
    'fqt': '1',
    'end': '20500101',
    'lmt': '10',  # 最近10天
}

headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://quote.eastmoney.com/'}
resp = requests.get(url, params=params, headers=headers, timeout=10)
data = resp.json()

print(f'\nAPI返回数据:')
if data.get('data') and data['data'].get('klines'):
    klines = data['data']['klines']
    print(f'  总条数: {len(klines)}')
    print(f'\n  最新5条数据:')
    for line in klines[-5:]:
        parts = line.split(',')
        print(f'    {parts[0]} open={parts[1]} close={parts[2]} high={parts[3]} low={parts[4]} vol={parts[5]} pct={parts[6] if len(parts)>6 else "N/A"}')
else:
    print('  无数据')

print(f'\n当前日期: {datetime.now().strftime("%Y-%m-%d %H:%M")}')

# 对比腾讯实时数据
print('\n腾讯实时数据:')
url2 = "http://qt.gtimg.cn/q=sh000300"
resp2 = requests.get(url2, headers=headers, timeout=10)
resp2.encoding = 'gbk'
import re
match = re.search(r'"([^"]+)"', resp2.text)
if match:
    parts = match.group(1).split('~')
    if len(parts) >= 5:
        print(f'  当前价: {parts[3]} 昨收: {parts[4]}')
        print(f'  时间: {parts[30] if len(parts)>30 else "N/A"}')

print('\n' + '='*60)