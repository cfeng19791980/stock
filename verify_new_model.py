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
print("验证重新训练的v5模型评分")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

with open(MODEL_CACHE, 'rb') as f:
    models = pickle.load(f)

print(f"模型加载: XGB {len(models['xgb'])}只")

# 特征提取
def get_features(df, i):
    row = df.iloc[i]
    close = row['close']
    
    feat = {
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
    return feat

# 测试评分
scores = []
print("\n测试最新数据评分:")

for code in list(models['xgb'].keys())[:5]:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND ma5 IS NOT NULL ORDER BY date DESC LIMIT 10", conn)
    
    if len(df) < 10:
        continue
    
    latest = df.iloc[0]
    feat = get_features(df, 0)  # 最新数据
    
    # 确保所有值为float
    X = pd.DataFrame([feat]).astype(float)
    
    xgb_p = models['xgb'][code].predict_proba(X)[0][1]
    lgb_p = models['lgb'][code].predict_proba(X)[0][1]
    cat_p = models['cat'][code].predict_proba(X)[0][1]
    
    score = int((xgb_p * 0.4 + lgb_p * 0.35 + cat_p * 0.25) * 100)
    scores.append(score)
    
    print(f"  {code}: xgb={xgb_p:.3f} lgb={lgb_p:.3f} cat={cat_p:.3f} -> score={score}")

conn.close()

print("\n" + "=" * 60)
print("评分统计")
print("=" * 60)
print(f"样本: {len(scores)}")
print(f"范围: {min(scores)} ~ {max(scores)}")
print(f"平均: {np.mean(scores):.1f}")

if np.mean(scores) > 50:
    print("✅ 模型评分正常!")
else:
    print("⚠️ 评分仍偏低，需进一步检查")

print("=" * 60)