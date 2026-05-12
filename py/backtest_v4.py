# -*- coding: utf-8 -*-
"""
股票模拟交易回测系统 V4 - 修复优化版
修复问题：
1. 止损用次日开盘价（不用当日收盘价）
2. 最优参数配置（买入阈值50-55，止损15%）
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
import json
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# 最优配置（基于参数调优结果）
CONFIG = {
    'BUY_THRESHOLD': 55,       # 买入阈值
    'SELL_THRESHOLD': 15,      # 卖出阈值
    'STOP_LOSS': 0.15,         # 止损15%（调优结果最优）
    'STOP_PROFIT': 0.50,       # 止盈50%（让盈利充分发展）
    'BUY_RATIO': 0.20,
    'TOP_COUNT': 5,
}

print("=" * 80)
print("回测系统 V4 - 最优配置版")
print("=" * 80)
print(f"配置: 买入阈值{CONFIG['BUY_THRESHOLD']}, 止损{CONFIG['STOP_LOSS']*100}%, 止盈{CONFIG['STOP_PROFIT']*100}%")
print("=" * 80)

conn = sqlite3.connect(r'E:\股票\csi500_data\stocks.db')

stock_pool = pd.read_csv(r'e:\csi10\波段股票Top30.csv')['股票代码'].tolist()
stock_data = {}
for code in stock_pool:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
    if len(df) > 0:
        df['date'] = pd.to_datetime(df['date'])
        df = df.reset_index(drop=True)
        stock_data[code] = df

dates_df = pd.read_sql("SELECT DISTINCT date FROM daily_price WHERE date >= '2025-01-01' AND date <= '2026-04-18' ORDER BY date", conn)
trade_dates = pd.to_datetime(dates_df['date']).tolist()
conn.close()

STOCK_NAMES = {
    '688028.SH': '沃尔德', '688195.SH': '芯源微', '688519.SH': '天奈科技',
    '600183.SH': '生益科技', '688416.SH': '恒玄科技', '688521.SH': '芯原股份',
    '300136.SZ': '信维通导', '603225.SH': '新凤鸣', '688388.SH': '嘉元科技',
    '688556.SH': '高测股份', '600118.SH': '中国卫星', '601231.SH': '环旭电子',
    '002202.SZ': '金风科技', '300604.SZ': '长川科技', '603228.SH': '景旺电子',
    '688698.SH': '博众精工', '002460.SZ': '赣锋锂业', '300476.SZ': '胜宏科技',
}

print(f"股票池: {len(stock_data)}只")

# 特征提取
def extract_features(df, i):
    if i < 60:
        return None
    row = df.iloc[i]
    close = row['close']
    feat = {
        'pct_chg': row['pct_chg'],
        'pct_chg_5d': df.iloc[i-5:i]['pct_chg'].sum() if i >= 5 else 0,
        'ma5_ratio': close/row['ma5'] if row['ma5'] > 0 else 1,
        'ma10_ratio': close/row['ma10'] if row['ma10'] > 0 else 1,
        'rsi6': row['rsi6'] if pd.notna(row['rsi6']) else 50,
        'rsi12': row['rsi12'] if pd.notna(row['rsi12']) else 50,
        'macd': row['macd'] if pd.notna(row['macd']) else 0,
        'k': row['k'] if pd.notna(row.get('k', 50)) else 50,
        'd': row['d'] if pd.notna(row.get('d', 50)) else 50,
    }
    if i >= 20:
        closes = df.iloc[i-20:i+1]['close'].values
        returns = np.diff(closes)/closes[:-1]
        feat['volatility'] = np.std(returns) * 100
    else:
        feat['volatility'] = 2
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
        model = xgb.XGBClassifier(n_estimators=200, max_depth=6, random_state=42, verbosity=0)
        model.fit(X, y)
        models[code] = model
    except:
        continue

print(f"已训练: {len(models)}个模型")

# 回测
print("\n开始回测...")
cash = 1000000
holdings = {}
trades = []
daily_values = []
pending_orders = []
stop_loss_count = 0
stop_profit_count = 0

for day_idx, trade_date in enumerate(trade_dates):
    date_str = trade_date.strftime('%Y-%m-%d')
    
    # ========== 第一步：执行昨日pending订单 ==========
    for order in pending_orders:
        if order['action'] == 'buy':
            code = order['code']
            df = stock_data[code]
            day_rows = df[df['date'] == trade_date]
            if len(day_rows) == 0 or cash < 10000:
                continue
            
            buy_price = day_rows.iloc[0].get('open', day_rows.iloc[0]['low'])
            shares = int(cash * CONFIG['BUY_RATIO'] / buy_price)
            if shares > 0:
                cash -= shares * buy_price
                holdings[code] = {'shares': shares, 'buy_price': buy_price, 'buy_date': date_str}
                trades.append({'日期': date_str, '股票': STOCK_NAMES.get(code, code)[:6], '类型': '买入', '价格': buy_price, '数量': shares})
        
        elif order['action'] == 'sell':
            code = order['code']
            if code not in holdings:
                continue
            h = holdings[code]
            df = stock_data[code]
            day_rows = df[df['date'] == trade_date]
            if len(day_rows) == 0:
                continue
            
            sell_price = day_rows.iloc[0].get('open', day_rows.iloc[0]['high'])
            profit_pct = (sell_price - h['buy_price']) / h['buy_price']
            cash += h['shares'] * sell_price
            
            sell_type = order.get('sell_type', '卖出')
            trades.append({
                '日期': date_str, '股票': STOCK_NAMES.get(code, code)[:6],
                '类型': sell_type, '价格': sell_price, '数量': h['shares'],
                '盈亏%': round(profit_pct*100, 2), '持仓天数': (trade_date - pd.to_datetime(h['buy_date'])).days
            })
            
            del holdings[code]
            if sell_type == '止损':
                stop_loss_count += 1
            elif sell_type == '止盈':
                stop_profit_count += 1
    
    pending_orders = []
    
    # ========== 第二步：当日市值 ==========
    holding_value = sum(h['shares'] * stock_data[c][stock_data[c]['date'] == trade_date].iloc[0]['close'] 
                        for c, h in holdings.items() if len(stock_data[c][stock_data[c]['date'] == trade_date]) > 0)
    total_value = cash + holding_value
    daily_values.append({'date': date_str, 'total_value': total_value})
    
    # ========== 第三步：止损止盈检查（用当日收盘价判断，次日执行）==========
    for code, h in holdings.items():
        df = stock_data[code]
        day_rows = df[df['date'] == trade_date]
        if len(day_rows) == 0:
            continue
        
        current_price = day_rows.iloc[0]['close']
        profit_pct = (current_price - h['buy_price']) / h['buy_price']
        
        if profit_pct < -CONFIG['STOP_LOSS']:  # 止损
            pending_orders.append({'code': code, 'action': 'sell', 'sell_type': '止损'})
        elif profit_pct > CONFIG['STOP_PROFIT']:  # 止盈
            pending_orders.append({'code': code, 'action': 'sell', 'sell_type': '止盈'})
    
    # ========== 第四步：当日预测（次日执行）==========
    if day_idx < len(trade_dates) - 1:
        buy_candidates = []
        for code, df in stock_data.items():
            idx_df = df[df['date'] == trade_date].index
            if len(idx_df) == 0 or idx_df[0] < 60 or code not in models:
                continue
            
            feat = extract_features(df, idx_df[0])
            if feat is None:
                continue
            
            try:
                pred = models[code].predict_proba(pd.DataFrame([feat]))[0]
                if pred[1] > CONFIG['BUY_THRESHOLD']/100 and code not in holdings:
                    buy_candidates.append({'code': code, 'score': int(pred[1]*100), 'action': 'buy'})
                elif pred[1] < CONFIG['SELL_THRESHOLD']/100 and code in holdings:
                    pending_orders.append({'code': code, 'action': 'sell', 'sell_type': '预测卖出'})
            except:
                pass
        
        for b in sorted(buy_candidates, key=lambda x: -x['score'])[:CONFIG['TOP_COUNT']]:
            pending_orders.append(b)

# 清算
for code, h in holdings.items():
    df = stock_data[code]
    last = df[df['date'] <= pd.to_datetime('2026-04-18')].tail(1)
    if len(last) > 0:
        sell_price = last.iloc[0]['close']
        cash += h['shares'] * sell_price
        trades.append({'日期': '清算', '股票': STOCK_NAMES.get(code, code)[:6], '价格': sell_price, '盈亏%': round((sell_price-h['buy_price'])/h['buy_price']*100, 2)})

# 统计
print("\n" + "=" * 80)
print("V4 回测结果")
print("=" * 80)

daily_df = pd.DataFrame(daily_values)
total_return = (cash - 1000000) / 1000000 * 100
daily_df['cummax'] = daily_df['total_value'].cummax()
daily_df['drawdown'] = (daily_df['cummax'] - daily_df['total_value']) / daily_df['cummax'] * 100
max_drawdown = daily_df['drawdown'].max()

# 夏普比率
daily_df['return'] = daily_df['total_value'].pct_change()
sharpe = (daily_df['return'].mean() * 252 - 0.03) / (daily_df['return'].std() * np.sqrt(252))

trades_df = pd.DataFrame(trades)
sell_trades = trades_df[trades_df['类型'].isin(['卖出', '止损', '止盈', '清算'])]
win_rate = len(sell_trades[sell_trades['盈亏%'] > 0]) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0

print(f"总收益率: {total_return:.2f}%")
print(f"胜率: {win_rate:.2f}%")
print(f"最大回撤: {max_drawdown:.2f}%")
print(f"夏普比率: {sharpe:.2f}")
print(f"止损触发: {stop_loss_count}次")
print(f"止盈触发: {stop_profit_count}次")
print("=" * 80)

# 输出
result = {
    'total_return': round(total_return, 2),
    'win_rate': round(win_rate, 2),
    'max_drawdown': round(max_drawdown, 2),
    'sharpe': round(sharpe, 2),
    'stop_loss_count': stop_loss_count,
    'stop_profit_count': stop_profit_count,
    'config': CONFIG
}

with open(r'e:\csi10\backtest_v4_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

trades_df.to_excel(r'e:\csi10\backtest_v4_trades.xlsx', index=False)
daily_df.to_excel(r'e:\csi10\backtest_v4_daily.xlsx', index=False)

print("✓ V4回测完成！")