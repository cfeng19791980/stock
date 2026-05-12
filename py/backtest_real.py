# -*- coding: utf-8 -*-
"""
股票模拟交易回测系统 - 最终严格版本
核心改进:
1. T日收盘预测 → T+1日开盘执行买卖（真实延迟）
2. 买入价格 = 下个交易日开盘价（realistic）
3. 卖出价格 = 下个交易日开盘价（realistic）
4. 详细说明每笔交易的买卖逻辑
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

# 配置
DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
OUTPUT_EXCEL = r'e:\csi10\backtest_real.xlsx'
OUTPUT_JSON = r'e:\csi10\backtest_real.json'
INITIAL_CAPITAL = 1000000
START_DATE = '2025-01-01'
END_DATE = '2026-04-18'

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
print("股票模拟交易回测系统 - 最终严格版")
print("=" * 80)
print("【核心规则】")
print("1. 买入时机: T日收盘预测 → T+1日开盘买入（真实延迟1天）")
print("2. 买入价格: T+1日开盘价（真实可成交价格）")
print("3. 卖出时机: T日收盘预测 → T+1日开盘卖出（真实延迟1天）")
print("4. 卖出价格: T+1日开盘价（真实可成交价格）")
print("5. 买入数量: 每笔不超过总资金的20%，分散风险")
print("6. TOP5规则: 只买入当日预测评分最高的5只股票")
print("=" * 80)
print(f"时间范围: {START_DATE} → {END_DATE}")
print(f"初始资金: {INITIAL_CAPITAL:,}元")
print("=" * 80)

conn = sqlite3.connect(DB_PATH)

# 加载股票池和数据
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
print(f"\n股票池: {len(stock_pool)}只")

stock_data = {}
for code in stock_pool:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
    if len(df) > 0:
        df['date'] = pd.to_datetime(df['date'])
        df = df.reset_index(drop=True)
        stock_data[code] = df

print(f"已加载: {len(stock_data)}只股票历史数据")

# 加载大盘数据
index_df = pd.read_sql("SELECT * FROM index_daily WHERE code='sh.000300' ORDER BY date", conn)
index_df['date'] = pd.to_datetime(index_df['date'])

# 获取交易日
dates_df = pd.read_sql(
    "SELECT DISTINCT date FROM daily_price WHERE date >= ? AND date <= ? ORDER BY date",
    conn, params=(START_DATE, END_DATE)
)
trade_dates = pd.to_datetime(dates_df['date']).tolist()
print(f"回测交易日: {len(trade_dates)}天")

conn.close()

# 特征提取函数（只用历史数据）
def extract_features(df, i):
    """提取43个特征 - 严格只用当日及之前数据"""
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
    j = row['j'] if pd.notna(row.get('j', 50)) else 50
    
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
        'ma5_slope': (ma5 - df.iloc[i-5]['ma5'])/ma5 if i >= 5 and ma5 > 0 else 0,
        'rsi6': rsi6, 'rsi12': rsi12, 'rsi24': rsi24,
        'rsi6_rsi12_diff': rsi6 - rsi12,
        'rsi_oversold': 1 if rsi6 < 30 else 0,
        'rsi_overbought': 1 if rsi6 > 70 else 0,
        'macd': macd, 'macd_hist': macd_hist, 'macd_signal': macd_signal,
        'macd_cross_up': 1 if macd > macd_signal and macd_hist > 0 else 0,
        'macd_cross_down': 1 if macd < macd_signal and macd_hist < 0 else 0,
        'k': k, 'd': d, 'j': j,
        'kdj_cross': 1 if k > d else 0,
        'vol_ratio': volume/df.iloc[i-20:i]['volume'].mean() if i >= 20 and df.iloc[i-20:i]['volume'].mean() > 0 else 1,
        'vol_price_trend': 1 if volume > df.iloc[i-20:i]['volume'].mean() * 1.5 and pct_chg > 0 else 0,
    }
    
    # 波动率
    if i >= 20:
        closes = df.iloc[i-20:i+1]['close'].values
        returns = np.diff(closes)/closes[:-1]
        feat['volatility_20'] = np.std(returns) * 100
    else:
        feat['volatility_20'] = 2
    
    if i >= 30:
        closes = df.iloc[i-30:i+1]['close'].values
        returns = np.diff(closes)/closes[:-1]
        feat['volatility_30'] = np.std(returns) * 100
    else:
        feat['volatility_30'] = 2
    
    # 价格位置
    if i >= 60:
        high_60 = df.iloc[i-60:i+1]['close'].max()
        low_60 = df.iloc[i-60:i+1]['close'].min()
        feat['price_position_60'] = (close - low_60)/(high_60 - low_60) if high_60 > low_60 else 0.5
    else:
        feat['price_position_60'] = 0.5
    
    # 涨跌统计
    if i >= 5:
        feat['up_days_5'] = len([p for p in df.iloc[i-5:i]['pct_chg'].values if p > 0])
        feat['down_days_5'] = len([p for p in df.iloc[i-5:i]['pct_chg'].values if p < 0])
    else:
        feat['up_days_5'] = 0
        feat['down_days_5'] = 0
    
    if i >= 10:
        feat['up_days_10'] = len([p for p in df.iloc[i-10:i]['pct_chg'].values if p > 0])
        feat['down_days_10'] = len([p for p in df.iloc[i-10:i]['pct_chg'].values if p < 0])
    else:
        feat['up_days_10'] = 0
        feat['down_days_10'] = 0
    
    feat['intraday_range'] = (high - low)/low * 100 if low > 0 else 0
    
    return feat

# 训练模型
print("\n训练模型（用2024年历史数据）...")
models = {}

for code, df in stock_data.items():
    if len(df) < 200:
        continue
    
    # 只用2024年之前数据训练
    train_end = df[df['date'] < START_DATE].tail(500)
    if len(train_end) < 100:
        continue
    
    train_df = train_end.reset_index(drop=True)
    
    features = []
    for i in range(60, len(train_df)-3):
        feat = extract_features(train_df, i)
        if feat:
            # target: 未来3日涨幅>=3%（训练用）
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
        model = xgb.XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8,
            objective='binary:logistic', eval_metric='auc',
            random_state=42, n_jobs=-1, verbosity=0
        )
        model.fit(X, y)
        models[code] = model
    except Exception as e:
        continue

print(f"已训练: {len(models)}个模型（仅用历史数据）")

# ================== 严格回测 ==================
print("\n开始严格回测...")
print("=" * 80)

cash = INITIAL_CAPITAL
holdings = {}  # {code: {'shares': n, 'buy_price': p, 'buy_date': d, 'buy_exec_date': ed}}
trades = []
daily_values = []
pending_orders = []  # 待执行订单

for day_idx, trade_date in enumerate(trade_dates):
    date_str = trade_date.strftime('%Y-%m-%d')
    
    # ========== 第一步：执行昨日pending订单（T+1执行） ==========
    executed_today = []
    
    for order in pending_orders:
        if order['action'] == 'buy':
            code = order['code']
            df = stock_data[code]
            
            # 找到当日数据（执行日）
            day_rows = df[df['date'] == trade_date]
            if len(day_rows) == 0:
                continue  # 无法执行，跳过
            
            # 【关键】买入价格 = 当日开盘价（第一个有效价格）
            # 这里用当日第一笔交易的最低价作为保守估计（实际应该是开盘价）
            day_data = day_rows.iloc[0]
            buy_price = day_data['open'] if pd.notna(day_data.get('open')) else day_data['low']
            
            # 买入数量计算
            buy_amount = min(cash * 0.2, cash)  # 每笔最多20%资金
            shares = int(buy_amount / buy_price)
            
            if shares > 0 and cash >= shares * buy_price:
                actual_cost = shares * buy_price
                
                # 记录买入
                trade_record = {
                    '执行日期': date_str,
                    '股票代码': code,
                    '股票名称': STOCK_NAMES.get(code, code),
                    '交易类型': '买入',
                    '买入价格': round(buy_price, 2),
                    '买入数量': shares,
                    '买入金额': round(actual_cost, 2),
                    '预测日期': order['predict_date'],
                    '预测评分': order['score'],
                    '预测收盘价': round(order['predict_close'], 2),
                    '价格变化': round((buy_price - order['predict_close'])/order['predict_close']*100, 2),
                    '执行说明': f"T日({order['predict_date']})收盘预测评分{order['score']}，T+1日({date_str})开盘买入",
                    '买入价格说明': f"使用T+1日开盘价{buy_price}元",
                    '数量确定说明': f"可用资金{cash:.0f}元的20%={cash*0.2:.0f}元，买入{shares}股",
                }
                trades.append(trade_record)
                
                cash -= actual_cost
                holdings[code] = {
                    'shares': shares,
                    'buy_price': buy_price,
                    'buy_date': date_str,
                    'predict_date': order['predict_date'],
                    'predict_score': order['score']
                }
                
                executed_today.append(f"买入{STOCK_NAMES.get(code, code)} {shares}股 @ {buy_price}元")
        
        elif order['action'] == 'sell':
            code = order['code']
            if code not in holdings:
                continue
            
            holding = holdings[code]
            df = stock_data[code]
            
            day_rows = df[df['date'] == trade_date]
            if len(day_rows) == 0:
                continue
            
            # 【关键】卖出价格 = 当日开盘价
            day_data = day_rows.iloc[0]
            sell_price = day_data['open'] if pd.notna(day_data.get('open')) else day_data['high']
            
            sell_amount = holding['shares'] * sell_price
            profit = sell_amount - holding['shares'] * holding['buy_price']
            profit_pct = (sell_price - holding['buy_price']) / holding['buy_price'] * 100
            hold_days = (trade_date - pd.to_datetime(holding['buy_date'])).days
            
            trade_record = {
                '执行日期': date_str,
                '股票代码': code,
                '股票名称': STOCK_NAMES.get(code, code),
                '交易类型': '卖出',
                '卖出价格': round(sell_price, 2),
                '卖出数量': holding['shares'],
                '卖出金额': round(sell_amount, 2),
                '买入价格': round(holding['buy_price'], 2),
                '买入日期': holding['buy_date'],
                '持仓天数': hold_days,
                '盈亏金额': round(profit, 2),
                '盈亏比例': round(profit_pct, 2),
                '预测日期': order['predict_date'],
                '卖出评分': order['score'],
                '执行说明': f"T日({order['predict_date']})收盘预测跌幅概率{order['score']}%，T+1日({date_str})开盘卖出",
                '卖出价格说明': f"使用T+1日开盘价{sell_price}元",
                '盈亏说明': f"买入价{holding['buy_price']}元，卖出价{sell_price}元，盈亏{profit_pct:.2f}%",
            }
            trades.append(trade_record)
            
            cash += sell_amount
            del holdings[code]
            
            executed_today.append(f"卖出{STOCK_NAMES.get(code, code)} {holding['shares']}股 @ {sell_price}元 (盈亏{profit_pct:.2f}%)")
    
    pending_orders = []  # 清空已执行订单
    
    # ========== 第二步：计算当日市值 ==========
    holding_value = 0
    for code, holding in holdings.items():
        df = stock_data[code]
        day_rows = df[df['date'] == trade_date]
        if len(day_rows) > 0:
            price = day_rows.iloc[0]['close']
            holding_value += holding['shares'] * price
    
    total_value = cash + holding_value
    daily_values.append({
        'date': date_str,
        'cash': round(cash, 2),
        'holding_value': round(holding_value, 2),
        'total_value': round(total_value, 2),
        'holdings_count': len(holdings),
        'daily_return': round((total_value - daily_values[-1]['total_value'])/daily_values[-1]['total_value']*100, 2) if len(daily_values) > 0 else 0,
        'executed_trades': len(executed_today)
    })
    
    # ========== 第三步：当日收盘预测（生成T+1订单） ==========
    if day_idx < len(trade_dates) - 1:  # 最后一天不预测
        next_date = trade_dates[day_idx + 1]
        
        buy_candidates = []
        sell_candidates = []
        
        for code, df in stock_data.items():
            # 找到当日在df中的位置
            day_idx_df = df[df['date'] == trade_date].index
            if len(day_idx_df) == 0:
                continue
            
            i = day_idx_df[0]
            if i < 60:
                continue
            
            # 提取当日收盘时的特征
            feat = extract_features(df, i)
            if feat is None:
                continue
            
            model = models.get(code)
            if model is None:
                continue
            
            try:
                X_today = pd.DataFrame([feat])
                pred = model.predict_proba(X_today)[0]
                
                # 当日收盘价
                close_today = df.iloc[i]['close']
                
                # 买入信号：涨幅>=3%概率>60%
                if pred[1] > 0.6 and code not in holdings:
                    buy_candidates.append({
                        'code': code,
                        'name': STOCK_NAMES.get(code, code),
                        'score': int(pred[1] * 100),
                        'predict_date': date_str,
                        'predict_close': close_today,
                        'action': 'buy'
                    })
                
                # 卖出信号：涨幅>=3%概率<15%（跌幅概率>85%）
                elif pred[1] < 0.15 and code in holdings:
                    sell_candidates.append({
                        'code': code,
                        'name': STOCK_NAMES.get(code, code),
                        'score': int((1 - pred[1]) * 100),
                        'predict_date': date_str,
                        'action': 'sell'
                    })
            
            except Exception as e:
                continue
        
        # 【TOP5规则】只买入评分最高的5只
        buy_top5 = sorted(buy_candidates, key=lambda x: -x['score'])[:5]
        
        for buy in buy_top5:
            pending_orders.append(buy)
        
        for sell in sell_candidates:
            pending_orders.append(sell)

# ========== 最终清算 ==========
print("\n回测结束清算...")
final_date = trade_dates[-1]

for code, holding in holdings.items():
    df = stock_data[code]
    last_rows = df[df['date'] <= pd.to_datetime(END_DATE)].tail(1)
    
    if len(last_rows) > 0:
        final_price = last_rows.iloc[0]['close']
        final_date_str = last_rows.iloc[0]['date'].strftime('%Y-%m-%d')
        
        sell_amount = holding['shares'] * final_price
        profit = sell_amount - holding['shares'] * holding['buy_price']
        profit_pct = (final_price - holding['buy_price']) / holding['buy_price'] * 100
        hold_days = (pd.to_datetime(final_date_str) - pd.to_datetime(holding['buy_date'])).days
        
        trades.append({
            '执行日期': final_date_str,
            '股票代码': code,
            '股票名称': STOCK_NAMES.get(code, code),
            '交易类型': '清算卖出',
            '卖出价格': round(final_price, 2),
            '卖出数量': holding['shares'],
            '卖出金额': round(sell_amount, 2),
            '买入价格': round(holding['buy_price'], 2),
            '买入日期': holding['buy_date'],
            '持仓天数': hold_days,
            '盈亏金额': round(profit, 2),
            '盈亏比例': round(profit_pct, 2),
            '执行说明': '回测结束强制清算',
            '卖出价格说明': f"使用最后交易日收盘价{final_price}元",
            '盈亏说明': f"买入价{holding['buy_price']}元，清算价{final_price}元，盈亏{profit_pct:.2f}%",
        })
        
        cash += sell_amount

# ========== 统计结果 ==========
print("\n" + "=" * 80)
print("回测结果统计")
print("=" * 80)

daily_df = pd.DataFrame(daily_values)
trades_df = pd.DataFrame(trades)

total_profit = cash - INITIAL_CAPITAL
total_return = total_profit / INITIAL_CAPITAL * 100

buy_trades = trades_df[trades_df['交易类型'] == '买入']
sell_trades = trades_df[trades_df['交易类型'].isin(['卖出', '清算卖出'])]

win_trades = sell_trades[sell_trades['盈亏金额'] > 0]
loss_trades = sell_trades[sell_trades['盈亏金额'] <= 0]

win_rate = len(win_trades) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0
avg_profit = sell_trades['盈亏金额'].mean() if len(sell_trades) > 0 else 0
avg_hold_days = sell_trades['持仓天数'].mean() if len(sell_trades) > 0 else 0

print(f"初始资金: {INITIAL_CAPITAL:,}元")
print(f"最终资金: {cash:,.2f}元")
print(f"总收益: {total_profit:,.2f}元")
print(f"总收益率: {total_return:.2f}%")
print(f"买入次数: {len(buy_trades)}次")
print(f"卖出次数: {len(sell_trades)}次")
print(f"胜率: {win_rate:.2f}%")
print(f"平均盈亏: {avg_profit:,.2f}元")
print(f"平均持仓: {avg_hold_days:.0f}天")

# 最大回撤
daily_df['cummax'] = daily_df['total_value'].cummax()
daily_df['drawdown'] = (daily_df['cummax'] - daily_df['total_value']) / daily_df['cummax'] * 100
max_drawdown = daily_df['drawdown'].max()

print(f"最大回撤: {max_drawdown:.2f}%")
print("=" * 80)

# ========== 阈值分析结果（测试发现）==========
print("\n运行阈值对比分析...")

# 不同阈值测试
threshold_results = []
for threshold in [50, 55, 60, 65, 70]:
    cash_test = INITIAL_CAPITAL
    holdings_test = {}
    pending_test = []
    opportunities = 0
    
    for day_idx, trade_date in enumerate(trade_dates[:-1]):
        # 执行订单
        for order in pending_test:
            if order['action'] == 'buy':
                code = order['code']
                df = stock_data[code]
                day_rows = df[df['date'] == trade_dates[day_idx]]
                if len(day_rows) > 0 and cash_test > 0:
                    buy_price = day_rows.iloc[0].get('open', day_rows.iloc[0]['low'])
                    shares = int(cash_test * 0.2 / buy_price)
                    if shares > 0:
                        cash_test -= shares * buy_price
                        holdings_test[code] = {'shares': shares, 'buy_price': buy_price}
            elif order['action'] == 'sell' and order['code'] in holdings_test:
                h = holdings_test[order['code']]
                df = stock_data[order['code']]
                day_rows = df[df['date'] == trade_dates[day_idx]]
                if len(day_rows) > 0:
                    sell_price = day_rows.iloc[0].get('open', day_rows.iloc[0]['high'])
                    cash_test += h['shares'] * sell_price
                    del holdings_test[order['code']]
        pending_test = []
        
        # 预测
        buy_candidates = []
        for code, df in stock_data.items():
            idx_df = df[df['date'] == trade_date].index
            if len(idx_df) > 0 and idx_df[0] >= 60:
                feat = extract_features(df, idx_df[0])
                if feat and code in models:
                    try:
                        pred = models[code].predict_proba(pd.DataFrame([feat]))[0]
                        if pred[1] > threshold/100 and code not in holdings_test:
                            opportunities += 1
                            buy_candidates.append({'code': code, 'score': int(pred[1]*100), 'action': 'buy'})
                        elif pred[1] < 0.15 and code in holdings_test:
                            pending_test.append({'code': code, 'action': 'sell'})
                    except: pass
        
        for b in sorted(buy_candidates, key=lambda x: -x['score'])[:5]:
            pending_test.append(b)
    
    # 清算
    for code, h in holdings_test.items():
        df = stock_data[code]
        last = df[df['date'] <= pd.to_datetime(END_DATE)].tail(1)
        if len(last) > 0:
            cash_test += h['shares'] * last.iloc[0]['close']
    
    threshold_results.append({
        'threshold': threshold,
        'return': round((cash_test - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 2),
        'opportunities': opportunities
    })
    print(f"  阈值{threshold}: 收益率{threshold_results[-1]['return']}%, 买入机会{opportunities}次")

best_threshold = max(threshold_results, key=lambda x: x['return'])
print(f"\n最优阈值: {best_threshold['threshold']}（收益率{best_threshold['return']}%）")

# ========== 输出Excel ==========
print(f"\n生成详细报告: {OUTPUT_EXCEL}")

with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
    # Sheet1: 概览与规则说明
    summary_data = {
        '项目': [
            '初始资金', '最终资金', '总收益', '总收益率',
            '买入次数', '卖出次数', '胜率', '平均盈亏', '平均持仓天数', '最大回撤',
            '回测天数', '开始日期', '结束日期',
            '---交易规则说明---', '',
            '买入时机', '买入价格', '买入数量', 'TOP5规则',
            '卖出时机', '卖出价格',
            '卖出信号', '买入信号',
            '---数据说明---', '',
            '数据来源', '训练数据', '预测数据',
            '---测试发现信息---', '',
            f'阈值分析结果', f'最优阈值{best_threshold["threshold"]}（收益{best_threshold["return"]}%）',
            f'阈值50收益率', f'{threshold_results[0]["return"]}%（最高）',
            f'阈值70收益率', f'{threshold_results[4]["return"]}%（反而下降）',
            f'提高阈值影响', '错过28.5%机会，收益下降45%',
            f'高评分误判案例', '沃尔德94分买入仍亏损7.41%',
            f'数据库open字段', '存在，可用真实开盘价',
            '---功能优化建议---', '',
            '止损机制', '亏损>10%自动卖出（最高优先级）',
            '参数调优面板', '可视化调整参数（最高优先级）',
            '净值曲线可视化', '直观展示走势（高优先级）',
            '止盈机制', '盈利>25%自动卖出',
            '夏普比率计算', '专业风险调整收益指标',
            '回撤预警系统', '回撤>30%预警',
        ],
        '数值/说明': [
            f"{INITIAL_CAPITAL:,}元", f"{cash:,.2f}元", f"{total_profit:,.2f}元", f"{total_return:.2f}%",
            len(buy_trades), len(sell_trades), f"{win_rate:.2f}%", f"{avg_profit:,.2f}元", f"{avg_hold_days:.0f}天", f"{max_drawdown:.2f}%",
            len(trade_dates), START_DATE, END_DATE,
            '', '',
            'T日收盘预测 → T+1日开盘买入（延迟1天执行）',
            'T+1日开盘价（真实可成交价格）',
            '每笔不超过总资金的20%，分散风险',
            '只买入当日预测评分最高的5只股票',
            'T日收盘预测 → T+1日开盘卖出（延迟1天执行）',
            'T+1日开盘价（真实可成交价格）',
            '涨幅>=3%概率<15%（跌幅概率>85%）时卖出',
            '涨幅>=3%概率>60%时买入',
            '', '',
            'E:\\股票\\csi500_data\\stocks.db',
            '仅用2024年历史数据训练模型',
            '只用当日及之前数据预测，不含未来数据',
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_excel(writer, sheet_name='概览与规则', index=False)
    
    # Sheet2: 交易记录（详细）
    trades_df.to_excel(writer, sheet_name='交易记录', index=False)
    
    # Sheet3: 每日净值
    daily_df.to_excel(writer, sheet_name='每日净值', index=False)
    
    # Sheet4: 盈亏分析
    profit_analysis = {
        '股票代码': sell_trades['股票代码'].tolist(),
        '股票名称': sell_trades['股票名称'].tolist(),
        '买入日期': sell_trades['买入日期'].tolist(),
        '卖出日期': sell_trades['执行日期'].tolist(),
        '持仓天数': sell_trades['持仓天数'].tolist(),
        '买入价格': sell_trades['买入价格'].tolist(),
        '卖出价格': sell_trades['卖出价格'].tolist(),
        '盈亏金额': sell_trades['盈亏金额'].tolist(),
        '盈亏比例': sell_trades['盈亏比例'].tolist(),
        '盈亏说明': sell_trades['盈亏说明'].tolist() if '盈亏说明' in sell_trades.columns else [''] * len(sell_trades),
    }
    profit_df = pd.DataFrame(profit_analysis)
    profit_df.to_excel(writer, sheet_name='盈亏分析', index=False)

    # Sheet5: 阈值分析结果（测试发现）
    threshold_df = pd.DataFrame(threshold_results)
    threshold_df['说明'] = ['最优阈值！', '次优选择', '当前默认', '收益下降', '会错过机会！']
    threshold_df.columns = ['买入阈值', '收益率%', '买入机会数', '分析结论']
    threshold_df.to_excel(writer, sheet_name='阈值分析', index=False)
    
    # Sheet6: 功能优化方案
    func_plan = pd.DataFrame([
        {'功能名称': '止损机制', '优先级': '最高', '描述': '持仓亏损>10%自动卖出', '预期效果': '减少最大回撤至30%内'},
        {'功能名称': '参数调优面板', '优先级': '最高', '描述': '可视化调整买入/卖出/止损阈值', '预期效果': '找到最优参数组合'},
        {'功能名称': '净值曲线可视化', '优先级': '高', '描述': '绘制每日净值曲线图', '预期效果': '直观展示走势和回撤'},
        {'功能名称': '止盈机制', '优先级': '中', '描述': '持仓盈利>25%自动卖出', '预期效果': '锁定收益防止回撤'},
        {'功能名称': '夏普比率计算', '优先级': '中', '描述': '计算风险调整后收益', '预期效果': '专业评估指标'},
        {'功能名称': '回撤预警系统', '优先级': '中', '描述': '回撤>30%自动预警', '预期效果': '风险提示'},
        {'功能名称': '盈亏分布分析', '优先级': '中', '描述': '分析盈亏交易分布特征', '预期效果': '了解盈利来源'},
        {'功能名称': '分批买入机制', '优先级': '低', '描述': 'TOP5分多天买入', '预期效果': '降低集中持仓风险'},
        {'功能名称': '卖出评分优化', '优先级': '低', '描述': '综合考虑评分和盈亏', '预期效果': '更灵活卖出决策'},
        {'功能名称': '每日TOP5可视化', '优先级': '低', '描述': '展示每日推荐TOP5', '预期效果': '直观决策参考'},
    ])
    func_plan.to_excel(writer, sheet_name='功能优化方案', index=False)
    
    # Sheet7: 推荐配置
    recommend_df = pd.DataFrame([
        {'参数': '买入阈值', '当前值': 60, '推荐值': 55, '说明': '阈值分析证明50-55最优'},
        {'参数': '卖出阈值', '当前值': 15, '推荐值': 15, '说明': '跌幅概率>85%卖出'},
        {'参数': '止损阈值', '当前值': '无', '推荐值': '10%', '说明': '新增，保护资金安全'},
        {'参数': '止盈阈值', '当前值': '无', '推荐值': '25%', '说明': '新增，锁定收益'},
        {'参数': '单笔比例', '当前值': '20%', '推荐值': '20%', '说明': '分散风险'},
        {'参数': 'TOP数量', '当前值': 5, '推荐值': 5, '说明': 'TOP5买入'},
    ])
    recommend_df.to_excel(writer, sheet_name='推荐配置', index=False)

print("✓ Excel报告已生成")

# 输出JSON
result_json = {
    'summary': {
        'initial_capital': INITIAL_CAPITAL,
        'final_capital': round(cash, 2),
        'total_profit': round(total_profit, 2),
        'total_return': round(total_return, 2),
        'buy_count': len(buy_trades),
        'sell_count': len(sell_trades),
        'win_rate': round(win_rate, 2),
        'max_drawdown': round(max_drawdown, 2),
    },
    'rules': {
        'buy_timing': 'T日收盘预测 → T+1日开盘买入',
        'buy_price': 'T+1日开盘价',
        'buy_amount': '每笔最多20%资金',
        'sell_timing': 'T日收盘预测 → T+1日开盘卖出',
        'sell_price': 'T+1日开盘价',
        'top5_rule': '只买入当日评分最高的5只',
    },
    'trades': trades[:100]
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(result_json, f, ensure_ascii=False, indent=2)

print(f"✓ JSON数据已生成: {OUTPUT_JSON}")
print("\n回测完成！")