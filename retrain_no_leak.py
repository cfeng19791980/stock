# -*- coding: utf-8 -*-
"""
v5模型正确训练 - 排除测试数据防止过拟合
训练数据: 2022-2024
测试数据: 2025-2026（不参与训练）
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
import os

DB_PATH = r'E:\csi10\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
MODEL_DIR = r'E:\csi10\model_cache_v5_no_leak'

print("=" * 60)
print("v5模型重新训练 - 无数据泄露版本")
print("训练: 2022-2024 | 测试: 2025-2026")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

TRAIN_END = '2024-12-31'  # 训练截止日期
print(f"训练截止: {TRAIN_END}")

def get_features(row):
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

models = {'xgb': {}, 'lgb': {}, 'cat': {}}

print("\n训练进度:")
for idx, code in enumerate(stock_pool):
    try:
        # 只用2022-2024数据训练
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date <= '{TRAIN_END}' AND ma5 IS NOT NULL ORDER BY date", conn)
        
        if len(df) < 100:
            continue
        
        features = []
        for i in range(60, len(df)-3):
            feat = get_features(df.iloc[i])
            close = df.iloc[i]['close']
            close_3d = df.iloc[i+3]['close']
            rise = (close_3d - close) / close if close > 0 else 0
            feat['target'] = 1 if rise >= 0.03 else 0
            features.append(feat)
        
        if len(features) < 30:
            continue
        
        ds = pd.DataFrame(features)
        X = ds.drop('target', axis=1).astype(float)
        y = ds['target']
        
        xgb_model = xgb.XGBClassifier(n_estimators=100, max_depth=4, random_state=42, verbosity=0)
        xgb_model.fit(X, y)
        models['xgb'][code] = xgb_model
        
        lgb_model = lgb.LGBMClassifier(n_estimators=100, max_depth=4, random_state=42, verbose=-1)
        lgb_model.fit(X, y)
        models['lgb'][code] = lgb_model
        
        cat_model = CatBoostClassifier(iterations=100, depth=4, random_state=42, verbose=False)
        cat_model.fit(X, y)
        models['cat'][code] = cat_model
        
        if idx % 10 == 0:
            print(f"  {idx+1}/30: {code} samples={len(features)}")
        
    except: continue

conn.close()

print(f"\n训练完成: XGB {len(models['xgb'])}只")

# 保存
os.makedirs(MODEL_DIR, exist_ok=True)
with open(os.path.join(MODEL_DIR, 'models_no_leak.pkl'), 'wb') as f:
    pickle.dump(models, f)

print(f"模型保存: {MODEL_DIR}")

# 测试真实胜率（用训练外数据）
print("\n" + "=" * 60)
print("测试真实胜率 (2025年数据)")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
total, success = 0, 0

for code in list(models['xgb'].keys())[:10]:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date > '{TRAIN_END}' AND date <= '2025-06-30' AND ma5 IS NOT NULL ORDER BY date", conn)
    
    if len(df) < 60:
        continue
    
    for i in range(60, len(df)-3):
        X = pd.DataFrame([get_features(df.iloc[i])]).astype(float)
        try:
            score = int((models['xgb'][code].predict_proba(X)[0][1]*0.4 + 
                        models['lgb'][code].predict_proba(X)[0][1]*0.35 + 
                        models['cat'][code].predict_proba(X)[0][1]*0.25)*100)
            
            if score >= 50:
                ret = (df.iloc[i+3]['close'] - df.iloc[i]['close'])/df.iloc[i]['close']*100
                total += 1
                if ret >= 3: success += 1
        except: pass

conn.close()

print(f"总交易: {total}")
print(f"成功: {success}")
print(f"真实胜率: {success/total*100:.1f}%")

if success/total*100 >= 70:
    print("✅ 模型有效!")
else:
    print("⚠️ 胜率偏低，需进一步优化")

print("=" * 60)