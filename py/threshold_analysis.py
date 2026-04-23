# -*- coding: utf-8 -*-
"""
买入阈值对比分析
分析不同评分阈值对回测结果的影响
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

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
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

print("=" * 70)
print("买入阈值对比分析")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)

# 加载数据
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
    conn, params=(START_DATE, END_DATE)
)
trade_dates = pd.to_datetime(dates_df['date']).tolist()
conn.close()

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
    
    if i >= 60:
        high_60 = df.iloc[i-60:i+1]['close'].max()
        low_60 = df.iloc[i-60:i+1]['close'].min()
        feat['price_position_60'] = (close - low_60)/(high_60 - low_60) if high_60 > low_60 else 0.5
    else:
        feat['price_position_60'] = 0.5
    
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
print("\n训练模型...")
models = {}

for code, df in stock_data.items():
    if len(df) < 200:
        continue
    
    train_end = df[df['date'] < START_DATE].tail(500)
    if len(train_end) < 100:
        continue
    
    train_df = train_end.reset_index(drop=True)
    
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

# 测试不同阈值
thresholds = [50, 55, 60, 65, 70, 75, 80]
results = []

print("\n测试不同买入阈值...")

for threshold in thresholds:
    print(f"\n测试阈值: {threshold}（涨幅概率>{threshold}%）")
    
    cash = INITIAL_CAPITAL
    holdings = {}
    trades = []
    pending_orders = []
    buy_opportunities = 0  # 买入机会数
    
    for day_idx, trade_date in enumerate(trade_dates):
        # 执行pending订单
        for order in pending_orders:
            if order['action'] == 'buy':
                code = order['code']
                df = stock_data[code]
                day_rows = df[df['date'] == trade_date]
                if len(day_rows) == 0:
                    continue
                
                day_data = day_rows.iloc[0]
                buy_price = day_data['open'] if pd.notna(day_data.get('open')) else day_data['low']
                
                buy_amount = min(cash * 0.2, cash)
                shares = int(buy_amount / buy_price)
                
                if shares > 0 and cash >= shares * buy_price:
                    cash -= shares * buy_price
                    holdings[code] = {
                        'shares': shares,
                        'buy_price': buy_price,
                        'buy_date': trade_date
                    }
            
            elif order['action'] == 'sell':
                code = order['code']
                if code not in holdings:
                    continue
                
                holding = holdings[code]
                df = stock_data[code]
                day_rows = df[df['date'] == trade_date]
                if len(day_rows) == 0:
                    continue
                
                day_data = day_rows.iloc[0]
                sell_price = day_data['open'] if pd.notna(day_data.get('open')) else day_data['high']
                
                cash += holding['shares'] * sell_price
                del holdings[code]
        
        pending_orders = []
        
        # 当日预测
        if day_idx < len(trade_dates) - 1:
            buy_candidates = []
            
            for code, df in stock_data.items():
                day_idx_df = df[df['date'] == trade_date].index
                if len(day_idx_df) == 0:
                    continue
                
                i = day_idx_df[0]
                if i < 60:
                    continue
                
                feat = extract_features(df, i)
                if feat is None:
                    continue
                
                model = models.get(code)
                if model is None:
                    continue
                
                try:
                    X_today = pd.DataFrame([feat])
                    pred = model.predict_proba(X_today)[0]
                    
                    # 统计买入机会
                    if pred[1] > threshold/100:
                        buy_opportunities += 1
                    
                    # 买入信号
                    if pred[1] > threshold/100 and code not in holdings:
                        buy_candidates.append({
                            'code': code,
                            'score': int(pred[1] * 100),
                            'action': 'buy'
                        })
                    
                    # 卖出信号（固定）
                    elif pred[1] < 0.15 and code in holdings:
                        pending_orders.append({'code': code, 'action': 'sell'})
                
                except:
                    continue
            
            # TOP5
            buy_top5 = sorted(buy_candidates, key=lambda x: -x['score'])[:5]
            for buy in buy_top5:
                pending_orders.append(buy)
    
    # 清算
    for code, holding in holdings.items():
        df = stock_data[code]
        last_rows = df[df['date'] <= pd.to_datetime(END_DATE)].tail(1)
        if len(last_rows) > 0:
            cash += holding['shares'] * last_rows.iloc[0]['close']
    
    total_return = (cash - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # 统计买入次数
    buy_count = len([o for o in pending_orders if o.get('action') == 'buy'])
    
    results.append({
        'threshold': threshold,
        'final_cash': round(cash, 2),
        'total_return': round(total_return, 2),
        'buy_opportunities': buy_opportunities,
        'description': f"涨幅概率>{threshold}%时买入"
    })
    
    print(f"  最终资金: {cash:,.2f}元, 收益率: {total_return:.2f}%, 买入机会: {buy_opportunities}")

# 输出对比结果
print("\n" + "=" * 70)
print("阈值对比结果")
print("=" * 70)
print(f"{'阈值':<10} {'收益率':<15} {'买入机会数':<15} {'说明':<30}")
print("-" * 70)

for r in results:
    print(f"{r['threshold']:<10} {r['total_return']:.2f}%{'':<8} {r['buy_opportunities']:<15} {r['description']:<30}")

# 找最优
best = max(results, key=lambda x: x['total_return'])
print("-" * 70)
print(f"最优阈值: {best['threshold']}（收益率{best['total_return']}%）")

# 分析阈值≥70的影响
print("\n" + "=" * 70)
print("阈值≥70的影响分析")
print("=" * 70)

baseline = results[2]  # threshold=60
target70 = results[4]  # threshold=70

print(f"当前阈值(60): 买入机会{baseline['buy_opportunities']}次, 收益率{baseline['total_return']}%")
print(f"提高阈值(70): 买入机会{target70['buy_opportunities']}次, 收益率{target70['total_return']}%")
print(f"机会减少: {baseline['buy_opportunities'] - target70['buy_opportunities']}次 ({(baseline['buy_opportunities'] - target70['buy_opportunities'])/baseline['buy_opportunities']*100:.1f}%)")

# 保存结果
with open(r'e:\csi10\threshold_analysis.json', 'w', encoding='utf-8') as f:
    json.dump({
        'results': results,
        'best_threshold': best['threshold'],
        'analysis': {
            'baseline_60': baseline,
            'target_70': target70,
            'opportunity_reduction_pct': round((baseline['buy_opportunities'] - target70['buy_opportunities'])/baseline['buy_opportunities']*100, 1)
        }
    }, f, ensure_ascii=False, indent=2)

print("\n分析结果已保存: e:\\csi10\\threshold_analysis.json")