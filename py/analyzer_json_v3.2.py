# -*- coding: utf-8 -*-
"""
波段股票分析系统 v3.2 增强版
新增功能：
1. 持仓股监控
2. 买卖指导建议
3. 详细分析报告
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import pandas as pd
import sqlite3
import numpy as np
from datetime import datetime
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# 配置
DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
OUTPUT_JSON = r'e:\csi10\result.json'

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
print("波段股票分析系统 v3.2 增强版")
print("=" * 70)

# 持仓配置（可编辑）
HOLDINGS = [
    {'code': '688028.SH', 'shares': 1000, 'buy_price': 45.20, 'buy_date': '2026-04-15'},
    {'code': '688195.SH', 'shares': 500, 'buy_price': 78.50, 'buy_date': '2026-04-10'},
    {'code': '300136.SZ', 'shares': 800, 'buy_price': 32.00, 'buy_date': '2026-04-08'},
]

# ========== 生成建议函数 ==========

def generate_advice(score, row):
    """生成买卖建议"""
    rsi = row.get('rsi6', 50) if hasattr(row, 'get') else 50
    pct = row.get('pct_chg', 0) if hasattr(row, 'get') else 0
    
    if score >= 80:
        return f"强烈推荐买入！评分{score}分，高质量标的。建议优先配置15-20%仓位。"
    elif score >= 70:
        return f"推荐买入。评分{score}分，上涨概率高。建议分批建仓，首次10%。"
    elif score >= 60:
        return f"可考虑买入。评分{score}分，达到买入阈值。建议T+1策略买入。"
    elif score >= 40:
        return f"暂不买入。评分{score}分，未达买入阈值。建议观察等待突破60。"
    elif score >= 15:
        return f"观望。评分{score}分，中性区间。暂不操作等待明确信号。"
    else:
        return f"建议卖出！评分仅{score}分，跌幅概率{100-score}%。建议及时止损。"

def generate_holding_advice(profit, score, days):
    """生成持仓建议"""
    if profit >= 25:
        return f"已达止盈线(25%)！建议分批卖出锁定收益。盈利{profit:.1f}%。"
    elif profit >= 15:
        return f"盈利可观({profit:.1f}%)。建议部分止盈，卖出30-50%。"
    elif profit >= 5:
        return f"小幅盈利({profit:.1f}%)。可继续持有，关注走势。"
    elif profit >= -5:
        return f"轻微亏损({profit:.1f}%)。继续观察，等待反弹。"
    elif profit >= -10:
        return f"接近止损线(-10%)。亏损{profit:.1f}%，密切关注。"
    else:
        return f"触发止损线！亏损{profit:.1f}%，建议果断卖出止损。"

def generate_market_analysis(stocks):
    """生成市场分析"""
    buy_count = len([s for s in stocks if s['score'] >= 60])
    sell_count = len([s for s in stocks if s['score'] < 15])
    avg_score = sum(s['score'] for s in stocks) / len(stocks) if stocks else 50
    
    if buy_count >= 10:
        trend = "多头市场，买入信号较多，可适当增仓。"
    elif sell_count >= 5:
        trend = "空头市场，卖出信号较多，建议减仓观望。"
    else:
        trend = "震荡市场，信号中性，建议谨慎操作。"
    
    return f"{trend} 平均评分{avg_score:.0f}分。建议关注评分>70的标的，严格执行止损止盈。"

# 连接数据库
conn = sqlite3.connect(DB_PATH)

# 加载股票池
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
print(f"✓ 股票池: {len(stock_pool)}只")

# 特征提取（简化版）
def extract_features(df, i):
    if i < 30 or i >= len(df):
        return None
    
    row = df.iloc[i]
    close = row['close']
    
    feat = {
        'pct_chg': row['pct_chg'],
        'ma5_ratio': close / row['ma5'] if row['ma5'] > 0 else 1,
        'ma10_ratio': close / row['ma10'] if row['ma10'] > 0 else 1,
        'ma20_ratio': close / row['ma20'] if row['ma20'] > 0 else 1,
        'rsi6': row['rsi6'] if pd.notna(row['rsi6']) else 50,
        'macd': row['macd'] if pd.notna(row['macd']) else 0,
    }
    
    return feat

# 训练模型
print("\n训练模型...")
models = {}
for code in stock_pool:
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
        if len(df) < 100:
            continue
        
        # 生成训练数据
        features = []
        for i in range(60, len(df)-3):
            feat = extract_features(df, i)
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

# 分析当前股票
print("\n分析股票...")
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
        
        pred = models[code].predict_proba(pd.DataFrame([feat]))[0]
        score = int(pred[1] * 100)
        
        latest = df.iloc[0]
        name = STOCK_NAMES.get(code, code)
        
        # 生成买卖建议
        advice = generate_advice(score, latest)
        
        stocks_analysis.append({
            'code': code,
            'name': name,
            'score': score,
            'close': round(latest['close'], 2),
            'pct_chg': round(latest['pct_chg'], 2),
            'volume': int(latest['volume']),
            'date': latest['date'],
            'rsi6': round(latest.get('rsi6', 50), 1),
            'macd': round(latest.get('macd', 0), 2),
            'advice': advice,
            'buy_signal': score >= 60,
            'sell_signal': score < 15,
        })
        
    except:
        continue

conn.close()

# 持仓分析
print("\n持仓分析...")
holdings_analysis = []
total_profit = 0

for h in HOLDINGS:
    code = h['code']
    # 获取当前价格
    try:
        conn = sqlite3.connect(DB_PATH)
        latest = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date DESC LIMIT 1", conn)
        conn.close()
        
        if len(latest) > 0:
            current_price = latest.iloc[0]['close']
            profit = (current_price - h['buy_price']) / h['buy_price'] * 100
            hold_days = (datetime.now() - pd.to_datetime(h['buy_date'])).days
            
            # 匹配分析结果
            analysis = next((s for s in stocks_analysis if s['code'] == code), None)
            score = analysis['score'] if analysis else 50
            
            holding_advice = generate_holding_advice(profit, score, hold_days)
            
            holdings_analysis.append({
                'code': code,
                'name': STOCK_NAMES.get(code, code),
                'shares': h['shares'],
                'buy_price': h['buy_price'],
                'current_price': round(current_price, 2),
                'profit': round(profit, 2),
                'hold_days': hold_days,
                'score': score,
                'advice': holding_advice,
            })
            
            total_profit += profit * h['shares'] * h['buy_price'] / 100
            
    except:
        pass

# 市场分析
market_analysis = generate_market_analysis(stocks_analysis)

# 输出JSON
result = {
    'version': '3.2',
    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'stocks': stocks_analysis,
    'holdings': holdings_analysis,
    'total_profit': round(total_profit, 2),
    'market_analysis': market_analysis,
    'statistics': {
        'total': len(stocks_analysis),
        'buy_count': len([s for s in stocks_analysis if s['score'] >= 60]),
        'sell_count': len([s for s in stocks_analysis if s['score'] < 15]),
        'watch_count': len([s for s in stocks_analysis if 15 <= s['score'] < 60]),
        'avg_score': round(sum(s['score'] for s in stocks_analysis) / len(stocks_analysis), 1) if stocks_analysis else 0,
        'high_score_count': len([s for s in stocks_analysis if s['score'] >= 70]),
    }
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✓ 分析完成: {len(stocks_analysis)}只股票")
print(f"✓ 买入推荐: {result['statistics']['buy_count']}只")
print(f"✓ 卖出建议: {result['statistics']['sell_count']}只")
print(f"✓ 持仓盈亏: {result['total_profit']:.2f}元")
print(f"✓ 输出文件: {OUTPUT_JSON}")

print("\n" + "=" * 70)
print("TOP5 买入推荐:")
print("=" * 70)
for s in sorted(stocks_analysis, key=lambda x: -x['score'])[:5]:
    print(f"  {s['name']}: 评分{s['score']} | {s['close']}元 | {s['advice']}")

print("\n✓ v3.2增强版分析完成！")
print("请打开 index_v3.html 查看完整界面")