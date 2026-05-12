# -*- coding: utf-8 -*-
"""
csi10 回测系统 - 验证模型升级效果
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import sqlite3
import json
from datetime import datetime

DB_PATH = r'E:\csi10\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

print("=" * 60)
print("csi10 回测系统")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

print(f"股票池: {len(stock_pool)}只")

# 回测参数
START_DATE = '2025-01-01'
END_DATE = '2026-04-20'
BUY_THRESHOLD = 60
SELL_THRESHOLD = 15
HOLD_DAYS = 3

print(f"回测区间: {START_DATE} ~ {END_DATE}")

# 统计变量
total_trades = 0
success_trades = 0
total_return = 0
returns = []

print("\n开始回测...")

for code in stock_pool[:10]:  # 先测10只
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '{START_DATE}' AND '{END_DATE}' ORDER BY date", conn)
        if len(df) < 100:
            continue
        
        # 简化评分（基于涨跌趋势）
        for i in range(len(df)-HOLD_DAYS):
            row = df.iloc[i]
            close = row['close']
            ma5 = row['ma5'] if pd.notna(row['ma5']) else close
            ma10 = row['ma10'] if pd.notna(row['ma10']) else close
            
            # 简化评分逻辑
            score = 50
            if close > ma5:
                score += 10
            if close > ma10:
                score += 10
            if row['pct_chg'] > 2:
                score += 10
            elif row['pct_chg'] < -2:
                score -= 10
            
            # 模拟买入
            if score >= BUY_THRESHOLD:
                future_close = df.iloc[i+HOLD_DAYS]['close']
                trade_return = (future_close - close) / close * 100
                total_trades += 1
                returns.append(trade_return)
                
                if trade_return >= 3:
                    success_trades += 1
                
                total_return += trade_return
        
    except Exception as e:
        continue

conn.close()

# 计算指标
if total_trades > 0:
    win_rate = success_trades / total_trades * 100
    avg_return = total_return / total_trades
    max_return = max(returns) if returns else 0
    min_return = min(returns) if returns else 0
    
    # 最大回撤模拟
    cumulative = np.cumsum(returns)
    peak = np.maximum.accumulate(cumulative)
    drawdown = peak - cumulative
    max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
    
    # 夏普比率简化
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252/3) if np.std(returns) > 0 else 0
    
    print(f"\n回测结果:")
    print(f"  总交易次数: {total_trades}")
    print(f"  成功次数: {success_trades}")
    print(f"  胜率: {win_rate:.1f}%")
    print(f"  平均收益: {avg_return:.2f}%")
    print(f"  最大收益: {max_return:.2f}%")
    print(f"  最大亏损: {min_return:.2f}%")
    print(f"  最大回撤: {max_drawdown:.2f}%")
    print(f"  夏普比率: {sharpe:.2f}")
    
    # 保存回测结果
    backtest_result = {
        'timestamp': datetime.now().isoformat(),
        'period': f"{START_DATE} ~ {END_DATE}",
        'trades': total_trades,
        'win_rate': round(win_rate, 2),
        'avg_return': round(avg_return, 2),
        'max_return': round(max_return, 2),
        'min_return': round(min_return, 2),
        'max_drawdown': round(max_drawdown, 2),
        'sharpe': round(sharpe, 2),
    }
    
    with open(r'E:\csi10\backtest_result.json', 'w', encoding='utf-8') as f:
        json.dump(backtest_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n回测结果已保存: E:\\csi10\\backtest_result.json")
    
else:
    print("无交易记录")

print("=" * 60)