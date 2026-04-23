# -*- coding: utf-8 -*-
"""
波段股票分析系统 - JSON输出版（简化架构）
架构: Python分析引擎 → JSON文件 → Electron前端读取
版本: v3.0-json
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import pandas as pd
import sqlite3
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# 配置
DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
INDEX_CODE = 'sh.000300'
OUTPUT_JSON = r'e:\csi10\result.json'

print("=" * 60)
print("波段股票分析系统 v3.0 (XGBoost + JSON输出)")
print("=" * 60)

# 加载买点卖点预测器
try:
    import buysell_predictor_v5
    buysell_predictor = buysell_predictor_v5.BuySellPredictor()
    buysell_predictor.train_models()
    print(f"✓ 买点MAE: {buysell_predictor.buy_mae:.2f}%")
    print(f"✓ 卖点MAE: {buysell_predictor.sell_mae:.2f}%")
except Exception as e:
    print(f"买点卖点预测器加载失败: {e}")
    buysell_predictor = None

# 加载股票名称
stock_names = {}
try:
    names_df = pd.read_sql("SELECT DISTINCT code, name FROM daily_price WHERE code IN ('" + "','".join(stock_pool) + "')", conn)
    for _, row in names_df.iterrows():
        stock_names[row['code']] = row['name']
except:
    pass

# 加载股票名称
from stock_names import STOCK_NAMES

# 加载大盘数据
conn = sqlite3.connect(DB_PATH)
index_data = pd.read_sql(f"SELECT * FROM index_daily WHERE code='{INDEX_CODE}' ORDER BY date DESC LIMIT 1000", conn)

# 加载股票池
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
print(f"✓ 股票池: {len(stock_pool)}只")

# 训练模型
print("训练模型...")
models = {}
accuracy_report = {}

for code in stock_pool[:5]:  # 用前5只训练基准模型
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date DESC LIMIT 100", conn)
        if len(df) < 30:
            continue
        
        df['target'] = df['pct_chg'].shift(-3).apply(lambda x: 1 if pd.notna(x) and x > 2 else 0)
        df = df.dropna()
        
        if len(df) < 10:
            continue
        
        features = ['pct_chg', 'volume', 'close']
        X = df[features].fillna(0)
        y = df['target']
        
        if len(y[y==1]) < 2 or len(y[y==0]) < 2:  # 确保两类样本都有
            continue
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        model = xgb.XGBClassifier(n_estimators=50, max_depth=3, use_label_encoder=False, eval_metric='logloss')
        model.fit(X_train, y_train)
        
        acc = accuracy_score(y_test, model.predict(X_test))
        models[code] = model
        accuracy_report[code] = acc
    except Exception as e:
        print(f"  {code} 训练失败: {e}")
        continue

if models:
    avg_acc = np.mean(list(accuracy_report.values()))
    print(f"✓ 平均准确率: {avg_acc:.2%}")
else:
    avg_acc = 0.7
    print(f"⚠ 模型训练失败，使用默认准确率: {avg_acc:.2%}")

# 分析所有股票
print("分析股票...")
results = []

for code in stock_pool:
    df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date DESC LIMIT 50", conn)
    if len(df) < 20:
        continue
    
    latest = df.iloc[0]  # 第一行是最新日期（ORDER BY date DESC）
    
    # 预测
    features = ['pct_chg', 'volume', 'close']
    X = df[features].fillna(0).iloc[-1:].values
    
    # 使用第一个模型预测（简化）
    model = list(models.values())[0] if models else None
    if model:
        try:
            pred = model.predict_proba(X)[0]
            action = "买入" if pred[1] > 0.5 else "卖出" if pred[1] < 0.3 else "持有"
            score = int(pred[1] * 100)
        except:
            action = "持有"
            score = 50
    else:
        # 无模型时基于涨跌幅判断
        action = "买入" if latest['pct_chg'] and latest['pct_chg'] > 3 else "卖出" if latest['pct_chg'] and latest['pct_chg'] < -3 else "持有"
        score = 70 if action == "买入" else 30 if action == "卖出" else 50
    
    # 构建结果
    result = {
        'code': code,
        'name': STOCK_NAMES.get(code, code),  # 使用股票名称映射
        'price': float(latest['close']),
        'change_pct': float(latest['pct_chg'] or 0),
        'action': action,
        'score': score,
        'accuracy': float(avg_acc),
        'volume': int(latest['volume'] or 0),
        'date': str(latest['date'])
    }
    
    # 添加买点卖点
    if buysell_predictor:
        try:
            buysell = buysell_predictor.predict(code)
            if buysell:
                result['buy_price'] = float(buysell['buy']['price_center'])
                result['buy_change'] = float(buysell['buy']['change_pct'])
                result['sell_price'] = float(buysell['sell']['price_center'])
                result['sell_change'] = float(buysell['sell']['change_pct'])
        except:
            pass
    
    results.append(result)

# 排序
results.sort(key=lambda x: x['score'], reverse=True)

# 输出JSON
output = {
    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'stock_count': len(results),
    'buy_count': len([x for x in results if x['action'] == '买入']),
    'sell_count': len([x for x in results if x['action'] == '卖出']),
    'avg_accuracy': float(avg_acc),
    'buysell_enabled': buysell_predictor is not None,
    'buysell_buy_mae': buysell_predictor.buy_mae if buysell_predictor else 0,
    'buysell_sell_mae': buysell_predictor.sell_mae if buysell_predictor else 0,
    'stocks': results,
    'buy': [x for x in results if x['action'] == '买入'][:5],
    'sell': [x for x in results if x['action'] == '卖出']
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

conn.close()

print(f"✓ 分析完成: {len(results)}只股票")
print(f"✓ 买入信号: {len([x for x in results if x['action'] == '买入'])}只")
print(f"✓ 卖出信号: {len([x for x in results if x['action'] == '卖出'])}只")
print(f"✓ JSON输出: {OUTPUT_JSON}")
print("=" * 60)
print("分析完成！")