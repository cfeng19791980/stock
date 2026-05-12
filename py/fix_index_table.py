# -*- coding: utf-8 -*-
"""快速修复index_daily表"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3

DB = r'E:\股票\csi500_data\stocks.db'
conn = sqlite3.connect(DB)
cursor = conn.cursor()

print("修复index_daily表...")

# 删除旧表
cursor.execute("DROP TABLE IF EXISTS index_daily")

# 创建新表（18列）
cursor.execute('''CREATE TABLE index_daily (
    code TEXT,
    date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    pct_chg REAL,
    ma5 REAL,
    ma10 REAL,
    ma20 REAL,
    ma30 REAL,
    ema12 REAL,
    ema26 REAL,
    macd REAL,
    macd_signal REAL,
    macd_hist REAL,
    rsi6 REAL
)''')

conn.commit()
conn.close()
print("✓ 表结构已修复（18列）")

# 运行数据获取
import subprocess
subprocess.run(['python', r'e:\csi10\market_index_fetcher.py'], shell=True)