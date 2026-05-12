# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import pandas as pd
import pickle
import numpy as np

DB_PATH = r'E:\csi10\stocks.db'
MODEL_CACHE = r'E:\csi10\model_cache_v5\models_v5.pkl'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

with open(MODEL_CACHE, 'rb') as f:
    models = pickle.load(f)

print("=" * 60)
print("v5模型评分分布测试")
print("=" * 60)

# 测试评分分布
START_DATE = '2026-01-01'
END_DATE = '2026-04-20'

scores_list = []

for code in stock_pool[:5]:  # 先测5只
    if code not in models['xgb']:
        continue
    
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '{START_DATE}' AND '{END_DATE}' AND ma5 IS NOT NULL ORDER BY date", conn)
    
    if len(df) < 10:
        continue
    
    print(f"\n{code}:")
    
    for i in range(10, min(len(df)-3, 20)):
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
            'atr_5': 0, 'atr_20': 0, 'volatility_ratio': 1,
            'amplitude_10_mean': 0, 'volume_ratio': 1, 'obv_trend': 0,
            'position_20': 0.5, 'position_60': 0.5, 'high_low_ratio': 1,
            'day_of_week': 2, 'month': 4, 'pct_chg_3d': 0, 'pct_chg_5d': 0,
            'momentum': row['pct_chg'],
        }
        
        X = pd.DataFrame([feat])
        
        try:
            xgb_p = models['xgb'][code].predict_proba(X)[0][1]
            lgb_p = models['lgb'][code].predict_proba(X)[0][1]
            cat_p = models['cat'][code].predict_proba(X)[0][1]
            
            score = int((xgb_p * 0.4 + lgb_p * 0.35 + cat_p * 0.25) * 100)
            scores_list.append(score)
            
            print(f"  {row['date']}: xgb={xgb_p:.2f} lgb={lgb_p:.2f} cat={cat_p:.2f} -> score={score}")
        except Exception as e:
            print(f"  Error: {str(e)[:30]}")

conn.close()

print("\n" + "=" * 60)
print("评分统计")
print("=" * 60)

if scores_list:
    print(f"样本数: {len(scores_list)}")
    print(f"评分范围: {min(scores_list)} ~ {max(scores_list)}")
    print(f"平均评分: {np.mean(scores_list):.1f}")
    print(f"评分分布: {sorted(scores_list)}")
    
    # 统计各阈值
    for th in [30, 40, 50, 60, 70]:
        count = sum(1 for s in scores_list if s >= th)
        print(f"  >={th}分: {count}个 ({count/len(scores_list)*100:.1f}%)")
    
    # 建议
    avg = np.mean(scores_list)
    if avg < 50:
        print("\n⚠️ 模型评分偏低，可能原因:")
        print("  1. 训练数据不足")
        print("  2. 特征不匹配")
        print("  3. 模型参数需调整")
        print("\n建议: 用阈值40分回测")

print("=" * 60)