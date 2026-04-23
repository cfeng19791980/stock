# -*- coding: utf-8 -*-
"""
csi10 v5模型重新训练 - 使用正确特征顺序
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle
import json
from datetime import datetime

DB_PATH = r'E:\csi10\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
MODEL_CACHE = r'E:\csi10\model_cache_v5_correct'

print("=" * 60)
print("v5模型重新训练 (统一特征顺序)")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

# 正确的特征提取（正序数据）
def extract_features_correct(df, i):
    """正确特征提取 - 无反转"""
    if i < 30 or i >= len(df):
        return None
    
    row = df.iloc[i]
    close = row['close']
    
    feat = {
        'pct_chg': row['pct_chg'],
        'ma5_ratio': close / max(row['ma5'] or close, 0.01),
        'ma10_ratio': close / max(row['ma10'] or close, 0.01),
        'rsi6': row['rsi6'] or 50,
        'macd': row['macd'] or 0,
        'ma20_ratio': close / max(row['ma20'] or close, 0.01),
        'k': row['k'] or 50,
        'd': row['d'] or 50,
        'boll_ratio': close / max(row['boll_upper'] or close, 0.01),
        'bias10': row['bias10'] or 0,
        'vr': row['vr'] or 1,
        'amplitude': row['amplitude'] or 0,
    }
    
    # 扩展特征
    feat.update({
        'atr_5': 0, 'atr_20': 0, 'volatility_ratio': 1,
        'amplitude_10_mean': 0, 'volume_ratio': 1, 'obv_trend': 0,
        'position_20': 0.5, 'position_60': 0.5, 'high_low_ratio': 1,
        'day_of_week': 2, 'month': 4, 'pct_chg_3d': 0, 'pct_chg_5d': 0,
        'momentum': feat['pct_chg'],
    })
    
    return feat

# 训练
models = {'xgb': {}, 'lgb': {}, 'cat': {}}
features_list = {}

print("训练进度:")
for idx, code in enumerate(stock_pool):
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND ma5 IS NOT NULL ORDER BY date", conn)
        if len(df) < 100:
            continue
        
        features = []
        for i in range(60, len(df)-3):
            feat = extract_features_correct(df, i)
            if feat:
                close = df.iloc[i]['close']
                close_3d = df.iloc[i+3]['close']
                rise = (close_3d - close) / close if close > 0 else 0
                feat['target'] = 1 if rise >= 0.03 else 0
                features.append(feat)
        
        if len(features) < 30:
            continue
        
        ds = pd.DataFrame(features)
        X = ds.drop('target', axis=1)
        y = ds['target']
        
        # 训练三个模型
        xgb_model = xgb.XGBClassifier(n_estimators=100, max_depth=4, random_state=42, verbosity=0)
        xgb_model.fit(X, y)
        models['xgb'][code] = xgb_model
        
        lgb_model = lgb.LGBMClassifier(n_estimators=100, max_depth=4, random_state=42, verbose=-1)
        lgb_model.fit(X, y)
        models['lgb'][code] = lgb_model
        
        cat_model = CatBoostClassifier(iterations=100, depth=4, random_state=42, verbose=False)
        cat_model.fit(X, y)
        models['cat'][code] = cat_model
        
        features_list[code] = list(X.columns)
        
        if idx % 10 == 0:
            print(f"  {idx+1}/{len(stock_pool)}: {code} - samples={len(features)}")
        
    except Exception as e:
        continue

conn.close()

print(f"\n训练完成: XGB {len(models['xgb'])}, LGB {len(models['lgb'])}, CAT {len(models['cat'])}")

# 保存
import os
os.makedirs(MODEL_CACHE, exist_ok=True)
with open(os.path.join(MODEL_CACHE, 'models_v5_correct.pkl'), 'wb') as f:
    pickle.dump(models, f)

# 保存特征列表
with open(os.path.join(MODEL_CACHE, 'features_list.json'), 'w') as f:
    json.dump(features_list, f)

print(f"模型已保存: {MODEL_CACHE}")

# 测试评分
print("\n" + "=" * 60)
print("快速测试新模型评分")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
for code in list(models['xgb'].keys())[:3]:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date DESC LIMIT 10", conn)
    df = df.iloc[::-1]  # 转回正序
    
    for i in range(5, min(len(df)-3, 8)):
        feat = extract_features_correct(df, i)
        X = pd.DataFrame([feat])
        
        xgb_p = models['xgb'][code].predict_proba(X)[0][1]
        lgb_p = models['lgb'][code].predict_proba(X)[0][1]
        cat_p = models['cat'][code].predict_proba(X)[0][1]
        
        score = int((xgb_p * 0.4 + lgb_p * 0.35 + cat_p * 0.25) * 100)
        print(f"{code}: xgb={xgb_p:.2f} lgb={lgb_p:.2f} cat={cat_p:.2f} -> score={score}")

conn.close()

print("\n如果评分不为0，说明修复成功!")
print("=" * 60)