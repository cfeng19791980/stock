# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import pandas as pd
import pickle
import numpy as np
import json
from datetime import datetime

DB_PATH = r'E:\csi10\stocks.db'
MODEL_CACHE = r'E:\csi10\model_cache_v5\models_v5.pkl'

print("=" * 60)
print("csi10 真实模型回测 (修正版)")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)

# 正确的历史区间
START_DATE = '2024-01-01'
END_DATE = '2025-12-31'  # 使用2024-2025年历史数据
HOLD_DAYS = 3
BUY_THRESHOLD = 60

print(f"回测区间: {START_DATE} ~ {END_DATE}")

# 加载模型
with open(MODEL_CACHE, 'rb') as f:
    models = pickle.load(f)
print(f"模型加载: {len(models['xgb'])}只")

# 获取股票池
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT code FROM daily_price LIMIT 30")
stock_pool = [r[0] for r in cursor.fetchall()]

# 特征提取（简化版）
def get_features(df, i):
    row = df.iloc[i]
    close = row['close']
    return {
        'pct_chg': row['pct_chg'],
        'ma5_ratio': close / max(row['ma5'], 0.01),
        'ma10_ratio': close / max(row['ma10'], 0.01),
        'rsi6': row['rsi6'] if pd.notna(row['rsi6']) else 50,
        'macd': row['macd'] if pd.notna(row['macd']) else 0,
        'ma20_ratio': close / max(row['ma20'] if pd.notna(row['ma20']) else close, 0.01),
        'k': row['k'] if pd.notna(row['k']) else 50,
        'd': row['d'] if pd.notna(row['d']) else 50,
        'boll_ratio': close / max(row['boll_upper'] if pd.notna(row['boll_upper']) else close, 0.01),
        'bias10': row['bias10'] if pd.notna(row['bias10']) else 0,
        'vr': row['vr'] if pd.notna(row['vr']) else 1,
        'amplitude': row['amplitude'] if pd.notna(row['amplitude']) else 0,
        'atr_5': 0, 'atr_20': 0, 'volatility_ratio': 1, 'amplitude_10_mean': 0,
        'volume_ratio': 1, 'obv_trend': 0, 'position_20': 0.5, 'position_60': 0.5,
        'high_low_ratio': 1, 'day_of_week': 2, 'month': 4,
        'pct_chg_3d': 0, 'pct_chg_5d': 0, 'momentum': row['pct_chg'],
    }

total_trades = 0
success = 0
returns = []

print("回测进度:")
for idx, code in enumerate(stock_pool):
    if code not in models['xgb']:
        continue
    
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '{START_DATE}' AND '{END_DATE}' ORDER BY date", conn)
    
    if len(df) < 60:
        continue
    
    trades = 0
    for i in range(60, len(df)-HOLD_DAYS):
        feat = get_features(df, i)
        X = pd.DataFrame([feat])
        
        try:
            xgb_pred = models['xgb'][code].predict_proba(X)[0][1]
            lgb_pred = models['lgb'][code].predict_proba(X)[0][1]
            cat_pred = models['cat'][code].predict_proba(X)[0][1]
            
            score = int((xgb_pred * 0.4 + lgb_pred * 0.35 + cat_pred * 0.25) * 100)
            
            if score >= BUY_THRESHOLD:
                close = df.iloc[i]['close']
                future = df.iloc[i+HOLD_DAYS]['close']
                ret = (future - close) / close * 100
                
                total_trades += 1
                returns.append(ret)
                if ret >= 3:
                    success += 1
                trades += 1
        except:
            continue
    
    if idx % 5 == 0:
        print(f"  {idx+1}/{len(stock_pool)}: {code} trades={trades}")

conn.close()

print("\n" + "=" * 60)
if total_trades > 0:
    win_rate = success / total_trades * 100
    avg_ret = np.mean(returns)
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(84) if np.std(returns) > 0 else 0
    
    print(f"总交易: {total_trades}")
    print(f"胜率: {win_rate:.1f}%")
    print(f"平均收益: {avg_ret:.2f}%")
    print(f"夏普: {sharpe:.2f}")
    
    # 对比v4
    print(f"\n对比: v4=75% vs v5={win_rate:.1f}%")
    
    if win_rate < 75:
        gap = 75 - win_rate
        print(f"差距: {gap:.1f}%")
        print("建议: 调整融合权重或增加训练数据")
    
    # 保存
    with open(r'E:\csi10\backtest_v5_correct.json', 'w') as f:
        json.dump({'win_rate': win_rate, 'trades': total_trades, 'avg_return': avg_ret}, f)
else:
    print("无交易 - 模型评分均低于60")

print("=" * 60)