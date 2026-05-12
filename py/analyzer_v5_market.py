# -*- coding: utf-8 -*-
"""
波段股票分析系统 v5.0 - 大盘走势权重版
新增功能:
1. 大盘走势调整因子（不对称-弱市重罚）
2. 动态买入阈值（强势55/震荡60/弱势70）
3. 大盘状态实时显示
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import pandas as pd
import sqlite3
from datetime import datetime
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# ========== 建议生成函数 ==========

def generate_trade_advice(score, market_status, adjusted_score, threshold):
    """生成买卖建议（含大盘调整信息）"""
    
    # 大盘调整说明
    adjustment_info = f"\n大盘调整: {score}→{adjusted_score} ({market_status}, 阈值{threshold}分)"
    
    # 根据调整后评分给出建议（逻辑清晰）
    if adjusted_score < 15:
        # 低评分：建议卖出
        return f"建议卖出！评分仅{adjusted_score}分，风险较高" + adjustment_info + " → ❌卖出"
    elif adjusted_score < threshold:
        # 中等评分：暂不买入
        if adjusted_score >= 40:
            return f"暂不买入。评分{adjusted_score}分，接近阈值{threshold}" + adjustment_info + " → ⚠️观望"
        else:
            return f"观望。评分{adjusted_score}分，中性区间" + adjustment_info + " → ⏸️观望"
    else:
        # 高评分：建议买入
        if adjusted_score >= 80:
            return f"强烈推荐买入！评分{adjusted_score}分" + adjustment_info + " → ✅买入"
        elif adjusted_score >= 70:
            return f"推荐买入。评分{adjusted_score}分" + adjustment_info + " → ✅买入"
        else:
            return f"可考虑买入。评分{adjusted_score}分，达标{threshold}" + adjustment_info + " → ✅买入"

def generate_holding_advice(profit, score, days, holding, market_status):
    """生成持仓建议（含大盘状态）"""
    shares = holding['shares']
    buyPrice = holding['buyPrice']
    
    market_note = f"\n大盘状态: {market_status}"
    
    if profit >= 25:
        return f"✅ 已达止盈线(25%)！盈利{profit:.1f}%。建议分批卖出。" + market_note
    elif profit >= 15:
        return f"盈利可观({profit:.1f}%)。建议部分止盈。" + market_note
    elif profit >= 5:
        return f"小幅盈利({profit:.1f}%)。持仓{days}天。" + market_note
    elif profit >= -5:
        return f"轻微亏损({profit:.1f}%)。继续观察。" + market_note
    elif profit >= -10:
        return f"⚠️ 接近止损线！亏损{profit:.1f}%。" + market_note
    else:
        return f"🔴 触发止损线！亏损{profit:.1f}%。建议止损。" + market_note

# ========== 大盘调整函数 ==========

def get_market_adjustment(conn):
    """获取大盘调整因子和状态"""
    try:
        df = pd.read_sql(
            "SELECT * FROM index_daily WHERE code='sh.000300' ORDER BY date DESC LIMIT 5",
            conn
        )
        
        if len(df) < 5:
            return 1.0, 0, "无大盘数据", 60, []
        
        # 计算5日涨幅
        first_close = df.iloc[-1]['close']
        last_close = df.iloc[0]['close']
        market_pct = (last_close - first_close) / first_close * 100
        
        # 不对称调整因子（弱市重罚）
        if market_pct >= 3:
            factor = 1.05  # 强势轻奖5%
            status = "强势市场"
            threshold = 55  # 激进买入
        elif market_pct >= 1:
            factor = 1.02
            status = "偏强市场"
            threshold = 58
        elif market_pct >= -1:
            factor = 1.0   # 震荡不调整
            status = "震荡市场"
            threshold = 60
        elif market_pct >= -3:
            factor = 0.85  # 偏弱重罚15%
            status = "偏弱市场"
            threshold = 65
        else:
            factor = 0.75  # 弱势极重罚25%
            status = "弱势市场"
            threshold = 70  # 保守等待
        
        # 最近5日走势
        recent = df[['date', 'close', 'pct_chg']].iloc[::-1].to_dict('records')
        
        return factor, market_pct, status, threshold, recent
    
    except Exception as e:
        return 1.0, 0, "大盘数据异常", 60, []

def adjust_score(original_score, factor):
    """调整评分"""
    adjusted = int(original_score * factor)
    return min(100, max(0, adjusted))

# ========== 配置 ==========

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
OUTPUT_JSON = r'e:\csi10\result.json'
HOLDINGS_JSON = r'e:\csi10\holdings.json'

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
print("波段股票分析系统 v5.0 - 大盘走势权重版")
print("股票池范围：30只波段股票")
print("=" * 70)

# 加载股票池
conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
print(f"✓ 股票池: {len(stock_pool)}只（固定范围）")

# ========== 获取大盘状态 ==========

print("\n获取大盘走势...")
factor, market_pct, market_status, threshold, recent = get_market_adjustment(conn)

print(f"\n大盘状态: {market_status}")
print(f"沪深300 5日涨跌: {market_pct:.2f}%")
print(f"调整因子: {factor}")
print(f"买入阈值: {threshold}分")

if recent:
    print(f"\n最近5日走势:")
    for r in recent:
        print(f"  {r['date']} 收盘:{r['close']:.2f} 涨跌:{r['pct_chg']:.2f}%")

# ========== 加载持仓 ==========

print("\n加载用户持仓数据...")
holdings = []
try:
    with open(HOLDINGS_JSON, 'r', encoding='utf-8') as f:
        holdings_data = json.load(f)
        for h in holdings_data:
            if h['code'] in stock_pool:
                h['name'] = STOCK_NAMES.get(h['code'], h['code'])
                holdings.append(h)
                print(f"  ✓ {h['name']}: {h['shares']}股, 成本{h['buyPrice']}元")
except:
    print("  暂无持仓数据")

print(f"✓ 有效持仓: {len(holdings)}只")

# ========== 特征提取 ==========

def extract_features(df, i):
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
    }
    return feat

# ========== 训练模型 ==========

print("\n训练模型...")
models = {}
for code in stock_pool:
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
        if len(df) < 100:
            continue
        features = []
        for i in range(60, len(df)-3):
            feat = extract_features(df.iloc[::-1], len(df)-i-1)
            if feat:
                close = df.iloc[i]['close']
                close_3d = df.iloc[i+3]['close']
                rise = (close_3d - close) / close if close > 0 else 0
                feat['target'] = 1 if rise >= 0.03 else 0
                features.append(feat)
        if len(features) < 30:
            continue
        ds = pd.DataFrame(features)
        X = ds.drop('target', axis=1)
        y = ds['target']
        model = xgb.XGBClassifier(n_estimators=100, max_depth=4, random_state=42, verbosity=0)
        model.fit(X, y)
        models[code] = model
    except:
        continue

print(f"✓ 已训练: {len(models)}个模型")

# ========== 分析股票 ==========

print("\n分析股票池...")
stocks_analysis = []

for code in stock_pool:
    if code not in models:
        continue
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date DESC LIMIT 60", conn)
        if len(df) < 30:
            continue
        feat = extract_features(df.iloc[::-1], len(df)-1)
        if not feat:
            continue
        
        # 基础评分
        pred = models[code].predict_proba(pd.DataFrame([feat]))[0]
        base_score = int(pred[1] * 100)
        
        # 大盘调整评分
        adjusted_score = adjust_score(base_score, factor)
        
        latest = df.iloc[0]
        name = STOCK_NAMES.get(code, code)
        
        # 检查持仓
        holding = next((h for h in holdings if h['code'] == code), None)
        
        if holding:
            current_price = latest['close']
            profit = (current_price - holding['buyPrice']) / holding['buyPrice'] * 100
            hold_days = (datetime.now() - pd.to_datetime(holding['buyDate'])).days
            advice = generate_holding_advice(profit, base_score, hold_days, holding, market_status)
        else:
            advice = generate_trade_advice(base_score, market_status, adjusted_score, threshold)
        
        buy_price = round(latest['close'] * 0.97, 2)
        sell_price = round(latest['close'] * 1.10, 2)
        stop_price = round(latest['close'] * 0.90, 2)
        
        stocks_analysis.append({
            'code': code,
            'name': name,
            'score': base_score,  # 原评分
            'adjusted_score': adjusted_score,  # 调整后评分
            'close': round(latest['close'], 2),
            'pct_chg': round(latest['pct_chg'], 2),
            'volume': int(latest['volume']),
            'date': latest['date'],
            'rsi6': round(latest.get('rsi6', 50), 1),
            'macd': round(latest.get('macd', 0), 2),
            'buy_price': buy_price,
            'sell_price': sell_price,
            'stop_price': stop_price,
            'advice': advice,
            'buy_signal': bool(adjusted_score >= threshold and not holding),  # 用调整评分判断
            'sell_signal': bool(base_score < 15 or (holding and profit <= -10)),
            'is_holding': bool(holding is not None),
        })
    except:
        continue

conn.close()

# ========== 持仓统计 ==========

holdings_result = []
total_profit = 0
total_cost = 0
total_value = 0

for h in holdings:
    analysis = next((s for s in stocks_analysis if s['code'] == h['code']), None)
    if analysis:
        current_price = analysis['close']
        profit = (current_price - h['buyPrice']) / h['buyPrice'] * 100
        profit_amount = (current_price - h['buyPrice']) * h['shares']
        hold_days = (datetime.now() - pd.to_datetime(h['buyDate'])).days
        
        cost = h['buyPrice'] * h['shares']
        value = current_price * h['shares']
        total_cost += cost
        total_value += value
        total_profit += profit_amount
        
        holdings_result.append({
            'code': h['code'],
            'name': h['name'],
            'shares': h['shares'],
            'buyPrice': h['buyPrice'],
            'currentPrice': current_price,
            'profit': round(profit, 2),
            'profitAmount': round(profit_amount, 2),
            'holdDays': hold_days,
            'score': analysis['score'],
            'adjusted_score': analysis['adjusted_score'],
            'advice': analysis['advice'],
        })

# ========== 输出结果 ==========

result = {
    'version': '5.0',
    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'stock_pool_size': len(stock_pool),
    
    # 大盘信息（新增）
    'market': {
        'status': market_status,
        'pct_5d': round(market_pct, 2),
        'factor': factor,
        'threshold': threshold,
        'recent_5d': recent,
    },
    
    'stocks': stocks_analysis,
    'holdings': holdings_result,
    'holdings_stats': {
        'count': len(holdings_result),
        'total_cost': round(total_cost, 2),
        'total_value': round(total_value, 2),
        'total_profit': round(total_profit, 2),
        'profit_rate': round((total_value-total_cost)/total_cost*100, 2) if total_cost > 0 else 0,
    },
    'statistics': {
        'total': len(stocks_analysis),
        'buy_count': len([s for s in stocks_analysis if s['buy_signal']]),
        'sell_count': len([s for s in stocks_analysis if s['sell_signal']]),
        'holding_count': len(holdings_result),
        'watch_count': len([s for s in stocks_analysis if not s['is_holding'] and threshold <= s['adjusted_score'] < 80]),
    },
    'market_analysis': f"{market_status}，大盘5日涨跌{market_pct:.2f}%，调整因子{factor}",
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✓ 分析完成: {len(stocks_analysis)}只股票")
print(f"✓ 买入推荐: {result['statistics']['buy_count']}只")
print(f"✓ 卖出建议: {result['statistics']['sell_count']}只")
print(f"✓ 输出文件: {OUTPUT_JSON}")

# 打印大盘调整示例
print("\n" + "=" * 70)
print("大盘调整评分示例:")
print("=" * 70)
sample_stocks = stocks_analysis[:5]
for s in sample_stocks:
    print(f"{s['name']}: 原评分{s['score']} → 调整{s['adjusted_score']} ({s['advice'][:30]}...)")

print("\n" + "=" * 70)
print(f"系统版本: v5.0 (大盘走势权重版)")
print(f"大盘调整: {market_status} | 因子{factor} | 阈值{threshold}分")
print("=" * 70)