# -*- coding: utf-8 -*-
"""
波段股票分析系统 v4.0 - 持仓管理版
功能：
1. 用户录入持仓：代码+数量+成本（自动映射名称）
2. 分析引擎读取持仓，给出指导建议
3. 仅分析30只股票池范围内的股票
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

def generate_trade_advice(score, adjusted_score=None, market_status=None, factor=None):
    """生成买卖建议（非持仓股）- 包含大盘调整信息"""
    adj_info = ""
    if adjusted_score and adjusted_score != score:
        adj_info = f"，大盘调整后{adjusted_score}分"
    if market_status and factor:
        adj_info += f"（{market_status}，因子{factor:.2f}）"
    
    if score >= 80:
        return f"强烈推荐买入！评分{score}分{adj_info}，高质量标的。建议优先配置15-20%仓位。"
    elif score >= 70:
        return f"推荐买入。评分{score}分{adj_info}，上涨概率高。建议分批建仓，首次10%。"
    elif score >= 60:
        return f"可考虑买入。评分{score}分{adj_info}，达到买入阈值。建议T+1策略买入。"
    elif score >= 40:
        return f"暂不买入。评分{score}分{adj_info}，未达买入阈值。建议观察等待。"
    elif score >= 15:
        return f"观望。评分{score}分{adj_info}，中性区间。暂不操作。"
    else:
        return f"建议卖出！评分仅{score}分{adj_info}，跌幅概率{100-score}%。如有持仓建议止损。"

def generate_holding_advice(profit, score, days, holding):
    """生成持仓建议（持仓股）"""
    shares = holding['shares']
    buyPrice = holding['buyPrice']
    
    if profit >= 25:
        return f"✅ 已达止盈线(25%)！盈利{profit:.1f}%。建议分批卖出锁定收益。"
    elif profit >= 15:
        return f"盈利可观({profit:.1f}%)。建议部分止盈，卖出30-50%仓位。"
    elif profit >= 5:
        return f"小幅盈利({profit:.1f}%)。持仓{days}天。可继续持有。"
    elif profit >= -5:
        return f"轻微亏损({profit:.1f}%)。继续观察，止损线-10%。"
    elif profit >= -10:
        return f"⚠️ 接近止损线(-10%)！亏损{profit:.1f}%。密切关注。"
    else:
        return f"🔴 触发止损线！亏损{profit:.1f}%。建议果断止损。"

def generate_market_analysis(stocks):
    """生成市场分析"""
    buy_count = len([s for s in stocks if s['buy_signal']])
    sell_count = len([s for s in stocks if s['sell_signal']])
    avg_score = sum(s['score'] for s in stocks) / len(stocks) if stocks else 50
    
    if buy_count >= 8:
        trend = "多头市场"
    elif sell_count >= 8:
        trend = "空头市场"
    else:
        trend = "震荡市场"
    
    return f"{trend}。平均评分{avg_score:.0f}分，{buy_count}只买入信号。"

# 配置 - 使用环境变量DATA_DIR或相对路径（便携版兼容）
import os
DATA_DIR = os.environ.get('DATA_DIR', os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DATA_DIR, 'stocks.db')
CSV_PATH = os.path.join(BASE_DIR, '波段股票Top30.csv')
OUTPUT_JSON = os.path.join(DATA_DIR, 'result.json')
HOLDINGS_JSON = os.path.join(DATA_DIR, 'holdings.json')

# 股票名称映射（30只股票池）
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

# ========== 大盘走势功能（v5合并）==========

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
        
        # 不对称调整因子
        if market_pct >= 3:
            factor = 1.05; status = "强势市场"; threshold = 55
        elif market_pct >= 1:
            factor = 1.02; status = "偏强市场"; threshold = 58
        elif market_pct >= -1:
            factor = 1.0; status = "震荡市场"; threshold = 60
        elif market_pct >= -3:
            factor = 0.85; status = "偏弱市场"; threshold = 65
        else:
            factor = 0.75; status = "弱势市场"; threshold = 70
        
        # 最近5日走势
        recent = df[['date', 'close', 'pct_chg']].iloc[::-1].to_dict('records')
        return factor, market_pct, status, threshold, recent
    except Exception as e:
        return 1.0, 0, "大盘数据异常", 60, []

def adjust_score(original_score, factor):
    """调整评分（大盘权重）"""
    adjusted = int(original_score * factor)
    return min(100, max(0, adjusted))

print("=" * 70)
print("波段股票分析系统 v4.0 - 持仓管理版 + 大盘走势")
print("股票池范围：30只波段股票")
print("=" * 70)

# 加载股票池
conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
print(f"✓ 股票池: {len(stock_pool)}只（固定范围）")

# ========== 获取大盘状态 ==========
factor, market_pct, market_status, threshold, recent_5d = get_market_adjustment(conn)
print(f"\n大盘状态: {market_status}, 5日涨跌: {market_pct:.2f}%")
if recent_5d:
    print("最近5日走势:")
    for r in recent_5d:
        print(f"  {r['date']}: {r['close']:.2f}, 涨跌{r['pct_chg']:.2f}%")

# 加载用户持仓（从holdings.json）
print("\n加载用户持仓数据...")
holdings = []
try:
    with open(HOLDINGS_JSON, 'r', encoding='utf-8') as f:
        holdings_data = json.load(f)
        # 过滤：仅保留股票池范围内的持仓
        for h in holdings_data:
            if h['code'] in stock_pool:
                h['name'] = STOCK_NAMES.get(h['code'], h['code'])
                holdings.append(h)
                print(f"  ✓ {h['name']}: {h['shares']}股, 成本{h['buyPrice']}元")
            else:
                print(f"  ⚠️ {h['code']}不在股票池范围，已过滤")
except:
    print("  暂无持仓数据（可在界面添加）")

print(f"✓ 有效持仓: {len(holdings)}只（股票池范围内）")

# 特征提取
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

# 训练模型
print("\n训练模型（仅股票池30只）...")
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

print(f"✓ 已训练: {len(models)}个模型（仅股票池）")

# 分析股票池
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
        pred = models[code].predict_proba(pd.DataFrame([feat]))[0]
        score = int(pred[1] * 100)
        latest = df.iloc[0]
        name = STOCK_NAMES.get(code, code)
        
        # 检查是否持仓
        holding = next((h for h in holdings if h['code'] == code), None)
        
        if holding:
            # 持仓股：生成持仓建议
            current_price = latest['close']
            profit = (current_price - holding['buyPrice']) / holding['buyPrice'] * 100
            hold_days = (datetime.now() - pd.to_datetime(holding['buyDate'])).days
            advice = generate_holding_advice(profit, score, hold_days, holding)
        else:
            # 非持仓股：生成买卖建议（包含大盘调整信息）
            adjusted = adjust_score(score, factor)
            advice = generate_trade_advice(score, adjusted, market_status, factor)
        
        # 计算建议买入价和卖出价
        buy_price = round(latest['close'] * 0.97, 2)  # 建议买入价：现价-3%
        sell_price = round(latest['close'] * 1.10, 2)  # 建议卖出价：现价+10%（目标止盈）
        stop_price = round(latest['close'] * 0.90, 2)  # 止损价：现价-10%
        
        stocks_analysis.append({
            'code': code,
            'name': name,
            'score': score,
            'adjusted_score': adjust_score(score, factor),  # 大盘调整后评分
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
            'buy_signal': bool(adjust_score(score, factor) >= threshold and not holding),  # 使用调整后评分
            'sell_signal': bool(score < 15 or (holding and profit <= -10)),
            'is_holding': bool(holding is not None),
        })
    except:
        continue

conn.close()

# 持仓统计
print("\n持仓指导汇总...")
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
            'advice': analysis['advice'],
        })

print(f"  总成本: {total_cost:.2f}元")
print(f"  当前市值: {total_value:.2f}元")
print(f"  持仓盈亏: {total_profit:.2f}元 ({(total_value-total_cost)/total_cost*100:.1f}%)") if total_cost > 0 else print(f"  持仓盈亏: {total_profit:.2f}元")

# 输出JSON
result = {
    'version': '4.0',
    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'stock_pool_size': len(stock_pool),
    # 大盘信息（v5合并）
    'market': {
        'status': market_status,
        'pct_5d': round(market_pct, 2),
        'factor': factor,
        'threshold': threshold,
        'recent_5d': recent_5d,
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
        'watch_count': len([s for s in stocks_analysis if not s['is_holding'] and 15 <= s['score'] < 60]),
    },
    'market_analysis': generate_market_analysis(stocks_analysis),
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✓ 分析完成: {len(stocks_analysis)}只股票（股票池范围内）")
print(f"✓ 买入推荐: {result['statistics']['buy_count']}只")
print(f"✓ 卖出建议: {result['statistics']['sell_count']}只")
print(f"✓ 输出文件: {OUTPUT_JSON}")

# 打印大盘调整示例
print("\n" + "=" * 70)
print("大盘调整评分示例:")
print("=" * 70)
sample_stocks = stocks_analysis[:5]
for s in sample_stocks:
    diff = s['adjusted_score'] - s['score']
    print(f"  {s['name']}: 原评分{s['score']} → 调整后{s['adjusted_score']} ({diff:+d})")

print(f"\n大盘调整: {market_status} | 因子{factor} | 阈值{threshold}分")

# 打印持仓指导
print("\n" + "=" * 70)
print("持仓指导建议：")
print("=" * 70)
for h in holdings_result:
    status = "✅" if h['profit'] >= 0 else "⚠️"
    print(f"{status} {h['name']}: 盈亏{h['profit']}% | 评分{h['score']} | {h['advice'][:50]}...")

# 打印买入推荐
print("\n" + "=" * 70)
print("买入推荐（非持仓股）：")
print("=" * 70)
for s in sorted([s for s in stocks_analysis if s['buy_signal']], key=lambda x: -x['score'])[:5]:
    print(f"  {s['name']}: 评分{s['score']} | {s['close']}元 | {s['advice'][:40]}...")

print("\n✓ v4.0持仓管理版分析完成！")
print("请打开 index_v4.html 查看持仓管理界面")

# ========== 建议生成函数（已在顶部定义）==========

# generate_trade_advice和generate_holding_advice已在文件顶部定义
# 此处保留generate_holding_advice作为补充版本（持仓专用）

def generate_holding_advice(profit, score, days, holding):
    """生成持仓建议（持仓股）"""
    shares = holding['shares']
    buyPrice = holding['buyPrice']
    
    if profit >= 25:
        return f"✅ 已达止盈线(25%)！盈利{profit:.1f}%，建议分批卖出锁定收益。当前盈利{profit:.1f}%×{shares}股=约{(profit/100)*shares*buyPrice:.0f}元。可先卖出50%，保留底仓。"
    
    elif profit >= 15:
        return f"盈利可观({profit:.1f}%)。建议部分止盈，卖出30-50%仓位约{int(shares*0.3)}-{int(shares*0.5)}股。评分{score}分，{'趋势向好可保留' if score >= 50 else '评分下降建议减仓'}。"
    
    elif profit >= 5:
        return f"小幅盈利({profit:.1f}%)。持仓{days}天，评分{score}分。{'可继续持有等待更高收益' if score >= 40 else '评分偏低注意风险'}。目标止盈25%。"
    
    elif profit >= -5:
        return f"轻微亏损({profit:.1f}%)。持仓{days}天，评分{score}分。{'继续观察等待反弹' if score >= 30 else '注意风险，若跌破-10%止损'}。止损线-10%。"
    
    elif profit >= -10:
        return f"⚠️ 接近止损线(-10%)！亏损{profit:.1f}%约{abs(profit/100)*shares*buyPrice:.0f}元。评分{score}分。建议密切关注，跌破-10%果断止损卖出{shares}股。"
    
    else:
        return f"🔴 触发止损线！亏损{profit:.1f}%超过-10%。建议果断卖出{shares}股止损，避免扩大损失。评分{score}分，趋势不利。"

def generate_market_analysis(stocks):
    """生成市场分析"""
    buy_count = len([s for s in stocks if s['buy_signal']])
    sell_count = len([s for s in stocks if s['sell_signal']])
    avg_score = sum(s['score'] for s in stocks) / len(stocks) if stocks else 50
    
    if buy_count >= 8:
        trend = "多头市场，买入信号较多"
    elif sell_count >= 8:
        trend = "空头市场，卖出信号较多"
    else:
        trend = "震荡市场，信号中性"
    
    return f"{trend}。平均评分{avg_score:.0f}分，{buy_count}只买入信号，{sell_count}只卖出信号。操作聚焦30只股票池，严格执行止损止盈纪律。"