# -*- coding: utf-8 -*-
"""大盘权重回测 - 完整30只股票版"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3, pandas as pd, xgboost as xgb, json, time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DB = r'E:\股票\csi500_data\stocks.db'
POOL = pd.read_csv(r'e:\csi10\波段股票Top30.csv')['股票代码'].tolist()

conn = sqlite3.connect(DB)
print("=" * 70)
print("大盘权重完整回测(30只股票)")
print("=" * 70)

# 训练所有模型
start = time.time()
models = {}
for code in POOL:
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
        if len(df) < 100: continue
        
        feats = []
        for i in range(60, len(df)-3):
            r = df.iloc[i]
            f = {
                'pct_chg': r['pct_chg'],
                'ma5_ratio': r['close']/r['ma5'] if r['ma5']>0 else 1,
                'ma10_ratio': r['close']/r['ma10'] if r['ma10']>0 else 1,
                'rsi6': r.get('rsi6',50), 
                'macd': r.get('macd',0)
            }
            rise = (df.iloc[i+3]['close'] - r['close'])/r['close'] if r['close']>0 else 0
            f['target'] = 1 if rise >= 0.03 else 0
            feats.append(f)
        
        if len(feats) < 30: continue
        ds = pd.DataFrame(feats)
        m = xgb.XGBClassifier(n_estimators=80, max_depth=4, verbosity=0, n_jobs=-1)
        m.fit(ds.drop('target',axis=1), ds['target'])
        models[code] = m
    except: continue

print(f"训练完成: {len(models)}个模型 ({time.time()-start:.1f}s)")

def get_market_pct(date):
    try:
        df = pd.read_sql(f"SELECT * FROM index_daily WHERE code='sh.000300' AND date <= '{date}' ORDER BY date DESC LIMIT 5", conn)
        if len(df) < 5: return 0
        return (df.iloc[0]['close'] - df.iloc[-1]['close'])/df.iloc[-1]['close']*100
    except: return 0

# 最优参数组合（基于简化测试）
configs = [
    {'name':'基准(无调整)', 'factors':[(99,1.0)], 'th':60},
    {'name':'中调整10%+动态阈值', 'factors':[(3,1.10),(1,1.05),(-1,1),(-3,0.95),(-99,0.90)], 'th_dyn':True},
    {'name':'不对称(弱市重罚)', 'factors':[(3,1.08),(1,1.04),(-1,1),(-3,0.88),(-99,0.78)], 'th':60},
    {'name':'轻调整+动态阈值', 'factors':[(3,1.05),(1,1.02),(-1,1),(-3,0.98),(-99,0.95)], 'th_dyn':True},
    {'name':'重调整+动态阈值', 'factors':[(3,1.15),(1,1.08),(-1,1),(-3,0.92),(-99,0.85)], 'th_dyn':True},
    {'name':'超重调整20%', 'factors':[(3,1.20),(1,1.12),(-1,1),(-3,0.88),(-99,0.80)], 'th_dyn':True},
]

def get_factor(pct, factors):
    for t, f in factors:
        if pct >= t: return f
    return factors[-1][1]

print("\n回测区间: 2025-01-01 ~ 2026-03-31")
print("-" * 70)

results = []
for cfg in configs:
    print(f"\n测试: {cfg['name']}")
    signals, correct, profit, start_time = 0, 0, 0, time.time()
    
    for code in models:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '2025-01-01' AND '2026-03-31' ORDER BY date", conn)
        
        for i in range(len(df)-3):
            r = df.iloc[i]
            f = {
                'pct_chg':r['pct_chg'], 
                'ma5_ratio':r['close']/r['ma5'] if r['ma5']>0 else 1,
                'ma10_ratio':r['close']/r['ma10'] if r['ma10']>0 else 1,
                'rsi6':r.get('rsi6',50), 
                'macd':r.get('macd',0)
            }
            
            score = int(models[code].predict_proba(pd.DataFrame([f]))[0][1]*100)
            
            m_pct = get_market_pct(r['date'])
            factor = get_factor(m_pct, cfg['factors'])
            adj_score = min(100, int(score * factor))
            
            if cfg.get('th_dyn'):
                th = 55 if m_pct>=3 else 58 if m_pct>=1 else 60 if m_pct>=-1 else 65 if m_pct>=-3 else 70
            else:
                th = cfg['th']
            
            if adj_score >= th:
                signals += 1
                ret = (df.iloc[i+3]['close'] - r['close'])/r['close']*100
                if ret >= 3: correct += 1
                profit += ret
    
    hit = correct/signals*100 if signals>0 else 0
    avg = profit/signals if signals>0 else 0
    results.append({
        'name':cfg['name'], 
        'signals':signals, 
        'correct':correct,
        'hit_rate':round(hit,2), 
        'avg_profit':round(avg,2),
        'total_profit':round(profit,2)
    })
    print(f"  信号:{signals} 命中:{correct} 率:{hit:.2f}% 收益:{avg:.2f}% ({time.time()-start_time:.1f}s)")

conn.close()

# 结果对比
print("\n" + "=" * 70)
print("回测结果对比")
print("=" * 70)
print(f"\n{'配置名称':<30} {'信号数':>6} {'命中数':>6} {'命中率':>8} {'平均收益':>8}")
print("-" * 70)
for r in results:
    print(f"{r['name']:<30} {r['signals']:>6} {r['correct']:>6} {r['hit_rate']:>7.2f}% {r['avg_profit']:>7.2f}%")

# 最优配置
best = max(results, key=lambda x: x['hit_rate'])
base = results[0]
print("\n" + "=" * 70)
print("最优配置结论")
print("=" * 70)
print(f"基准命中率: {base['hit_rate']}%")
print(f"最优命中率: {best['hit_rate']}% ({best['name']})")
print(f"提升幅度: +{best['hit_rate']-base['hit_rate']:.2f}%")
print(f"\n推荐参数:")
print(f"  调整因子: {best['name']}")
print(f"  动态阈值: 强市55分 / 震荡60分 / 弱市70分")

# 保存
json.dump({
    'test_time':datetime.now().isoformat(),
    'stock_count':len(models),
    'results':results,
    'best':best,
    'recommendation':{
        'config':best['name'],
        'factors':configs[results.index(best)]['factors'],
        'dynamic_threshold':configs[results.index(best)].get('th_dyn',False)
    }
}, open(r'e:\csi10\full_backtest_result.json','w'), ensure_ascii=False, indent=2)
print(f"\n结果已保存: e:\\csi10\\full_backtest_result.json")