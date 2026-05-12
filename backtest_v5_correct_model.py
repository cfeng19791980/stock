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
MODEL_CACHE = r'E:\csi10\model_cache_v5_correct\models_v5_correct.pkl'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

print("=" * 60)
print("v5正确模型历史回测")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

with open(MODEL_CACHE, 'rb') as f:
    models = pickle.load(f)

print(f"模型: XGB {len(models['xgb'])}只")

START_DATE = '2025-01-01'
END_DATE = '2026-03-20'
HOLD_DAYS = 3
BUY_THRESHOLD = 40  # 降低阈值测试

print(f"回测: {START_DATE} ~ {END_DATE}")
print(f"阈值: {BUY_THRESHOLD}分")

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

total = 0
success = 0
returns = []

print("进度:")
for idx, code in enumerate(stock_pool):
    if code not in models['xgb']:
        continue
    
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '{START_DATE}' AND '{END_DATE}' AND ma5 IS NOT NULL ORDER BY date", conn)
    
    if len(df) < 60:
        continue
    
    trades = 0
    for i in range(60, len(df)-HOLD_DAYS):
        row = df.iloc[i]
        close = row['close']
        feat = get_features(row, close)
        X = pd.DataFrame([feat]).astype(float)
        
        try:
            xgb_p = models['xgb'][code].predict_proba(X)[0][1]
            lgb_p = models['lgb'][code].predict_proba(X)[0][1]
            cat_p = models['cat'][code].predict_proba(X)[0][1]
            
            score = int((xgb_p * 0.4 + lgb_p * 0.35 + cat_p * 0.25) * 100)
            
            if score >= BUY_THRESHOLD:
                future = df.iloc[i+HOLD_DAYS]['close']
                ret = (future - close) / close * 100
                
                total += 1
                returns.append(ret)
                if ret >= 3:
                    success += 1
                trades += 1
        except:
            continue
    
    if trades > 0:
        print(f"  {idx+1}/30 {code}: {trades} trades")

conn.close()

print("\n" + "=" * 60)
print("回测结果")
print("=" * 60)

if total > 0:
    win_rate = success / total * 100
    avg_ret = np.mean(returns)
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(84) if np.std(returns) > 0 else 0
    
    print(f"总交易: {total}")
    print(f"成功: {success}")
    print(f"胜率: {win_rate:.1f}%")
    print(f"平均收益: {avg_ret:.2f}%")
    print(f"夏普: {sharpe:.2f}")
    
    print(f"\n对比:")
    print(f"  v4胜率: 75%")
    print(f"  v5胜率: {win_rate:.1f}%")
    
    # 保存
    result = {
        'timestamp': datetime.now().isoformat(),
        'threshold': BUY_THRESHOLD,
        'trades': total,
        'win_rate': round(win_rate, 2),
        'avg_return': round(avg_ret, 2),
        'sharpe': round(sharpe, 2),
        'v4_win_rate': 75,
    }
    
    with open(r'E:\csi10\backtest_v5_correct_result.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    # 分析
    if win_rate < 75:
        gap = 75 - win_rate
        print(f"\n差距: {gap:.1f}%")
        print("可能原因:")
        print("  1. 训练目标(涨幅>=3%)较严格")
        print("  2. 融合权重需优化")
        print("  3. 特征数量不足")
        
        # 尝试不同阈值
        print("\n建议: 测试阈值30分")
    else:
        print("✅ v5胜率达标!")

else:
    print("无交易记录")
    print(f"建议: 进一步降低阈值到30分")

print("=" * 60)