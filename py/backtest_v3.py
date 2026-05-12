# -*- coding: utf-8 -*-
"""
股票模拟交易回测系统 V3 - 功能优化版
新增功能：
1. 止损机制（亏损>10%自动卖出）
2. 止盈机制（盈利>25%自动卖出）
3. 参数可配置
4. 夏普比率计算
5. 回撤预警统计
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
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ========== 可配置参数 ==========
CONFIG = {
    'BUY_THRESHOLD': 55,       # 买入阈值（涨幅概率>55%）
    'SELL_THRESHOLD': 15,      # 卖出阈值（涨幅概率<15%）
    'STOP_LOSS': 0.10,         # 止损阈值（亏损>10%）
    'STOP_PROFIT': 0.25,       # 止盈阈值（盈利>25%）
    'BUY_RATIO': 0.20,         # 单笔买入比例（20%资金）
    'TOP_COUNT': 5,            # TOP数量
    'INITIAL_CAPITAL': 1000000,
    'START_DATE': '2025-01-01',
    'END_DATE': '2026-04-18',
}

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
OUTPUT_EXCEL = r'e:\csi10\backtest_v3.xlsx'

STOCK_NAMES = {
    '605196.SH': '华通线缆', '688028.SH': '沃尔德', '688195.SH': '芯源微',
    '688233.SH': '铂力特', '688519.SH': '天奈科技', '002353.SZ': '杰瑞股份',
    '002384.SZ': '东山精密', '600183.SH': '生益科技', '603876.SH': '鼎胜新材',
    '603986.SH': '兆易创新', '688416.SH': '恒玄科技', '688521.SH': '芯原股份',
    '688676.SH': '金迪克', '300136.SZ': '信维通导', '603225.SH': '新凤鸣',
    '688308.SH': '拓荆科技', '688388.SH': '嘉元科技', '688556.SH': '高测股份',
    '600118.SH': '中国卫星', '601231.SH': '环旭电子', '688658.SH': '悦康药业',
    '688668.SH': '鼎通股份', '688788.SH': '科思科技', '002202.SZ': '金风科技',
    '002916.SZ': '深南电路', '300604.SZ': '长川科技', '603228.SH': '景旺电子',
    '688698.SH': '博众精工', '002460.SZ': '赣锋锂业', '300476.SZ': '胜宏科技',
}

print("=" * 80)
print("股票模拟交易回测系统 V3 - 功能优化版")
print("=" * 80)
print("【新增功能】")
print("1. ✅ 止损机制：持仓亏损>10%自动卖出")
print("2. ✅ 止盈机制：持仓盈利>25%自动卖出")
print("3. ✅ 参数可配置")
print("4. ✅ 夏普比率计算")
print("5. ✅ 回撤预警统计")
print("=" * 80)
print(f"当前配置：")
print(f"  买入阈值: {CONFIG['BUY_THRESHOLD']}（涨幅概率>{CONFIG['BUY_THRESHOLD']}%）")
print(f"  卖出阈值: {CONFIG['SELL_THRESHOLD']}（涨幅概率<{CONFIG['SELL_THRESHOLD']}%）")
print(f"  止损阈值: {CONFIG['STOP_LOSS']*100}%（亏损>{CONFIG['STOP_LOSS']*100}%止损）")
print(f"  止盈阈值: {CONFIG['STOP_PROFIT']*100}%（盈利>{CONFIG['STOP_PROFIT']*100}%止盈）")
print(f"  单笔比例: {CONFIG['BUY_RATIO']*100}%")
print(f"  TOP数量: {CONFIG['TOP_COUNT']}")
print("=" * 80)

conn = sqlite3.connect(DB_PATH)

# 加载股票池和数据
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
stock_data = {}
for code in stock_pool:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
    if len(df) > 0:
        df['date'] = pd.to_datetime(df['date'])
        df = df.reset_index(drop=True)
        stock_data[code] = df

dates_df = pd.read_sql(
    "SELECT DISTINCT date FROM daily_price WHERE date >= ? AND date <= ? ORDER BY date",
    conn, params=(CONFIG['START_DATE'], CONFIG['END_DATE'])
)
trade_dates = pd.to_datetime(dates_df['date']).tolist()

conn.close()

print(f"股票池: {len(stock_data)}只")
print(f"回测天数: {len(trade_dates)}天")

# 特征提取
def extract_features(df, i):
    if i < 60:
        return None
    
    row = df.iloc[i]
    close = row['close'] if pd.notna(row['close']) else 0
    volume = row['volume'] if pd.notna(row['volume']) else 0
    pct_chg = row['pct_chg'] if pd.notna(row['pct_chg']) else 0
    high = row['high'] if pd.notna(row['high']) else close
    low = row['low'] if pd.notna(row['low']) else close
    
    ma5 = row['ma5'] if pd.notna(row['ma5']) else close
    ma10 = row['ma10'] if pd.notna(row['ma10']) else close
    ma20 = row['ma20'] if pd.notna(row['ma20']) else close
    ma30 = row['ma30'] if pd.notna(row['ma30']) else close
    
    rsi6 = row['rsi6'] if pd.notna(row['rsi6']) else 50
    rsi12 = row['rsi12'] if pd.notna(row['rsi12']) else 50
    rsi24 = row['rsi24'] if pd.notna(row['rsi24']) else 50
    
    macd = row['macd'] if pd.notna(row['macd']) else 0
    macd_signal = row['macd_signal'] if pd.notna(row['macd_signal']) else 0
    macd_hist = row['macd_hist'] if pd.notna(row.get('macd_hist', 0)) else 0
    
    k = row['k'] if pd.notna(row.get('k', 50)) else 50
    d = row['d'] if pd.notna(row.get('d', 50)) else 50
    
    feat = {
        'pct_chg': pct_chg,
        'pct_chg_5d': df.iloc[i-5:i]['pct_chg'].sum() if i >= 5 else 0,
        'pct_chg_10d': df.iloc[i-10:i]['pct_chg'].sum() if i >= 10 else 0,
        'ma5_ratio': close/ma5 if ma5 > 0 else 1,
        'ma10_ratio': close/ma10 if ma10 > 0 else 1,
        'ma20_ratio': close/ma20 if ma20 > 0 else 1,
        'ma30_ratio': close/ma30 if ma30 > 0 else 1,
        'ma5_ma10_diff': (ma5 - ma10)/ma10 if ma10 > 0 else 0,
        'ma10_ma20_diff': (ma10 - ma20)/ma20 if ma20 > 0 else 0,
        'rsi6': rsi6, 'rsi12': rsi12, 'rsi24': rsi24,
        'rsi_oversold': 1 if rsi6 < 30 else 0,
        'rsi_overbought': 1 if rsi6 > 70 else 0,
        'macd': macd, 'macd_hist': macd_hist, 'macd_signal': macd_signal,
        'macd_cross_up': 1 if macd > macd_signal and macd_hist > 0 else 0,
        'k': k, 'd': d,
        'kdj_cross': 1 if k > d else 0,
        'vol_ratio': volume/df.iloc[i-20:i]['volume'].mean() if i >= 20 else 1,
    }
    
    if i >= 20:
        closes = df.iloc[i-20:i+1]['close'].values
        returns = np.diff(closes)/closes[:-1]
        feat['volatility_20'] = np.std(returns) * 100
    else:
        feat['volatility_20'] = 2
    
    if i >= 60:
        high_60 = df.iloc[i-60:i+1]['close'].max()
        low_60 = df.iloc[i-60:i+1]['close'].min()
        feat['price_position_60'] = (close - low_60)/(high_60 - low_60) if high_60 > low_60 else 0.5
    else:
        feat['price_position_60'] = 0.5
    
    return feat

# 训练模型
print("\n训练模型...")
models = {}

for code, df in stock_data.items():
    if len(df) < 200:
        continue
    
    train_df = df[df['date'] < CONFIG['START_DATE']].tail(500).reset_index(drop=True)
    if len(train_df) < 100:
        continue
    
    features = []
    for i in range(60, len(train_df)-3):
        feat = extract_features(train_df, i)
        if feat:
            close = train_df.iloc[i]['close']
            close_3d = train_df.iloc[i+3]['close']
            rise = (close_3d - close)/close if close > 0 else 0
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
        model = xgb.XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1, verbosity=0)
        model.fit(X, y)
        models[code] = model
    except:
        continue

print(f"已训练: {len(models)}个模型")

# ========== 回测（含止损止盈）==========
print("\n开始回测（含止损止盈）...")

cash = CONFIG['INITIAL_CAPITAL']
holdings = {}
trades = []
daily_values = []
pending_orders = []
stop_loss_triggers = 0
stop_profit_triggers = 0
drawdown_warnings = []

for day_idx, trade_date in enumerate(trade_dates):
    date_str = trade_date.strftime('%Y-%m-%d')
    
    # 执行pending订单
    for order in pending_orders:
        if order['action'] == 'buy':
            code = order['code']
            df = stock_data[code]
            day_rows = df[df['date'] == trade_date]
            if len(day_rows) == 0:
                continue
            
            buy_price = day_rows.iloc[0].get('open', day_rows.iloc[0]['low'])
            buy_amount = min(cash * CONFIG['BUY_RATIO'], cash)
            shares = int(buy_amount / buy_price)
            
            if shares > 0 and cash >= shares * buy_price:
                cash -= shares * buy_price
                holdings[code] = {
                    'shares': shares, 
                    'buy_price': buy_price, 
                    'buy_date': date_str,
                    'buy_reason': order.get('reason', '预测买入')
                }
                
                trades.append({
                    '日期': date_str, '股票': STOCK_NAMES.get(code, code), 
                    '类型': '买入', '价格': buy_price, '数量': shares,
                    '金额': shares*buy_price, '原因': order.get('reason', '预测买入')
                })
        
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
            
            trades.append({
                '日期': date_str, '股票': STOCK_NAMES.get(code, code),
                '类型': order.get('sell_type', '卖出'), '价格': sell_price,
                '数量': h['shares'], '金额': h['shares']*sell_price,
                '盈亏': round((sell_price-h['buy_price'])*h['shares'], 2),
                '盈亏%': round(profit_pct*100, 2),
                '持仓天数': (trade_date - pd.to_datetime(h['buy_date'])).days,
                '原因': order.get('reason', '预测卖出')
            })
            
            del holdings[code]
            
            if order.get('sell_type') == '止损':
                stop_loss_triggers += 1
            elif order.get('sell_type') == '止盈':
                stop_profit_triggers += 1
    
    pending_orders = []
    
    # 计算当日市值
    holding_value = 0
    for code, h in holdings.items():
        df = stock_data[code]
        day_rows = df[df['date'] == trade_date]
        if len(day_rows) > 0:
            price = day_rows.iloc[0]['close']
            holding_value += h['shares'] * price
    
    total_value = cash + holding_value
    
    # 回撤预警
    if len(daily_values) > 0:
        peak = max([d['total_value'] for d in daily_values])
        drawdown = (peak - total_value) / peak * 100
        if drawdown > 30:
            drawdown_warnings.append({'date': date_str, 'drawdown': drawdown})
    
    daily_values.append({
        'date': date_str, 'cash': cash, 'holding_value': holding_value,
        'total_value': total_value, 'holdings_count': len(holdings)
    })
    
    # ========== 止损止盈检查 ==========
    for code, h in holdings.items():
        df = stock_data[code]
        day_rows = df[df['date'] == trade_date]
        if len(day_rows) == 0:
            continue
        
        current_price = day_rows.iloc[0]['close']
        profit_pct = (current_price - h['buy_price']) / h['buy_price']
        
        # 止损：亏损>10%
        if profit_pct < -CONFIG['STOP_LOSS']:
            pending_orders.append({
                'code': code, 'action': 'sell', 
                'sell_type': '止损',
                'reason': f'亏损{profit_pct*100:.1f}%触发止损'
            })
        
        # 止盈：盈利>25%
        elif profit_pct > CONFIG['STOP_PROFIT']:
            pending_orders.append({
                'code': code, 'action': 'sell',
                'sell_type': '止盈',
                'reason': f'盈利{profit_pct*100:.1f}%触发止盈'
            })
    
    # 当日预测
    if day_idx < len(trade_dates) - 1:
        buy_candidates = []
        
        for code, df in stock_data.items():
            idx_df = df[df['date'] == trade_date].index
            if len(idx_df) == 0 or idx_df[0] < 60:
                continue
            
            feat = extract_features(df, idx_df[0])
            if feat is None or code not in models:
                continue
            
            try:
                pred = models[code].predict_proba(pd.DataFrame([feat]))[0]
                
                # 买入信号
                if pred[1] > CONFIG['BUY_THRESHOLD']/100 and code not in holdings:
                    buy_candidates.append({
                        'code': code, 'score': int(pred[1]*100),
                        'action': 'buy', 'reason': f'预测评分{int(pred[1]*100)}'
                    })
                
                # 卖出信号（模型预测）
                elif pred[1] < CONFIG['SELL_THRESHOLD']/100 and code in holdings:
                    pending_orders.append({
                        'code': code, 'action': 'sell',
                        'sell_type': '预测卖出',
                        'reason': f'预测跌幅概率{int((1-pred[1])*100)}%'
                    })
            except:
                continue
        
        # TOP5买入
        for b in sorted(buy_candidates, key=lambda x: -x['score'])[:CONFIG['TOP_COUNT']]:
            pending_orders.append(b)

# 清算
for code, h in holdings.items():
    df = stock_data[code]
    last = df[df['date'] <= pd.to_datetime(CONFIG['END_DATE'])].tail(1)
    if len(last) > 0:
        sell_price = last.iloc[0]['close']
        cash += h['shares'] * sell_price
        
        trades.append({
            '日期': last.iloc[0]['date'].strftime('%Y-%m-%d'),
            '股票': STOCK_NAMES.get(code, code), '类型': '清算',
            '价格': sell_price, '数量': h['shares'],
            '盈亏': round((sell_price-h['buy_price'])*h['shares'], 2),
            '盈亏%': round((sell_price-h['buy_price'])/h['buy_price']*100, 2)
        })

# ========== 统计结果 ==========
print("\n" + "=" * 80)
print("V3 回测结果（含止损止盈）")
print("=" * 80)

daily_df = pd.DataFrame(daily_values)
trades_df = pd.DataFrame(trades)

total_return = (cash - CONFIG['INITIAL_CAPITAL']) / CONFIG['INITIAL_CAPITAL'] * 100
sell_trades = trades_df[trades_df['类型'].isin(['卖出', '止损', '止盈', '清算'])]

win_trades = sell_trades[sell_trades['盈亏'] > 0]
win_rate = len(win_trades) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0

# 最大回撤
daily_df['cummax'] = daily_df['total_value'].cummax()
daily_df['drawdown'] = (daily_df['cummax'] - daily_df['total_value']) / daily_df['cummax'] * 100
max_drawdown = daily_df['drawdown'].max()

# 夏普比率
daily_df['return'] = daily_df['total_value'].pct_change()
sharpe = (daily_df['return'].mean() * 252 - 0.03) / (daily_df['return'].std() * np.sqrt(252))

print(f"总收益率: {total_return:.2f}%")
print(f"胜率: {win_rate:.2f}%")
print(f"最大回撤: {max_drawdown:.2f}%")
print(f"夏普比率: {sharpe:.2f}")
print(f"止损触发: {stop_loss_triggers}次")
print(f"止盈触发: {stop_profit_triggers}次")
print(f"回撤预警: {len(drawdown_warnings)}次（>30%）")

# 输出Excel
with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
    # 概览
    summary = pd.DataFrame([
        {'项目': '总收益率', '数值': f'{total_return:.2f}%'},
        {'项目': '胜率', '数值': f'{win_rate:.2f}%'},
        {'项目': '最大回撤', '数值': f'{max_drawdown:.2f}%'},
        {'项目': '夏普比率', '数值': f'{sharpe:.2f}'},
        {'项目': '止损触发次数', '数值': stop_loss_triggers},
        {'项目': '止盈触发次数', '数值': stop_profit_triggers},
        {'项目': '', '数值': ''},
        {'项目': '---配置参数---', '数值': ''},
        {'项目': '买入阈值', '数值': CONFIG['BUY_THRESHOLD']},
        {'项目': '止损阈值', '数值': f'{CONFIG["STOP_LOSS"]*100}%'},
        {'项目': '止盈阈值', '数值': f'{CONFIG["STOP_PROFIT"]*100}%'},
    ])
    summary.to_excel(writer, sheet_name='概览', index=False)
    
    trades_df.to_excel(writer, sheet_name='交易记录', index=False)
    daily_df.to_excel(writer, sheet_name='每日净值', index=False)

print(f"\n✓ Excel已生成: {OUTPUT_EXCEL}")

# 保存结果
result = {
    'total_return': total_return,
    'win_rate': win_rate,
    'max_drawdown': max_drawdown,
    'sharpe': sharpe,
    'stop_loss_count': stop_loss_triggers,
    'stop_profit_count': stop_profit_triggers,
    'config': CONFIG
}

with open(r'e:\csi10\backtest_v3_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("✓ V3回测完成！")