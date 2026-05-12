# -*- coding: utf-8 -*-
"""大盘权重深度测试 - 分析弱势市场效果"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3, pandas as pd, xgboost as xgb, json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DB = r'E:\股票\csi500_data\stocks.db'
POOL = pd.read_csv(r'e:\csi10\波段股票Top30.csv')['股票代码'].tolist()

conn = sqlite3.connect(DB)
print("=" * 70)
print("大盘权重深度测试")
print("=" * 70)

# 分析大盘走势分布
print("\n大盘走势分布分析:")
df_market = pd.read_sql("SELECT * FROM index_daily WHERE code='sh.000300' ORDER BY date", conn)
df_market['ma5'] = df_market['close'].rolling(5).mean()
df_market['pct_5d'] = (df_market['close'] - df_market['ma5'].shift(5)) / df_market['ma5'].shift(5) * 100

# 统计市场状态分布（2025-2026）
df_recent = df_market[df_market['date'] >= '2025-01-01']
strong_days = len(df_recent[df_recent['pct_5d'] >= 3])
weak_days = len(df_recent[df_recent['pct_5d'] < -3])
neutral_days = len(df_recent[(df_recent['pct_5d'] >= -1) & (df_recent['pct_5d'] <= 1)])

print(f"强势天数(≥+3%): {strong_days}天")
print(f"弱势天数(<-3%): {weak_days}天")
print(f"震荡天数: {neutral_days}天")

if weak_days < 10:
    print("\n⚠️ 发现问题: 回测区间弱势天数太少，无法验证大盘调整在弱市的效果！")
    print("建议: 扩大回测区间到2024年，包含更多弱势市场")

# 扩大回测区间到2024年
print("\n" + "=" * 70)
print("扩大回测区间: 2024-01-01 ~ 2026-03-31")
print("=" * 70)

# 训练模型
models = {}
for code in POOL:
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
        if len(df) < 150: continue
        
        feats = []
        for i in range(60, len(df)-3):
            r = df.iloc[i]
            f = {
                'pct_chg': r['pct_chg'],
                'ma5_ratio': r['close']/r['ma5'] if r['ma5']>0 else 1,
                'ma10_ratio': r['close']/r['ma10'] if r['ma10']>0 else 1,
                'rsi6': r.get('rsi6',50), 'macd': r.get('macd',0)
            }
            rise = (df.iloc[i+3]['close'] - r['close'])/r['close'] if r['close']>0 else 0
            f['target'] = 1 if rise >= 0.03 else 0
            feats.append(f)
        
        if len(feats) < 50: continue
        ds = pd.DataFrame(feats)
        m = xgb.XGBClassifier(n_estimators=80, max_depth=4, verbosity=0)
        m.fit(ds.drop('target',axis=1), ds['target'])
        models[code] = m
    except: continue

print(f"训练完成: {len(models)}个模型")

def get_market_pct(date):
    try:
        df = pd.read_sql(f"SELECT * FROM index_daily WHERE code='sh.000300' AND date <= '{date}' ORDER BY date DESC LIMIT 5", conn)
        if len(df) < 5: return 0
        return (df.iloc[0]['close'] - df.iloc[-1]['close'])/df.iloc[-1]['close']*100
    except: return 0

# 测试不同阈值和调整强度
configs = [
    {'name':'基准(无调整)阈值60', 'factors':[(99,1.0)], 'th':60},
    {'name':'基准阈值70', 'factors':[(99,1.0)], 'th':70},
    {'name':'基准阈值80', 'factors':[(99,1.0)], 'th':80},
    {'name':'中调整+动态阈值', 'factors':[(3,1.10),(1,1.05),(-1,1),(-3,0.95),(-99,0.90)], 'th_dyn':True},
    {'name':'不对称弱市重罚', 'factors':[(3,1.05),(1,1.02),(-1,1),(-3,0.85),(-99,0.75)], 'th':70},
    {'name':'极重调整+阈值80', 'factors':[(3,1.10),(1,1.05),(-1,1),(-3,0.80),(-99,0.70)], 'th':80},
]

def get_factor(pct, factors):
    for t, f in factors:
        if pct >= t: return f
    return factors[-1][1]

# 分市场状态统计
results_by_market = {'强势':{}, '震荡':{}, '弱势':{}}

for cfg in configs:
    print(f"\n测试: {cfg['name']}")
    
    # 分市场状态统计
    stats = {'强势':{'sig':0,'hit':0,'prof':0}, '震荡':{'sig':0,'hit':0,'prof':0}, '弱势':{'sig':0,'hit':0,'prof':0}}
    
    for code in models:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '2024-01-01' AND '2026-03-31' ORDER BY date", conn)
        
        for i in range(len(df)-3):
            r = df.iloc[i]
            f = {'pct_chg':r['pct_chg'], 'ma5_ratio':r['close']/r['ma5'] if r['ma5']>0 else 1, 'ma10_ratio':r['close']/r['ma10'] if r['ma10']>0 else 1, 'rsi6':r.get('rsi6',50), 'macd':r.get('macd',0)}
            
            score = int(models[code].predict_proba(pd.DataFrame([f]))[0][1]*100)
            m_pct = get_market_pct(r['date'])
            factor = get_factor(m_pct, cfg['factors'])
            adj_score = min(100, int(score * factor))
            
            if cfg.get('th_dyn'):
                th = 55 if m_pct>=3 else 58 if m_pct>=1 else 60 if m_pct>=-1 else 65 if m_pct>=-3 else 70
            else:
                th = cfg['th']
            
            if adj_score >= th:
                ret = (df.iloc[i+3]['close'] - r['close'])/r['close']*100
                
                # 分类统计
                if m_pct >= 3:
                    market = '强势'
                elif m_pct >= -1:
                    market = '震荡'
                else:
                    market = '弱势'
                
                stats[market]['sig'] += 1
                if ret >= 3: stats[market]['hit'] += 1
                stats[market]['prof'] += ret
    
    # 计算各市场命中率
    for market in ['强势','震荡','弱势']:
        if stats[market]['sig'] > 0:
            hit = stats[market]['hit']/stats[market]['sig']*100
            avg = stats[market]['prof']/stats[market]['sig']
            results_by_market[market][cfg['name']] = {'sig':stats[market]['sig'], 'hit':round(hit,2), 'avg':round(avg,2)}
    
    total_sig = sum(s['sig'] for s in stats.values())
    total_hit = sum(s['hit'] for s in stats.values())
    print(f"  总信号:{total_sig} 总命中:{total_hit}")

conn.close()

# 分市场对比
print("\n" + "=" * 70)
print("分市场状态命中率对比")
print("=" * 70)

for market in ['强势','震荡','弱势']:
    print(f"\n{market}市场:")
    print(f"{'配置':<30} {'信号':>6} {'命中率':>8} {'收益':>8}")
    print("-" * 50)
    for name, data in results_by_market[market].items():
        print(f"{name:<30} {data['sig']:>6} {data['hit']:>7.2f}% {data['avg']:>7.2f}%")

# 找最优配置（看弱势市场）
print("\n" + "=" * 70)
print("弱势市场最优配置")
print("=" * 70)

if results_by_market['弱势']:
    weak_results = sorted(results_by_market['弱势'].items(), key=lambda x: x[1]['hit'], reverse=True)
    best_weak = weak_results[0]
    print(f"最优配置: {best_weak[0]}")
    print(f"弱势市场命中率: {best_weak[1]['hit']}%")
    print(f"弱势市场平均收益: {best_weak[1]['avg']}%")

# 保存结果
json.dump({
    'test_time':datetime.now().isoformat(),
    'period':'2024-01-01 ~ 2026-03-31',
    'results_by_market':results_by_market,
}, open(r'e:\csi10\market_segment_test.json','w'), ensure_ascii=False, indent=2)

print(f"\n结果已保存")