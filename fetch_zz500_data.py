# -*- coding: utf-8 -*-
"""获取中证500历史数据"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import sqlite3
import requests
import re
from datetime import datetime

DB_PATH = r'E:\csi10\stocks.db'

def fetch_zz500_history(days=30):
    """获取中证500历史数据（最近30天）"""
    try:
        # 使用东方财富API
        url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            'secid': '1.000905',  # 中证500
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': '101',  # 日K线
            'fqt': '1',    # 前复权
            'end': '20500101',
            'lmt': days,
        }
        
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://quote.eastmoney.com/'}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        
        if data.get('data') and data['data'].get('klines'):
            klines = data['data']['klines']
            
            # 解析K线数据
            records = []
            for kline in klines:
                parts = kline.split(',')
                date = parts[0]
                open_price = float(parts[1])
                close_price = float(parts[2])
                high_price = float(parts[3])
                low_price = float(parts[4])
                volume = float(parts[5]) if parts[5] != '-' else 0
                amount = float(parts[6]) if parts[6] != '-' else 0
                pct_chg = float(parts[7]) if parts[7] != '-' else 0
                
                records.append({
                    'code': 'sh.000905',
                    'name': '中证500',
                    'date': date,
                    'open': open_price,
                    'close': close_price,
                    'high': high_price,
                    'low': low_price,
                    'volume': volume,
                    'amount': amount,
                    'pct_chg': pct_chg,
                })
            
            # 保存到数据库
            conn = sqlite3.connect(DB_PATH)
            
            # 检查表结构
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(index_daily)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # 如果缺少amount列，添加它
            if 'amount' not in columns:
                print("Adding amount column to index_daily...")
                cursor.execute("ALTER TABLE index_daily ADD COLUMN amount REAL")
                conn.commit()
            
            # 删除旧数据
            cursor.execute("DELETE FROM index_daily WHERE code='sh.000905'")
            
            # 插入新数据
            df = pd.DataFrame(records)
            df.to_sql('index_daily', conn, if_exists='append', index=False)
            
            conn.commit()
            conn.close()
            
            print(f"✓ Successfully fetched {len(records)} days of ZZ500 data")
            print(f"  Latest: {records[0]['date']} close={records[0]['close']}")
            print(f"  5d trend: {records[0]['close']} vs {records[4]['close']} = {(records[0]['close']-records[4]['close'])/records[4]['close']*100:.2f}%")
            
            return records
            
    except Exception as e:
        print(f"✗ Error fetching ZZ500: {e}")
        return None

def fetch_zz500_tencent(days=5):
    """获取中证500最新数据（腾讯API）"""
    try:
        # 腾讯股票API
        url = 'https://web.sqt.gtimg.cn/q='
        params = {'q': 's_sh000905'}  # 中证500代码
        
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://gu.qq.com/sh000905'}
        resp = requests.get(url + 's_sh000905', headers=headers, timeout=10)
        text = resp.text
        
        # 解析腾讯返回格式: v_s_sh000905="1~中证500~6000.00~..."
        if 'v_s_sh' in text:
            print(f"Raw response: {text[:200]}")  # Debug output
            match = re.search(r'v_s_sh000905="(.+?)"', text)
            if match:
                data_str = match.group(1)
                parts = data_str.split('~')
                
                # parts格式: [序号, 名称, 代码, 当前价格, 涨跌额, 涨跌幅%, 成交量, ...]
                name = parts[1] if len(parts) > 1 else '中证500'
                close = float(parts[3]) if len(parts) > 3 else 0
                pct_chg = float(parts[5]) if len(parts) > 5 else 0
                
                today = datetime.now().strftime('%Y-%m-%d')
                
                # 保存到数据库
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # 检查表结构
                cursor.execute("PRAGMA table_info(index_daily)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'amount' not in columns:
                    cursor.execute("ALTER TABLE index_daily ADD COLUMN amount REAL")
                    conn.commit()
                
                # 插入今日数据（不包含name列）
                cursor.execute('''
                    INSERT OR REPLACE INTO index_daily 
                    (code, date, open, close, high, low, volume, amount, pct_chg)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('sh.000905', today, close, close, close, close, 0, 0, pct_chg))
                
                conn.commit()
                conn.close()
                
                print(f"✓ Successfully fetched ZZ500 from Tencent")
                print(f"  Date: {today}, Close: {close:.2f}, Change: {pct_chg:.2f}%")
                
                return {'date': today, 'close': close, 'pct_chg': pct_chg}
        
        print("✗ Failed to parse Tencent response")
        return None
        
    except Exception as e:
        print(f"✗ Error fetching ZZ500 from Tencent: {e}")
        return None

if __name__ == '__main__':
    print("="*60)
    print("Fetching ZZ500 (中证500) latest data from Tencent...")
    print("="*60)
    fetch_zz500_tencent(5)