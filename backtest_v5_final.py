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
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

print("=" * 60)
print("csi10 v5真实模型回测 (修正版)")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

# 加载模型
with open(MODEL_CACHE, 'rb') as f:
    models = pickle.load(f)
print(f"模型: XGB {len(models['xgb'])}只")

# 使用有完整指标的时间范围
START_DATE = '2025-01-01'
END_DATE = '2026-04-20'
HOLD_DAYS = 3
BUY_THRESHOLD = 60

print(f"回测: {START_DATE} ~ {END_DATE}")
print(f"阈值: {BUY_THRESHOLD}分")

# 特征提取
def get_features(row, close):
    return {
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

# 回测
total = 0
success = 0
returns = []

print("\n进度:")
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
        X = pd.DataFrame([feat])
        
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
        print(f"  {idx+1}/{len(stock_pool)} {code}: trades={trades}")

conn.close()

print("\n" + "=" * 60)
print("v5真实模型回测结果")
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
    
    # 对比
    print(f"\n【对比】")
    print(f"  v4胜率: 75%")
    print(f"  v5胜率: {win_rate:.1f}%")
    
    if win_rate < 75:
        print(f"\n⚠️ v5低于v4，差距{75-win_rate:.1f}%")
        print("原因分析:")
        print("  1. 模型融合权重可能需调整")
        print("  2. 买入阈值60可能太高")
        print("  3. 需更多训练数据验证")
        
        # 尝试降低阈值
        print("\n建议: 降低买入阈值到50分重测")
    
    # 保存
    json.dump({
        'win_rate': round(win_rate, 2),
        'trades': total,
        'avg_return': round(avg_ret, 2),
        'v4_win_rate': 75
    }, open(r'E:\csi10\backtest_v5_final.json', 'w'))
    
else:
    print("无交易 - 模型评分均低于阈值")
    print("建议降低阈值到50分测试")

print("=" * 60)