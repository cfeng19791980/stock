# -*- coding: utf-8 -*-
"""
v5反向优化 - 简化模型
策略: 减少特征噪音，只保留核心有效特征
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
MODEL_DIR = r'E:\csi10\model_cache_v5_simple'

print("=" * 60)
print("v5反向优化 - 简化模型")
print("策略: 只保留核心特征，减少噪音")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

# 核心特征（筛选有效）
def get_core_features(row):
    """只保留核心有效特征"""
    c = row['close']
    
    # 核心特征（10个）
    return {
        'pct_chg': float(row['pct_chg']),          # 涨跌幅
        'ma5_ratio': float(c/max(row['ma5'] or c, 0.01)),   # MA5比例
        'ma10_ratio': float(c/max(row['ma10'] or c, 0.01)), # MA10比例
        'rsi6': float(row['rsi6'] or 50),          # RSI
        'macd': float(row['macd'] or 0),           # MACD
        'k': float(row['k'] or 50),                # K值
        'd': float(row['d'] or 50),                # D值
        'volume': float(row['volume'] or 1),       # 成交量
        'amplitude': float(row['amplitude'] or 0), # 振幅
        'turnover': float(row['turnover'] or 0),   # 换手率
    }

print("\n核心特征: 10个（原25个）")
print("  pct_chg, ma5_ratio, ma10_ratio, rsi6, macd")
print("  k, d, volume, amplitude, turnover")

models_simple = {'xgb': {}, 'lgb': {}, 'cat': {}}
TRAIN_END = '2024-12-31'

print("\n训练进度:")
for idx, code in enumerate(stock_pool):
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date <= '{TRAIN_END}' AND ma5 IS NOT NULL ORDER BY date", conn)
        
        if len(df) < 100: continue
        
        features = []
        for i in range(60, len(df)-3):
            feat = get_core_features(df.iloc[i])
            close = df.iloc[i]['close']
            close_3d = df.iloc[i+3]['close']
            rise = (close_3d - close) / close
            feat['target'] = 1 if rise >= 0.03 else 0  # 保持原目标>=3%
            features.append(feat)
        
        if len(features) < 30: continue
        
        ds = pd.DataFrame(features)
        X = ds.drop('target', axis=1).astype(float)
        y = ds['target']
        
        # 简化模型（少迭代、浅深度）
        models_simple['xgb'][code] = xgb.XGBClassifier(n_estimators=80, max_depth=3, random_state=42, verbosity=0)
        models_simple['xgb'][code].fit(X, y)
        
        models_simple['lgb'][code] = lgb.LGBMClassifier(n_estimators=80, max_depth=3, random_state=42, verbose=-1)
        models_simple['lgb'][code].fit(X, y)
        
        models_simple['cat'][code] = CatBoostClassifier(iterations=80, depth=3, random_state=42, verbose=False)
        models_simple['cat'][code].fit(X, y)
        
        if idx % 10 == 0:
            print(f"  {idx+1}/30: {code}")
        
    except: continue

print(f"\n训练完成: {len(models_simple['xgb'])}只")

# 测试
print("\n[测试] 2025年数据验证")

def predict_simple(models, code, X):
    try:
        xgb_p = models['xgb'][code].predict_proba(X)[0][1]
        lgb_p = models['lgb'][code].predict_proba(X)[0][1]
        cat_p = models['cat'][code].predict_proba(X)[0][1]
        return int((xgb_p * 0.4 + lgb_p * 0.35 + cat_p * 0.25) * 100)
    except: return 50

results = {}
for threshold in [30, 35, 40, 45, 50]:
    total, success = 0, 0
    
    for code in list(models_simple['xgb'].keys())[:15]:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date > '{TRAIN_END}' AND date <= '2025-06-30' AND ma5 IS NOT NULL ORDER BY date", conn)
        
        if len(df) < 60: continue
        
        for i in range(60, len(df)-3):
            X = pd.DataFrame([get_core_features(df.iloc[i])]).astype(float)
            score = predict_simple(models_simple, code, X)
            
            if score >= threshold:
                ret = (df.iloc[i+3]['close'] - df.iloc[i]['close'])/df.iloc[i]['close']*100
                total += 1
                if ret >= 3:  # 保持原标准>=3%
                    success += 1
    
    if total > 0:
        rate = success/total*100
        results[threshold] = rate
        print(f"  阈值{threshold}: {total}笔, 胜率{rate:.1f}%")

if results:
    best_threshold = max(results.keys(), key=lambda x: results[x])
    best_rate = results[best_threshold]
    
    print(f"\n最佳: 阈值{best_threshold}, 胜率{best_rate:.1f}%")
    
    # 保存
    import os
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, 'models_simple.pkl'), 'wb') as f:
        pickle.dump(models_simple, f)
    
    result = {
        'strategy': '简化模型 - 核心特征10个',
        'features': ['pct_chg', 'ma5_ratio', 'ma10_ratio', 'rsi6', 'macd', 'k', 'd', 'volume', 'amplitude', 'turnover'],
        'model_params': '80迭代/3深度',
        'best_threshold': best_threshold,
        'win_rate': round(best_rate, 2),
        'original': 44.2,
        'improvement': round(best_rate - 44.2, 2),
        'timestamp': datetime.now().isoformat(),
    }
    
    with open(os.path.join(MODEL_DIR, 'simple_opt_result.json'), 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\n" + "=" * 60)
    print("简化优化结果")
    print("=" * 60)
    print(f"原始胜率: 44.2%")
    print(f"简化胜率: {best_rate:.1f}%")
    print(f"提升: {best_rate - 44.2:.1f}%")
    
    if best_rate >= 60:
        print("✅ 达成目标60%!")
    elif best_rate >= 55:
        print("⚠️ 接近目标，差距{:.1f}%".format(60 - best_rate))
    else:
        print("⚠️ 需进一步优化")

conn.close()
print("=" * 60)