# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import pandas as pd
import pickle
import numpy as np

DB_PATH = r'E:\csi10\stocks.db'
MODEL_CACHE = r'E:\csi10\model_cache_v5_correct\models_v5_correct.pkl'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

print("=" * 60)
print("v5模型 - 不同阈值对比测试")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

with open(MODEL_CACHE, 'rb') as f:
    models = pickle.load(f)

def get_features(row, close):
    return {
        'pct_chg': float(row['pct_chg']),
        'ma5_ratio': float(close / max(row['ma5'] or close, 0.01)),
        'ma10_ratio': float(close / max(row['ma10'] or close, 0.01)),
        'rsi6': float(row['rsi6'] or 50),
        'macd': float(row['macd'] or 0),
        'ma20_ratio': float(close / max(row['ma20'] or close, 0.01)),
        'k': float(row['k'] or 50),
        'd': float(row['d'] or 50),
        'boll_ratio': float(close / max(row['boll_upper'] or close, 0.01)),
        'bias10': float(row['bias10'] or 0),
        'vr': float(row['vr'] or 1),
        'amplitude': float(row['amplitude'] or 0),
        'atr_5': 0.0, 'atr_20': 0.0, 'volatility_ratio': 1.0,
        'amplitude_10_mean': 0.0, 'volume_ratio': 1.0, 'obv_trend': 0.0,
        'position_20': 0.5, 'position_60': 0.5, 'high_low_ratio': 1.0,
        'day_of_week': 2.0, 'month': 4.0, 'pct_chg_3d': 0.0, 'pct_chg_5d': 0.0,
        'momentum': float(row['pct_chg']),
    }

# 测试不同阈值
for threshold in [30, 40, 50, 60, 70]:
    total = 0
    success = 0
    returns = []
    
    for code in stock_pool[:15]:  # 测试15只
        if code not in models['xgb']:
            continue
        
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '2025-01-01' AND '2026-03-20' AND ma5 IS NOT NULL ORDER BY date", conn)
        
        if len(df) < 60:
            continue
        
        for i in range(60, len(df)-3):
            row = df.iloc[i]
            feat = get_features(row, row['close'])
            X = pd.DataFrame([feat]).astype(float)
            
            try:
                xgb_p = models['xgb'][code].predict_proba(X)[0][1]
                lgb_p = models['lgb'][code].predict_proba(X)[0][1]
                cat_p = models['cat'][code].predict_proba(X)[0][1]
                score = int((xgb_p * 0.4 + lgb_p * 0.35 + cat_p * 0.25) * 100)
                
                if score >= threshold:
                    future = df.iloc[i+3]['close']
                    ret = (future - row['close']) / row['close'] * 100
                    total += 1
                    returns.append(ret)
                    if ret >= 3:
                        success += 1
            except:
                continue
    
    if total > 0:
        win_rate = success / total * 100
        avg_ret = np.mean(returns)
        print(f"阈值{threshold}分: {total}笔交易, 胜率{win_rate:.1f}%, 平均收益{avg_ret:.2f}%")
    else:
        print(f"阈值{threshold}分: 无交易")

conn.close()
print("=" * 60)