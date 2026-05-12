# -*- coding: utf-8 -*-
"""
股票模拟交易回测系统
时间范围: 2025-01-01 到 2026-04-18
初始资金: 100万
策略: 只购买模型推荐的TOP5买入股票
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
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

# 配置
DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
INDEX_CODE = 'sh.000300'
OUTPUT_EXCEL = r'e:\csi10\backtest_result.xlsx'
INITIAL_CAPITAL = 1000000  # 100万
START_DATE = '2025-01-01'
END_DATE = '2026-04-18'

# 股票名称映射
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

print("=" * 70)
print("股票模拟交易回测系统")
print(f"时间范围: {START_DATE} → {END_DATE}")
print(f"初始资金: {INITIAL_CAPITAL:,}元")
print("=" * 70)

# 连接数据库
conn = sqlite3.connect(DB_PATH)

# 加载股票池
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
print(f"股票池: {len(stock_pool)}只")

# 加载大盘数据
index_sql = '''
    SELECT date, close, pct_chg, ma5, ma10, ma20, ma30,
           macd, macd_signal, macd_hist, rsi6, rsi12, rsi24
    FROM index_daily WHERE code = ? ORDER BY date
'''
index_data = pd.read_sql_query(index_sql, conn, params=(INDEX_CODE,))
index_data['date'] = pd.to_datetime(index_data['date'])
print(f"大盘数据: {len(index_data)}条")

# 获取交易日列表
dates_sql = "SELECT DISTINCT date FROM daily_price WHERE date >= ? AND date <= ? ORDER BY date"
dates_df = pd.read_sql_query(dates_sql, conn, params=(START_DATE, END_DATE))
trade_dates = pd.to_datetime(dates_df['date']).tolist()
print(f"交易日: {len(trade_dates)}天")

# 特征提取函数
def extract_features(df, i, index_data=None):
    """完整特征提取（43个特征）"""
    if i < 60 or i >= len(df) - 3:
        return None
    
    row = df.iloc[i]
    current_date = row['date']
    
    # 基础数据
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
    
    feat = {}
    
    # 价格动量（3个特征）
    feat['pct_chg'] = pct_chg
    feat['pct_chg_5d'] = df.iloc[i-5:i]['pct_chg'].sum() if i >= 5 else 0
    feat['pct_chg_10d'] = df.iloc[i-10:i]['pct_chg'].sum() if i >= 10 else 0
    
    # 均线系统（7个特征）
    feat['ma5_ratio'] = close/ma5 if ma5 > 0 else 1
    feat['ma10_ratio'] = close/ma10 if ma10 > 0 else 1
    feat['ma20_ratio'] = close/ma20 if ma20 > 0 else 1
    feat['ma30_ratio'] = close/ma30 if ma30 > 0 else 1
    feat['ma5_ma10_diff'] = (ma5 - ma10)/ma10 if ma10 > 0 else 0
    feat['ma10_ma20_diff'] = (ma10 - ma20)/ma20 if ma20 > 0 else 0
    feat['ma5_slope'] = (ma5 - df.iloc[i-5]['ma5'])/ma5 if i >= 5 and ma5 > 0 else 0
    
    # RSI系统（6个特征）
    feat['rsi6'] = rsi6
    feat['rsi12'] = rsi12
    feat['rsi24'] = rsi24
    feat['rsi6_rsi12_diff'] = rsi6 - rsi12
    feat['rsi_oversold'] = 1 if rsi6 < 30 else 0
    feat['rsi_overbought'] = 1 if rsi6 > 70 else 0
    
    # MACD系统（5个特征）
    feat['macd'] = macd
    feat['macd_hist'] = macd_hist
    feat['macd_signal'] = macd_signal
    feat['macd_cross_up'] = 1 if macd > macd_signal and macd_hist > 0 else 0
    feat['macd_cross_down'] = 1 if macd < macd_signal and macd_hist < 0 else 0
    
    # KDJ系统（4个特征）
    feat['k'] = k
    feat['d'] = d
    feat['j'] = j
    feat['kdj_cross'] = 1 if k > d else 0
    
    # 量价关系（2个特征）
    if i >= 20:
        vol_ma = df.iloc[i-20:i]['volume'].mean()
        feat['vol_ratio'] = volume/vol_ma if vol_ma > 0 else 1
    else:
        feat['vol_ratio'] = 1
    feat['vol_price_trend'] = 1 if volume > feat['vol_ratio'] * 1.5 and pct_chg > 0 else 0
    
    # 波动率（2个特征）
    if i >= 20:
        closes20 = df.iloc[i-20:i+1]['close'].values
        returns20 = np.diff(closes20)/closes20[:-1]
        feat['volatility_20'] = np.std(returns20) * 100
    else:
        feat['volatility_20'] = 2
    if i >= 30:
        closes30 = df.iloc[i-30:i+1]['close'].values
        returns30 = np.diff(closes30)/closes30[:-1]
        feat['volatility_30'] = np.std(returns30) * 100
    else:
        feat['volatility_30'] = 2
    
    # 价格位置（1个特征）
    if i >= 60:
        high_60 = df.iloc[i-60:i+1]['close'].max()
        low_60 = df.iloc[i-60:i+1]['close'].min()
        feat['price_position_60'] = (close - low_60)/(high_60 - low_60) if high_60 > low_60 else 0.5
    else:
        feat['price_position_60'] = 0.5
    
    # 涨跌统计（4个特征）
    if i >= 5:
        pct_list5 = df.iloc[i-5:i]['pct_chg'].values
        feat['up_days_5'] = len([p for p in pct_list5 if p > 0])
        feat['down_days_5'] = len([p for p in pct_list5 if p < 0])
    else:
        feat['up_days_5'] = 0
        feat['down_days_5'] = 0
    if i >= 10:
        pct_list10 = df.iloc[i-10:i]['pct_chg'].values
        feat['up_days_10'] = len([p for p in pct_list10 if p > 0])
        feat['down_days_10'] = len([p for p in pct_list10 if p < 0])
    else:
        feat['up_days_10'] = 0
        feat['down_days_10'] = 0
    
    # 日内波动（1个特征）
    feat['intraday_range'] = (high - low)/low * 100 if low > 0 else 0
    
    # 大盘因子（7个特征）
    if index_data is not None:
        idx_row = index_data[index_data['date'] == current_date]
        if len(idx_row) > 0:
            idx = idx_row.iloc[0]
            feat['index_pct_chg'] = idx['pct_chg'] if pd.notna(idx['pct_chg']) else 0
            feat['index_ma5_ratio'] = idx['close']/idx['ma5'] if pd.notna(idx['ma5']) and idx['ma5'] > 0 else 1
            feat['index_rsi6'] = idx['rsi6'] if pd.notna(idx['rsi6']) else 50
            feat['index_rsi12'] = idx['rsi12'] if pd.notna(idx['rsi12']) else 50
            feat['index_macd'] = idx['macd'] if pd.notna(idx['macd']) else 0
            feat['index_macd_hist'] = idx['macd_hist'] if pd.notna(idx['macd_hist']) else 0
            feat['stock_vs_index'] = pct_chg - feat['index_pct_chg']
        else:
            feat['index_pct_chg'] = 0
            feat['index_ma5_ratio'] = 1
            feat['index_rsi6'] = 50
            feat['index_rsi12'] = 50
            feat['index_macd'] = 0
            feat['index_macd_hist'] = 0
            feat['stock_vs_index'] = 0
    else:
        feat['index_pct_chg'] = 0
        feat['index_ma5_ratio'] = 1
        feat['index_rsi6'] = 50
        feat['index_rsi12'] = 50
        feat['index_macd'] = 0
        feat['index_macd_hist'] = 0
        feat['stock_vs_index'] = 0
    
    # 目标（3日涨幅>=3%）
    close_3d = df.iloc[i+3]['close']
    rise_3d = (close_3d - close)/close if close > 0 else 0
    feat['target'] = 1 if rise_3d >= 0.03 else 0
    
    return feat

# 加载所有股票历史数据
print("\n加载股票历史数据...")
stock_data = {}
for code in stock_pool:
    sql = f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date"
    df = pd.read_sql_query(sql, conn)
    if len(df) > 0:
        df['date'] = pd.to_datetime(df['date'])
        stock_data[code] = df

print(f"已加载: {len(stock_data)}只股票")

# 训练模型（使用2024年数据）
print("\n训练模型...")
models = {}

for code, df in stock_data.items():
    if len(df) < 200:
        continue
    
    # 使用2024年数据训练
    train_df = df[df['date'] < START_DATE].tail(500)
    if len(train_df) < 100:
        continue
    
    train_df = train_df.reset_index(drop=True)
    
    features = []
    for i in range(60, len(train_df)-3):
        feat = extract_features(train_df, i, index_data)
        if feat:
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
    except:
        continue

print(f"已训练: {len(models)}个模型")

# 模拟交易
print("\n开始模拟交易...")

# 初始化
cash = INITIAL_CAPITAL
holdings = {}  # {code: {'shares': n, 'buy_price': p, 'buy_date': d}}
trades = []  # 交易记录
daily_values = []  # 每日净值

# 模拟每个交易日
for trade_date in trade_dates:
    date_str = trade_date.strftime('%Y-%m-%d')
    
    # 计算当日持仓市值
    holding_value = 0
    for code, holding in holdings.items():
        df = stock_data[code]
        day_data = df[df['date'] == trade_date]
        if len(day_data) > 0:
            price = day_data.iloc[0]['close']
            holding_value += holding['shares'] * price
    
    total_value = cash + holding_value
    daily_values.append({
        'date': date_str,
        'cash': cash,
        'holding_value': holding_value,
        'total_value': total_value,
        'holdings_count': len(holdings)
    })
    
    # 每日决策
    buy_candidates = []
    sell_candidates = []
    
    for code, df in stock_data.items():
        # 找到当日在数据中的位置
        day_idx = df[df['date'] == trade_date].index
        if len(day_idx) == 0:
            continue
        
        idx = day_idx[0]
        if idx < 60 or idx >= len(df) - 3:
            continue
        
        # 提取特征
        feat = extract_features(df.reset_index(drop=True), idx, index_data)
        if feat is None:
            continue
        
        # 预测
        model = models.get(code)
        if model:
            try:
                X_latest = pd.DataFrame([feat]).drop('target', axis=1, errors='ignore')
                pred = model.predict_proba(X_latest)[0]
                
                # 买入信号：涨幅>=3%概率>60%
                if pred[1] > 0.6:
                    buy_candidates.append({
                        'code': code,
                        'name': STOCK_NAMES.get(code, code),
                        'price': df.iloc[idx]['close'],
                        'score': int(pred[1] * 100),
                        'date': date_str
                    })
                
                # 卖出信号：涨幅>=3%概率<15%
                elif pred[1] < 0.15 and code in holdings:
                    sell_candidates.append({
                        'code': code,
                        'name': STOCK_NAMES.get(code, code),
                        'price': df.iloc[idx]['close'],
                        'score': int((1 - pred[1]) * 100),
                        'date': date_str
                    })
            except:
                continue
    
    # 先卖出
    for sell in sell_candidates:
        if sell['code'] in holdings:
            holding = holdings[sell['code']]
            sell_amount = holding['shares'] * sell['price']
            profit = sell_amount - holding['shares'] * holding['buy_price']
            profit_pct = (sell['price'] - holding['buy_price']) / holding['buy_price'] * 100
            
            trades.append({
                '交易日期': date_str,
                '股票代码': sell['code'],
                '股票名称': sell['name'],
                '交易类型': '卖出',
                '交易价格': round(sell['price'], 2),
                '交易数量': holding['shares'],
                '交易金额': round(sell_amount, 2),
                '买入价格': round(holding['buy_price'], 2),
                '买入日期': holding['buy_date'],
                '持仓天数': (trade_date - pd.to_datetime(holding['buy_date'])).days,
                '盈亏金额': round(profit, 2),
                '盈亏比例': round(profit_pct, 2),
                '卖出评分': sell['score']
            })
            
            cash += sell_amount
            del holdings[sell['code']]
    
    # 买入TOP5
    buy_candidates_sorted = sorted(buy_candidates, key=lambda x: -x['score'])[:5]
    
    for buy in buy_candidates_sorted:
        if buy['code'] in holdings:
            continue  # 已持有，不重复买入
        
        # 计算可买数量（每次买入不超过总资金的20%）
        buy_amount = min(cash * 0.2, cash)
        shares = int(buy_amount / buy['price'])
        
        if shares > 0:
            actual_amount = shares * buy['price']
            
            trades.append({
                '交易日期': date_str,
                '股票代码': buy['code'],
                '股票名称': buy['name'],
                '交易类型': '买入',
                '交易价格': round(buy['price'], 2),
                '交易数量': shares,
                '交易金额': round(actual_amount, 2),
                '买入价格': round(buy['price'], 2),
                '买入日期': date_str,
                '持仓天数': 0,
                '盈亏金额': 0,
                '盈亏比例': 0,
                '买入评分': buy['score']
            })
            
            cash -= actual_amount
            holdings[buy['code']] = {
                'shares': shares,
                'buy_price': buy['price'],
                'buy_date': date_str
            }

# 最终清算
print("\n最终清算...")
end_date = pd.to_datetime(END_DATE)

for code, holding in holdings.items():
    df = stock_data[code]
    last_data = df[df['date'] <= end_date].tail(1)
    
    if len(last_data) > 0:
        final_price = last_data.iloc[0]['close']
        final_date = last_data.iloc[0]['date'].strftime('%Y-%m-%d')
        
        sell_amount = holding['shares'] * final_price
        profit = sell_amount - holding['shares'] * holding['buy_price']
        profit_pct = (final_price - holding['buy_price']) / holding['buy_price'] * 100
        
        trades.append({
            '交易日期': final_date,
            '股票代码': code,
            '股票名称': STOCK_NAMES.get(code, code),
            '交易类型': '清算卖出',
            '交易价格': round(final_price, 2),
            '交易数量': holding['shares'],
            '交易金额': round(sell_amount, 2),
            '买入价格': round(holding['buy_price'], 2),
            '买入日期': holding['buy_date'],
            '持仓天数': (pd.to_datetime(final_date) - pd.to_datetime(holding['buy_date'])).days,
            '盈亏金额': round(profit, 2),
            '盈亏比例': round(profit_pct, 2),
            '卖出评分': 0
        })
        
        cash += sell_amount

# 统计结果
print("\n统计结果...")

# 每日净值
daily_df = pd.DataFrame(daily_values)
daily_df['收益率'] = (daily_df['total_value'] / INITIAL_CAPITAL - 1) * 100

# 交易记录
trades_df = pd.DataFrame(trades)

# 统计
total_profit = cash - INITIAL_CAPITAL
total_return = total_profit / INITIAL_CAPITAL * 100

buy_trades = trades_df[trades_df['交易类型'] == '买入']
sell_trades = trades_df[trades_df['交易类型'].isin(['卖出', '清算卖出'])]

win_trades = sell_trades[sell_trades['盈亏金额'] > 0]
loss_trades = sell_trades[sell_trades['盈亏金额'] <= 0]

win_rate = len(win_trades) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0
avg_profit = sell_trades['盈亏金额'].mean() if len(sell_trades) > 0 else 0
max_profit = sell_trades['盈亏比例'].max() if len(sell_trades) > 0 else 0
max_loss = sell_trades['盈亏比例'].min() if len(sell_trades) > 0 else 0

print("=" * 70)
print("回测结果")
print("=" * 70)
print(f"初始资金: {INITIAL_CAPITAL:,}元")
print(f"最终资金: {cash:,.2f}元")
print(f"总收益: {total_profit:,.2f}元")
print(f"总收益率: {total_return:.2f}%")
print(f"交易次数: 买入{len(buy_trades)}次, 卖出{len(sell_trades)}次")
print(f"胜率: {win_rate:.2f}%")
print(f"平均盈亏: {avg_profit:,.2f}元")
print(f"最大盈利: {max_profit:.2f}%")
print(f"最大亏损: {max_loss:.2f}%")
print("=" * 70)

# 输出Excel
print(f"\n输出Excel: {OUTPUT_EXCEL}")

with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
    # 概览
    summary_df = pd.DataFrame([{
        '初始资金': INITIAL_CAPITAL,
        '最终资金': round(cash, 2),
        '总收益': round(total_profit, 2),
        '总收益率': round(total_return, 2),
        '买入次数': len(buy_trades),
        '卖出次数': len(sell_trades),
        '胜率': round(win_rate, 2),
        '平均盈亏': round(avg_profit, 2),
        '最大盈利': round(max_profit, 2),
        '最大亏损': round(max_loss, 2),
        '回测天数': len(trade_dates),
        '开始日期': START_DATE,
        '结束日期': END_DATE
    }])
    summary_df.to_excel(writer, sheet_name='概览', index=False)
    
    # 每日净值
    daily_df.to_excel(writer, sheet_name='每日净值', index=False)
    
    # 交易记录
    trades_df.to_excel(writer, sheet_name='交易记录', index=False)

print("✓ Excel已生成")

# 保存JSON结果
result_json = {
    'start_date': START_DATE,
    'end_date': END_DATE,
    'initial_capital': INITIAL_CAPITAL,
    'final_capital': round(cash, 2),
    'total_profit': round(total_profit, 2),
    'total_return': round(total_return, 2),
    'trades_count': len(trades),
    'buy_count': len(buy_trades),
    'sell_count': len(sell_trades),
    'win_rate': round(win_rate, 2),
    'avg_profit': round(avg_profit, 2),
    'max_profit': round(max_profit, 2),
    'max_loss': round(max_loss, 2),
    'trades': trades[:50]  # 只保存前50条
}

with open(r'e:\csi10\backtest_result.json', 'w', encoding='utf-8') as f:
    json.dump(result_json, f, ensure_ascii=False, indent=2)

print("✓ JSON已生成: e:\\csi10\\backtest_result.json")

conn.close()
print("\n回测完成！")