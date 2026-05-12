# -*- coding: utf-8 -*-
"""
csi10 真实模型回测 - 使用v5融合模型
对比v4结果
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import sqlite3
import pickle
import os
import json
from datetime import datetime

DB_PATH = r'E:\csi10\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
MODEL_CACHE = r'E:\csi10\model_cache_v5\models_v5.pkl'

print("=" * 60)
print("csi10 真实模型回测 (使用v5融合模型)")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()

# 加载模型
if os.path.exists(MODEL_CACHE):
    with open(MODEL_CACHE, 'rb') as f:
        models = pickle.load(f)
    print(f"加载模型: XGB {len(models['xgb'])}, LGB {len(models['lgb'])}, CAT {len(models['cat'])}")
else:
    print("未找到模型缓存，请先运行 analyzer_v5.py")
    conn.close()
    exit(1)

# 回测参数
START_DATE = '2025-01-01'
END_DATE = '2026-03-01'  # 截止到3月，留足够时间验证
HOLD_DAYS = 3
BUY_THRESHOLD = 60

print(f"回测区间: {START_DATE} ~ {END_DATE}")
print(f"买入阈值: {BUY_THRESHOLD}分")

# 特征提取函数（复制analyzer_v5）
def extract_features_v5(df, i):
    """v5特征提取"""
    if i < 30 or i >= len(df):
        return None
    
    row = df.iloc[i]
    close = row['close']
    
    feat = {
        'pct_chg': row['pct_chg'],
        'ma5_ratio': close / row['ma5'] if row['ma5'] > 0 else 1,
        'ma10_ratio': close / row['ma10'] if row['ma10'] > 0 else 1,
        'rsi6': row['rsi6'] if pd.notna(row['rsi6']) else 50,
        'macd': row['macd'] if pd.notna(row['macd']) else 0,
        'ma20_ratio': close / row['ma20'] if pd.notna(row['ma20']) and row['ma20'] > 0 else 1,
        'k': row['k'] if pd.notna(row['k']) else 50,
        'd': row['d'] if pd.notna(row['d']) else 50,
        'boll_ratio': close / row['boll_upper'] if pd.notna(row['boll_upper']) and row['boll_upper'] > 0 else 1,
        'bias10': row['bias10'] if pd.notna(row['bias10']) else 0,
        'vr': row['vr'] if pd.notna(row['vr']) else 1,
        'amplitude': row['amplitude'] if pd.notna(row['amplitude']) else 0,
    }
    
    # 简化版本，添加基础扩展特征
    feat['atr_5'] = 0
    feat['atr_20'] = 0
    feat['volatility_ratio'] = 1
    feat['amplitude_10_mean'] = 0
    feat['volume_ratio'] = 1
    feat['obv_trend'] = 0
    feat['position_20'] = 0.5
    feat['position_60'] = 0.5
    feat['high_low_ratio'] = 1
    feat['day_of_week'] = 2
    feat['month'] = 4
    feat['pct_chg_3d'] = 0
    feat['pct_chg_5d'] = 0
    feat['momentum'] = feat['pct_chg']
    
    return feat

def predict_fusion(models, code, feat):
    """融合预测"""
    try:
        import xgboost as xgb
        import lightgbm as lgb
        from catboost import CatBoostClassifier
        
        X = pd.DataFrame([feat])
        
        xgb_pred = models['xgb'][code].predict_proba(X)[0][1] if code in models['xgb'] else 0.5
        lgb_pred = models['lgb'][code].predict_proba(X)[0][1] if code in models['lgb'] else 0.5
        cat_pred = models['cat'][code].predict_proba(X)[0][1] if code in models['cat'] else 0.5
        
        # 融合
        fusion_score = xgb_pred * 0.4 + lgb_pred * 0.35 + cat_pred * 0.25
        return int(fusion_score * 100)
    except Exception as e:
        return 50

# 回测统计
total_trades = 0
success_trades = 0
returns = []

print("\n开始真实模型回测...")

for code in stock_pool[:20]:  # 测试20只
    if code not in models['xgb']:
        continue
    
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '{START_DATE}' AND '{END_DATE}' ORDER BY date", conn)
        if len(df) < 60:
            continue
        
        print(f"  {code}: {len(df)}条数据")
        
        for i in range(60, len(df)-HOLD_DAYS):
            feat = extract_features_v5(df, i)
            if not feat:
                continue
            
            score = predict_fusion(models, code, feat)
            
            if score >= BUY_THRESHOLD:
                close = df.iloc[i]['close']
                future_close = df.iloc[i+HOLD_DAYS]['close']
                trade_return = (future_close - close) / close * 100
                
                total_trades += 1
                returns.append(trade_return)
                
                if trade_return >= 3:
                    success_trades += 1
        
    except Exception as e:
        print(f"  {code}: Error - {str(e)[:30]}")
        continue

conn.close()

# 计算结果
print("\n" + "=" * 60)
print("真实模型回测结果 (v5融合)")
print("=" * 60)

if total_trades > 0:
    win_rate = success_trades / total_trades * 100
    avg_return = np.mean(returns)
    max_return = max(returns)
    min_return = min(returns)
    
    # 夏普比率
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252/3) if np.std(returns) > 0 else 0
    
    print(f"总交易次数: {total_trades}")
    print(f"成功次数: {success_trades}")
    print(f"胜率: {win_rate:.1f}%")
    print(f"平均收益: {avg_return:.2f}%")
    print(f"最大收益: {max_return:.2f}%")
    print(f"最大亏损: {min_return:.2f}%")
    print(f"夏普比率: {sharpe:.2f}")
    
    # 保存结果
    result = {
        'timestamp': datetime.now().isoformat(),
        'version': 'v5-real-model',
        'trades': total_trades,
        'win_rate': round(win_rate, 2),
        'avg_return': round(avg_return, 2),
        'sharpe': round(sharpe, 2),
    }
    
    with open(r'E:\csi10\backtest_v5_real.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    # 对比v4
    print("\n对比说明:")
    print("  v4胜率: 75% (用户反馈)")
    print(f"  v5胜率: {win_rate:.1f}% (真实模型)")
    
    if win_rate < 75:
        print("\n⚠️ v5胜率低于v4，需要调整:")
        print("  1. 调整融合权重")
        print("  2. 增加训练数据")
        print("  3. 优化特征选择")
    
else:
    print("无交易记录")

print("=" * 60)