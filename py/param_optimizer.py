# -*- coding: utf-8 -*-
"""
参数调优面板 - 测试不同止损/止盈配置
"""

import sys
import io
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except:
    pass

import pandas as pd
import numpy as np
import sqlite3
import xgboost as xgb
import json
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("参数调优面板 - 测试最优配置")
print("=" * 80)

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

conn = sqlite3.connect(DB_PATH)

stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
stock_data = {}
for code in stock_pool:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
    if len(df) > 0:
        df['date'] = pd.to_datetime(df['date'])
        df = df.reset_index(drop=True)
        stock_data[code] = df

dates_df = pd.read_sql(
    "SELECT DISTINCT date FROM daily_price WHERE date >= '2025-01-01' AND date <= '2026-04-18' ORDER BY date", conn
)
trade_dates = pd.to_datetime(dates_df['date']).tolist()
conn.close()

# 特征提取（简化）
def extract_features(df, i):
    if i < 60:
        return None
    row = df.iloc[i]
    close = row['close']
    feat = {
        'pct_chg': row['pct_chg'],
        'ma5_ratio': close/row['ma5'] if row['ma5'] > 0 else 1,
        'rsi6': row['rsi6'] if pd.notna(row['rsi6']) else 50,
        'macd': row['macd'] if pd.notna(row['macd']) else 0,
    }
    return feat

# 训练模型
print("\n训练模型...")
models = {}
for code, df in stock_data.items():
    if len(df) < 200:
        continue
    train_df = df[df['date'] < '2025-01-01'].tail(500).reset_index(drop=True)
    if len(train_df) < 100:
        continue
    features = []
    for i in range(60, len(train_df)-3):
        feat = extract_features(train_df, i)
        if feat:
            rise = (train_df.iloc[i+3]['close'] - train_df.iloc[i]['close'])/train_df.iloc[i]['close']
            feat['target'] = 1 if rise >= 0.03 else 0
            features.append(feat)
    if len(features) < 30:
        continue
    ds = pd.DataFrame(features)
    X = ds.drop('target', axis=1)
    y = ds['target']
    if len(y[y==1]) < 2 or len(y[y==0]) < 2:
        continue
    try:
        model = xgb.XGBClassifier(n_estimators=100, max_depth=4, random_state=42, verbosity=0)
        model.fit(X, y)
        models[code] = model
    except:
        continue

print(f"已训练: {len(models)}个模型")

# 回测函数
def backtest(config):
    cash = 1000000
    holdings = {}
    pending = []
    
    for day_idx, trade_date in enumerate(trade_dates[:-1]):
        # 执行订单
        for order in pending:
            if order['action'] == 'buy':
                code = order['code']
                df = stock_data[code]
                day_rows = df[df['date'] == trade_dates[day_idx]]
                if len(day_rows) > 0 and cash > 0:
                    buy_price = day_rows.iloc[0].get('open', day_rows.iloc[0]['low'])
                    shares = int(cash * config['buy_ratio'] / buy_price)
                    if shares > 0:
                        cash -= shares * buy_price
                        holdings[code] = {'shares': shares, 'buy_price': buy_price}
            elif order['action'] == 'sell' and order['code'] in holdings:
                h = holdings[order['code']]
                df = stock_data[order['code']]
                day_rows = df[df['date'] == trade_dates[day_idx]]
                if len(day_rows) > 0:
                    sell_price = day_rows.iloc[0].get('open', day_rows.iloc[0]['high'])
                    cash += h['shares'] * sell_price
                    del holdings[order['code']]
        pending = []
        
        # 止损止盈检查
        for code, h in holdings.items():
            df = stock_data[code]
            day_rows = df[df['date'] == trade_date]
            if len(day_rows) > 0:
                current_price = day_rows.iloc[0]['close']
                profit_pct = (current_price - h['buy_price']) / h['buy_price']
                if profit_pct < -config['stop_loss']:
                    pending.append({'code': code, 'action': 'sell'})
                elif profit_pct > config['stop_profit']:
                    pending.append({'code': code, 'action': 'sell'})
        
        # 预测
        buy_candidates = []
        for code, df in stock_data.items():
            idx_df = df[df['date'] == trade_date].index
            if len(idx_df) > 0 and idx_df[0] >= 60 and code in models:
                feat = extract_features(df, idx_df[0])
                if feat:
                    try:
                        pred = models[code].predict_proba(pd.DataFrame([feat]))[0]
                        if pred[1] > config['buy_threshold']/100 and code not in holdings:
                            buy_candidates.append({'code': code, 'score': int(pred[1]*100), 'action': 'buy'})
                        elif pred[1] < config['sell_threshold']/100 and code in holdings:
                            pending.append({'code': code, 'action': 'sell'})
                    except:
                        pass
        
        for b in sorted(buy_candidates, key=lambda x: -x['score'])[:config['top_count']]:
            pending.append(b)
    
    # 清算
    for code, h in holdings.items():
        df = stock_data[code]
        last = df[df['date'] <= pd.to_datetime('2026-04-18')].tail(1)
        if len(last) > 0:
            cash += h['shares'] * last.iloc[0]['close']
    
    return (cash - 1000000) / 1000000 * 100

