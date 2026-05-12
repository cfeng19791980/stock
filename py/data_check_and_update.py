# -*- coding: utf-8 -*-
"""
数据自动更新脚本
用途: 每交易日开盘前自动更新数据
原则: 准确性第一，确保数据实时性
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import pandas as pd
from datetime import datetime, time as dt_time
import subprocess
import os

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
FETCHER_SCRIPT = r'e:\csi10\data_fetcher.py'

print("=" * 70)
print("数据自动更新检查")
print("=" * 70)

# 检查是否是交易时间（9:30-15:00）
now = datetime.now()
current_time = now.time()

# A股交易时间
trading_hours = [
    (dt_time(9, 30), dt_time(11, 30)),  # 早盘
    (dt_time(13, 0), dt_time(15, 0)),   # 午盘
]

is_trading_time = any(start <= current_time <= end for start, end in trading_hours)

print(f"\n当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"交易时间: {'是' if is_trading_time else '否'}")

# 检查数据完整性
conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

today = now.strftime('%Y-%m-%d')
query = f"""
SELECT code, MAX(date) as latest_date, COUNT(*) as data_count
FROM daily_price
WHERE code IN ({','.join([f"'{c}'" for c in stock_pool])})
GROUP BY code
"""
stock_dates = pd.read_sql(query, conn)
conn.close()

# 统计数据状态
latest_stocks = stock_dates[stock_dates['latest_date'] == today]
outdated_stocks = stock_dates[stock_dates['latest_date'] < today]

print(f"\n数据状态:")
print(f"  已更新到今天: {len(latest_stocks)}只")
print(f"  数据滞后: {len(outdated_stocks)}只")

# 决策：是否需要更新
need_update = False

if len(outdated_stocks) > 0:
    print(f"\n❌ 发现滞后数据，需要更新")
    print("滞后股票:")
    print(outdated_stocks.to_string(index=False))
    need_update = True
elif is_trading_time and len(latest_stocks) < len(stock_pool):
    print(f"\n⚠️ 交易时间但数据不完整，需要更新")
    need_update = True
else:
    print(f"\n✅ 数据完整，无需更新")

# 执行更新
if need_update:
    print("\n启动数据更新...")
    print("-" * 70)
    
    try:
        # 运行数据获取脚本
        result = subprocess.run(
            ['python', FETCHER_SCRIPT],
            capture_output=True,
            text=True,
            timeout=180,
            encoding='utf-8',
            cwd=r'e:\csi10'
        )
        
        print(result.stdout)
        
        if result.returncode == 0:
            print("\n✅ 数据更新成功！")
            
            # 验证更新结果
            conn = sqlite3.connect(DB_PATH)
            query = f"""
            SELECT code, MAX(date) as latest_date
            FROM daily_price
            WHERE code IN ({','.join([f"'{c}'" for c in stock_pool])})
            GROUP BY code
            """
            new_dates = pd.read_sql(query, conn)
            conn.close()
            
            updated_today = new_dates[new_dates['latest_date'] == today]
            print(f"更新后统计: {len(updated_today)}/{len(stock_pool)}只股票已更新到今天")
            
        else:
            print(f"\n⚠️ 数据更新失败: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("\n❌ 数据更新超时（180秒）")
    except Exception as e:
        print(f"\n❌ 数据更新异常: {e}")

print("\n" + "=" * 70)
print("检查完成")
print("=" * 70)

# 返回状态
exit(0 if not need_update else 1)