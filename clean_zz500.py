import sqlite3
conn = sqlite3.connect('E:/csi10/stocks.db')
cursor = conn.cursor()

# 删除中证500旧数据（只保留最新一条）
cursor.execute('DELETE FROM index_daily WHERE code="sh.000905"')
conn.commit()

print('Deleted old ZZ500 data')

# 重新获取最新数据
import requests
import re
from datetime import datetime

url = 'https://web.sqt.gtimg.cn/q=s_sh000905'
headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://gu.qq.com/sh000905'}
resp = requests.get(url, headers=headers, timeout=10)
text = resp.text

match = re.search(r'v_s_sh000905="(.+?)"', text)
if match:
    parts = match.group(1).split('~')
    name = parts[1]
    close = float(parts[3])
    pct_chg = float(parts[5])
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 插入唯一一条数据
    cursor.execute('''
        INSERT INTO index_daily 
        (code, date, open, close, high, low, volume, pct_chg)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('sh.000905', today, close, close, close, close, 0, pct_chg))
    
    conn.commit()
    print(f'Inserted: {today}, close={close:.2f}, pct_chg={pct_chg:.2f}%')

conn.close()