# 测试不同配置
print("\n测试不同配置组合...")

configs = [
    {'name': '无止损止盈', 'buy_threshold': 55, 'sell_threshold': 15, 'stop_loss': 1.0, 'stop_profit': 1.0, 'buy_ratio': 0.2, 'top_count': 5},
    {'name': '止损5%', 'buy_threshold': 55, 'sell_threshold': 15, 'stop_loss': 0.05, 'stop_profit': 1.0, 'buy_ratio': 0.2, 'top_count': 5},
    {'name': '止损10%', 'buy_threshold': 55, 'sell_threshold': 15, 'stop_loss': 0.10, 'stop_profit': 1.0, 'buy_ratio': 0.2, 'top_count': 5},
    {'name': '止损15%', 'buy_threshold': 55, 'sell_threshold': 15, 'stop_loss': 0.15, 'stop_profit': 1.0, 'buy_ratio': 0.2, 'top_count': 5},
    {'name': '止损10%+止盈30%', 'buy_threshold': 55, 'sell_threshold': 15, 'stop_loss': 0.10, 'stop_profit': 0.30, 'buy_ratio': 0.2, 'top_count': 5},
    {'name': '止损5%+止盈20%', 'buy_threshold': 55, 'sell_threshold': 15, 'stop_loss': 0.05, 'stop_profit': 0.20, 'buy_ratio': 0.2, 'top_count': 5},
    {'name': '止损8%+止盈25%', 'buy_threshold': 55, 'sell_threshold': 15, 'stop_loss': 0.08, 'stop_profit': 0.25, 'buy_ratio': 0.2, 'top_count': 5},
    {'name': '阈值50+止损8%', 'buy_threshold': 50, 'sell_threshold': 15, 'stop_loss': 0.08, 'stop_profit': 0.30, 'buy_ratio': 0.2, 'top_count': 5},
    {'name': '阈值50+止损5%', 'buy_threshold': 50, 'sell_threshold': 15, 'stop_loss': 0.05, 'stop_profit': 0.30, 'buy_ratio': 0.2, 'top_count': 5},
    {'name': '阈值60+止损8%', 'buy_threshold': 60, 'sell_threshold': 15, 'stop_loss': 0.08, 'stop_profit': 0.30, 'buy_ratio': 0.2, 'top_count': 5},
]

results = []
for cfg in configs:
    ret = backtest(cfg)
    results.append({'配置': cfg['name'], '收益率': round(ret, 2)})
    print(f"  {cfg['name']}: {ret:.2f}%")

# 找最优
best = max(results, key=lambda x: x['收益率'])
print("\n" + "=" * 80)
print(f"最优配置: {best['配置']}（收益率{best['收益率']}%）")
print("=" * 80)

# 保存结果
results_df = pd.DataFrame(results)
results_df.to_excel(r'e:\csi10\参数调优结果.xlsx', index=False)

with open(r'e:\csi10\参数调优结果.json', 'w', encoding='utf-8') as f:
    json.dump({'results': results, 'best': best}, f, ensure_ascii=False, indent=2)

print("✓ 参数调优完成！结果已保存")