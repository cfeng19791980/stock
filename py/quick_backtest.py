# -*- coding: utf-8 -*-
"""大盘权重回测 - 简化快速版"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3, pandas as pd, xgboost as xgb, json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DB = r'E:\股票\csi500_data\stocks.db'
POOL = pd.read_csv(r'e:\csi10\波段股票Top30.csv')['股票代码'].tolist()

conn = sqlite3.connect(DB)
print("=" * 60)
print("大盘权重回测(简化版)")
print("=" * 60)

# 只选5只代表性股票快速测试
test_codes = POOL[:5]  # 取前5只
print(f"测试股票: {len(test_codes)}只")

# 快速训练模型
models = {}
for code in test_codes:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
    if len(df) < 100: continue
    
    feats = []
    for i in range(60, len(df)-3):
        r = df.iloc[i]
        f = {
            'pct_chg': r['pct_chg'],
            'ma5_ratio': r['close']/r['ma5'] if r['ma5']>0 else 1,
            'rsi6': r.get('rsi6',50), 'macd': r.get('macd',0)
        }
        rise = (df.iloc[i+3]['close'] - r['close'])/r['close'] if r['close']>0 else 0
        f['target'] = 1 if rise >= 0.03 else 0
        feats.append(f)
    
    if len(feats) < 30: continue
    ds = pd.DataFrame(feats)
    m = xgb.XGBClassifier(n_estimators=50, max_depth=3, verbosity=0)
    m.fit(ds.drop('target',axis=1), ds['target'])
    models[code] = m

print(f"模型数: {len(models)}")

# 获取大盘数据函数
def get_market_pct(date):
    try:
        df = pd.read_sql(f"SELECT * FROM index_daily WHERE code='sh.000300' AND date <= '{date}' ORDER BY date DESC LIMIT 5", conn)
        if len(df) < 5: return 0
        return (df.iloc[0]['close'] - df.iloc[-1]['close'])/df.iloc[-1]['close']*100
    except: return 0

# 回测参数配置
configs = [
    {'name':'基准(无调整)', 'factors':[(99,1.0)], 'th':60},
    {'name':'轻调整5%', 'factors':[(3,1.05),(1,1.02),(-1,1),(-3,0.98),( -99,0.95)], 'th':60},
    {'name':'中调整10%', 'factors':[(3,1.10),(1,1.05),(-1,1),(-3,0.95),(-99,0.90)], 'th':60},
    {'name':'重调整15%', 'factors':[(3,1.15),(1,1.08),(-1,1),(-3,0.92),(-99,0.85)], 'th':60},
    {'name':'中调整+动态阈值', 'factors':[(3,1.10),(1,1.05),(-1,1),(-3,0.95),(-99,0.90)], 'th_dyn':True},
    {'name':'不对称(弱市重罚)', 'factors':[(3,1.08),(1,1.04),(-1,1),(-3,0.88),(-99,0.78)], 'th':60},
]

def get_factor(pct, factors):
    for t, f in factors:
        if pct >= t: return f
    return factors[-1][1]

print("\n回测区间: 2025-01-01 ~ 2026-03-31")
print("-" * 60)

results = []
for cfg in configs:
    signals, correct, profit = 0, 0, 0
    
    for code in models:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '2025-01-01' AND '2026-03-31' ORDER BY date", conn)
        
        for i in range(len(df)-3):
            r = df.iloc[i]
            f = {'pct_chg':r['pct_chg'], 'ma5_ratio':r['close']/r['ma5'] if r['ma5']>0 else 1, 'rsi6':r.get('rsi6',50), 'macd':r.get('macd',0)}
            
            score = int(models[code].predict_proba(pd.DataFrame([f]))[0][1]*100)
            
            # 大盘调整
            m_pct = get_market_pct(r['date'])
            factor = get_factor(m_pct, cfg['factors'])
            adj_score = min(100, int(score * factor))
            
            # 阈值
            if cfg.get('th_dyn'):
                th = 55 if m_pct>=3 else 58 if m_pct>=1 else 60 if m_pct>=-1 else 65 if m_pct>=-3 else 70
            else:
                th = cfg['th']
            
            # 买入判断
            if adj_score >= th:
                signals += 1
                ret = (df.iloc[i+3]['close'] - r['close'])/r['close']*100
                if ret >= 3: correct += 1
                profit += ret
    
    hit = correct/signals*100 if signals>0 else 0
    avg = profit/signals if signals>0 else 0
    results.append({'name':cfg['name'], 'sig':signals, 'hit':round(hit,2), 'avg':round(avg,2)})
    print(f"{cfg['name']:<25} 信号:{signals:>4} 命中:{hit:>6.2f}% 收益:{avg:>6.2f}%")

conn.close()

# 汇总
print("\n" + "=" * 60)
best = max(results, key=lambda x: x['hit'])
base = results[0]
print(f"基准命中率: {base['hit']}%")
print(f"最优命中率: {best['hit']}% ({best['name']})")
print(f"提升幅度: +{best['hit']-base['hit']:.2f}%")
print("=" * 60)

json.dump({'time':datetime.now().isoformat(),'results':results,'best':best}, 
          open(r'e:\csi10\quick_backtest.json','w'), ensure_ascii=False, indent=2)
print("\n结果已保存")