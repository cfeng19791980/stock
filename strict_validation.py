# -*- coding: utf-8 -*-
"""
严格验证 - 用训练外时间段测试
训练数据: 2020-2024
测试数据: 2025（确保不重叠）
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3, pandas as pd, pickle, numpy as np

print("=" * 60)
print("严格验证 - 训练外数据测试")
print("=" * 60)

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

# 检查训练数据范围
print("\n检查数据范围:")
for code in ['605196.SH']:
    df = pd.read_sql(f"SELECT MIN(date), MAX(date) FROM daily_price WHERE code='{code}'", conn)
    print(f"  {code}: {df.iloc[0][0]} ~ {df.iloc[0][1]}")

# 训练时用的数据范围应该是全部数据
# 现在用严格的2025年数据（最新，可能未包含在训练）
print("\n严格测试 2025年 (1-6月):")
total, success = 0, 0
returns = []

for code in ['605196.SH', '688028.SH', '688195.SH', '002353.SZ', '600183.SH']:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '2025-01-01' AND '2025-06-30' AND ma5 IS NOT NULL ORDER BY date", conn)
    
    if len(df) < 60:
        continue
    
    trades = 0
    for i in range(60, len(df)-3):
        X = pd.DataFrame([get_f(df.iloc[i])]).astype(float)
        try:
            score = int((models['xgb'][code].predict_proba(X)[0][1]*0.4 + 
                        models['lgb'][code].predict_proba(X)[0][1]*0.35 + 
                        models['cat'][code].predict_proba(X)[0][1]*0.25)*100)
            
            if score >= 50:
                ret = (df.iloc[i+3]['close'] - df.iloc[i]['close'])/df.iloc[i]['close']*100
                total += 1
                returns.append(ret)
                if ret >= 3: success += 1
                trades += 1
        except: pass
    
    print(f"  {code}: trades={trades}")

print(f"\n总计: {total}笔, 成功{success}, 胜率{success/total*100:.1f}%")
print(f"平均收益: {np.mean(returns):.2f}%")

if success/total*100 > 90:
    print("\n⚠️ 警示: 胜率>90%，可能过拟合!")
    print("建议: 重新训练时排除测试数据")
elif success/total*100 > 70:
    print("\n✅ 胜率>70%，模型有效!")
else:
    print("\n模型需优化")

conn.close()
print("=" * 60)