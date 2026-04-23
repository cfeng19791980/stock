# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3, pandas as pd, pickle, numpy as np

conn = sqlite3.connect(r'E:\csi10\stocks.db')
with open(r'E:\csi10\model_cache_v5_correct\models_v5_correct.pkl', 'rb') as f:
    models = pickle.load(f)

def get_f(row):
    c = row['close']
    return {
        'pct_chg': float(row['pct_chg']),
        'ma5_ratio': float(c/max(row['ma5'] or c, 0.01)),
        'ma10_ratio': float(c/max(row['ma10'] or c, 0.01)),
        'rsi6': float(row['rsi6'] or 50), 'macd': float(row['macd'] or 0),
        'ma20_ratio': float(c/max(row['ma20'] or c, 0.01)),
        'k': float(row['k'] or 50), 'd': float(row['d'] or 50),
        'boll_ratio': float(c/max(row['boll_upper'] or c, 0.01)),
        'bias10': float(row['bias10'] or 0), 'vr': float(row['vr'] or 1),
        'amplitude': float(row['amplitude'] or 0),
        'atr_5': 0.0, 'atr_20': 0.0, 'volatility_ratio': 1.0,
        'amplitude_10_mean': 0.0, 'volume_ratio': 1.0, 'obv_trend': 0.0,
        'position_20': 0.5, 'position_60': 0.5, 'high_low_ratio': 1.0,
        'day_of_week': 2.0, 'month': 4.0, 'pct_chg_3d': 0.0, 'pct_chg_5d': 0.0,
        'momentum': float(row['pct_chg']),
    }

print("Threshold 50 test (quick):")
total, success = 0, 0
for code in ['605196.SH', '688028.SH']:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '2025-01-01' AND '2025-06-30' AND ma5 IS NOT NULL ORDER BY date", conn)
    for i in range(60, len(df)-3):
        X = pd.DataFrame([get_f(df.iloc[i])]).astype(float)
        try:
            score = int((models['xgb'][code].predict_proba(X)[0][1]*0.4 + models['lgb'][code].predict_proba(X)[0][1]*0.35 + models['cat'][code].predict_proba(X)[0][1]*0.25)*100)
            if score >= 50:
                ret = (df.iloc[i+3]['close'] - df.iloc[i]['close'])/df.iloc[i]['close']*100
                total += 1
                if ret >= 3: success += 1
        except: pass
print(f"  trades={total}, win={success}, rate={success/total*100:.1f}%")

print("\nThreshold 60 test:")
total, success = 0, 0
for code in ['605196.SH', '688028.SH']:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '2025-01-01' AND '2025-06-30' AND ma5 IS NOT NULL ORDER BY date", conn)
    for i in range(60, len(df)-3):
        X = pd.DataFrame([get_f(df.iloc[i])]).astype(float)
        try:
            score = int((models['xgb'][code].predict_proba(X)[0][1]*0.4 + models['lgb'][code].predict_proba(X)[0][1]*0.35 + models['cat'][code].predict_proba(X)[0][1]*0.25)*100)
            if score >= 60:
                ret = (df.iloc[i+3]['close'] - df.iloc[i]['close'])/df.iloc[i]['close']*100
                total += 1
                if ret >= 3: success += 1
        except: pass
print(f"  trades={total}, win={success}, rate={success/total*100 if total else 0:.1f}%")

conn.close()