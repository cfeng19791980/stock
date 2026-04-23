# -*- coding: utf-8 -*-
"""
大盘走势权重回测对比
目标: 测试加入大盘调整后命中率提升
方法: 多轮回测，对比不同参数效果
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import pandas as pd
import xgboost as xgb
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

print("=" * 70)
print("大盘走势权重回测对比")
print("=" * 70)

# 加载股票池
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
print(f"股票池: {len(stock_pool)}只")

# 连接数据库
conn = sqlite3.connect(DB_PATH)

# ========== 回测配置 ==========

# 参数组合测试
param_configs = [
    {'name': '无大盘调整', 'factor': 1.0, 'threshold': 60},
    {'name': '保守调整(5%权重)', 'factor_range': [(3, 1.05), (1, 1.02), (-1, 1.0), (-3, 0.98), (-999, 0.95)], 'threshold': 60},
    {'name': '中等调整(10%权重)', 'factor_range': [(3, 1.10), (1, 1.05), (-1, 1.0), (-3, 0.95), (-999, 0.90)], 'threshold': 60},
    {'name': '激进调整(15%权重)', 'factor_range': [(3, 1.15), (1, 1.08), (-1, 1.0), (-3, 0.92), (-999, 0.85)], 'threshold': 60},
    {'name': '中等调整+阈值提升', 'factor_range': [(3, 1.10), (1, 1.05), (-1, 1.0), (-3, 0.95), (-999, 0.90)], 'threshold_dynamic': True},
]

# ========== 工具函数 ==========

def get_market_factor(market_pct, factor_range):
    """根据涨幅获取调整因子"""
    for threshold, factor in factor_range:
        if market_pct >= threshold:
            return factor
    return factor_range[-1][1]

def get_market_pct(date, conn):
    """获取指定日期的大盘5日涨跌幅"""
    try:
        df = pd.read_sql(
            f"SELECT * FROM index_daily WHERE code='sh.000300' AND date <= '{date}' ORDER BY date DESC LIMIT 5",
            conn
        )
        if len(df) < 5:
            return 0
        
        first_close = df.iloc[-1]['close']
        last_close = df.iloc[0]['close']
        return (last_close - first_close) / first_close * 100
    except:
        return 0

def extract_features(df, i):
    """提取特征"""
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

# ========== 训练基础模型 ==========

print("\n训练基础XGBoost模型...")
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

print(f"已训练模型: {len(models)}个")

# ========== 回测对比 ==========

print("\n" + "=" * 70)
print("回测区间: 2025-01-01 ~ 2026-04-10")
print("=" * 70)

backtest_start = '2025-01-01'
backtest_end = '2026-04-10'

results = []

for config in param_configs:
    print(f"\n测试配置: {config['name']}")
    
    total_signals = 0
    correct_signals = 0
    total_profit = 0
    
    for code in models:
        try:
            df = pd.read_sql(
                f"SELECT * FROM daily_price WHERE code='{code}' AND date >= '{backtest_start}' AND date <= '{backtest_end}' ORDER BY date",
                conn
            )
            if len(df) < 30:
                continue
            
            for i in range(len(df) - 3):
                date = df.iloc[i]['date']
                feat = extract_features(df.iloc[::-1], len(df)-i-1)
                if not feat:
                    continue
                
                # 基础评分
                pred = models[code].predict_proba(pd.DataFrame([feat]))[0]
                base_score = int(pred[1] * 100)
                
                # 大盘调整
                if 'factor_range' in config:
                    market_pct = get_market_pct(date, conn)
                    factor = get_market_factor(market_pct, config['factor_range'])
                    adjusted_score = min(100, int(base_score * factor))
                else:
                    adjusted_score = base_score
                
                # 动态阈值
                if config.get('threshold_dynamic'):
                    market_pct = get_market_pct(date, conn)
                    if market_pct >= 3:
                        threshold = 55  # 强势降低阈值
                    elif market_pct >= 1:
                        threshold = 58
                    elif market_pct >= -1:
                        threshold = 60
                    elif market_pct >= -3:
                        threshold = 65  # 弱势提高阈值
                    else:
                        threshold = 70
                else:
                    threshold = config['threshold']
                
                # 买入信号
                if adjusted_score >= threshold:
                    close = df.iloc[i]['close']
                    close_3d = df.iloc[i+3]['close']
                    profit_pct = (close_3d - close) / close * 100
                    
                    total_signals += 1
                    if profit_pct >= 3:
                        correct_signals += 1
                    total_profit += profit_pct
        
        except:
            continue
    
    # 计算指标
    hit_rate = correct_signals / total_signals * 100 if total_signals > 0 else 0
    avg_profit = total_profit / total_signals if total_signals > 0 else 0
    
    results.append({
        'config': config['name'],
        'signals': total_signals,
        'correct': correct_signals,
        'hit_rate': round(hit_rate, 2),
        'avg_profit': round(avg_profit, 2),
        'total_profit': round(total_profit, 2),
    })
    
    print(f"  信号数: {total_signals}")
    print(f"  命中数: {correct_signals}")
    print(f"  命中率: {hit_rate:.2f}%")
    print(f"  平均收益: {avg_profit:.2f}%")
    print(f"  总收益: {total_profit:.2f}%")

# ========== 细粒度参数调优 ==========

print("\n" + "=" * 70)
print("细粒度参数调优")
print("=" * 70)

fine_configs = [
    # 测试不同权重强度
    {'name': '权重8%', 'factor_range': [(3, 1.08), (1, 1.04), (-1, 1.0), (-3, 0.96), (-999, 0.92)], 'threshold': 60},
    {'name': '权重12%', 'factor_range': [(3, 1.12), (1, 1.06), (-1, 1.0), (-3, 0.94), (-999, 0.88)], 'threshold': 60},
    
    # 测试不同阈值
    {'name': '中等权重+阈值55', 'factor_range': [(3, 1.10), (1, 1.05), (-1, 1.0), (-3, 0.95), (-999, 0.90)], 'threshold': 55},
    {'name': '中等权重+阈值65', 'factor_range': [(3, 1.10), (1, 1.05), (-1, 1.0), (-3, 0.95), (-999, 0.90)], 'threshold': 65},
    
    # 测试不对称调整（弱市影响更大）
    {'name': '不对称-弱市重罚', 'factor_range': [(3, 1.08), (1, 1.04), (-1, 1.0), (-3, 0.90), (-999, 0.80)], 'threshold': 60},
    
    # 测试强市轻奖+弱市重罚
    {'name': '轻奖重罚', 'factor_range': [(3, 1.05), (1, 1.03), (-1, 1.0), (-3, 0.92), (-999, 0.85)], 'threshold': 60},
]

for config in fine_configs:
    print(f"\n测试: {config['name']}")
    
    total_signals = 0
    correct_signals = 0
    total_profit = 0
    
    for code in models:
        try:
            df = pd.read_sql(
                f"SELECT * FROM daily_price WHERE code='{code}' AND date >= '{backtest_start}' AND date <= '{backtest_end}' ORDER BY date",
                conn
            )
            if len(df) < 30:
                continue
            
            for i in range(len(df) - 3):
                date = df.iloc[i]['date']
                feat = extract_features(df.iloc[::-1], len(df)-i-1)
                if not feat:
                    continue
                
                pred = models[code].predict_proba(pd.DataFrame([feat]))[0]
                base_score = int(pred[1] * 100)
                
                market_pct = get_market_pct(date, conn)
                factor = get_market_factor(market_pct, config['factor_range'])
                adjusted_score = min(100, int(base_score * factor))
                
                threshold = config['threshold']
                
                if adjusted_score >= threshold:
                    close = df.iloc[i]['close']
                    close_3d = df.iloc[i+3]['close']
                    profit_pct = (close_3d - close) / close * 100
                    
                    total_signals += 1
                    if profit_pct >= 3:
                        correct_signals += 1
                    total_profit += profit_pct
        except:
            continue
    
    hit_rate = correct_signals / total_signals * 100 if total_signals > 0 else 0
    avg_profit = total_profit / total_signals if total_signals > 0 else 0
    
    results.append({
        'config': config['name'],
        'signals': total_signals,
        'correct': correct_signals,
        'hit_rate': round(hit_rate, 2),
        'avg_profit': round(avg_profit, 2),
        'total_profit': round(total_profit, 2),
    })
    
    print(f"  命中率: {hit_rate:.2f}% | 平均收益: {avg_profit:.2f}%")

conn.close()

# ========== 结果汇总 ==========

print("\n" + "=" * 70)
print("回测结果汇总")
print("=" * 70)

# 按命中率排序
results.sort(key=lambda x: x['hit_rate'], reverse=True)

print(f"\n{'配置名称':<30} {'信号数':>8} {'命中率':>8} {'平均收益':>10}")
print("-" * 70)
for r in results:
    print(f"{r['config']:<30} {r['signals']:>8} {r['hit_rate']:>7.2f}% {r['avg_profit']:>9.2f}%")

# 找最优配置
best = results[0]
print("\n" + "=" * 70)
print(f"最优配置: {best['config']}")
print(f"命中率提升: {results[-1]['hit_rate']:.2f}% → {best['hit_rate']:.2f}% (+{best['hit_rate'] - results[-1]['hit_rate']:.2f}%)")
print("=" * 70)

# 保存结果
with open(r'e:\csi10\market_backtest_result.json', 'w', encoding='utf-8') as f:
    json.dump({
        'test_time': datetime.now().isoformat(),
        'backtest_period': f"{backtest_start} ~ {backtest_end}",
        'stock_count': len(models),
        'results': results,
        'best_config': best,
    }, f, ensure_ascii=False, indent=2)

print(f"\n结果已保存: e:\\csi10\\market_backtest_result.json")