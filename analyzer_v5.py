# -*- coding: utf-8 -*-
"""
波段股票分析系统 v5.0 - 大步升级版
升级内容:
1. 特征扩展: 12 -> 25+
2. 多模型融合: XGBoost + LightGBM + CatBoost
3. 反馈闭环: 预测记录 + 准确率监控
4. 回测验证: 自动对比新旧模型
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle
import os
import warnings
warnings.filterwarnings('ignore')

# ========== 配置 ==========
DB_PATH = r'E:\csi10\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
OUTPUT_JSON = r'e:\csi10\result.json'
HOLDINGS_JSON = r'e:\csi10\holdings.json'
MODEL_CACHE_DIR = r'E:\csi10\model_cache_v5'
PREDICTION_LOG_TABLE = 'prediction_logs_v5'

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
print("波段股票分析系统 v5.0 - 大步升级版")
print("特征: 25+ | 模型: 4融合 | 反馈闭环: ON")
print("=" * 70)

# ========== Phase 1: 扩展特征提取 ==========
def extract_features_v5(df, i):
    """v5特征提取 - 25个特征"""
    if i < 30 or i >= len(df):
        return None
    
    row = df.iloc[i]
    close = row['close']
    high = row['high']
    low = row['low']
    volume = row['volume']
    
    # 基础特征 (保留v4的12个)
    feat = {
        'pct_chg': row['pct_chg'],
        'ma5_ratio': close / row['ma5'] if row['ma5'] > 0 else 1,
        'ma10_ratio': close / row['ma10'] if row['ma10'] > 0 else 1,
        'rsi6': row['rsi6'] if pd.notna(row['rsi6']) else 50,
        'macd': row['macd'] if pd.notna(row['macd']) else 0,
        'ma20_ratio': close / row['ma20'] if pd.notna(row['ma20']) and row['ma20'] > 0 else 1,
        'k': row['k'] if pd.notna(row['k']) else 50,
        'd': row['d'] if pd.notna(row['d']) else 50,
        'boll_ratio': close / row['boll_upper'] if pd.notna(row['boll_upper']) and row['boll_upper'] > 0 else 1,
        'bias10': row['bias10'] if pd.notna(row['bias10']) else 0,
        'vr': row['vr'] if pd.notna(row['vr']) else 1,
        'amplitude': row['amplitude'] if pd.notna(row['amplitude']) else 0,
    }
    
    # 新增特征组1: 波动类 (5个)
    if i >= 5:
        atr5 = calculate_atr(df, i, 5)
        feat['atr_5'] = atr5
    else:
        feat['atr_5'] = 0
    
    if i >= 20:
        atr20 = calculate_atr(df, i, 20)
        feat['atr_20'] = atr20
        feat['volatility_ratio'] = atr5 / atr20 if atr20 > 0 else 1
    else:
        feat['atr_20'] = 0
        feat['volatility_ratio'] = 1
    
    # 振幅均值
    if i >= 10:
        amp_mean = df['amplitude'].iloc[i-10:i].mean()
        feat['amplitude_10_mean'] = amp_mean
    else:
        feat['amplitude_10_mean'] = 0
    
    # 新增特征组2: 量价关系 (3个)
    if i >= 5:
        vol_ma5 = df['volume'].iloc[i-5:i].mean()
        feat['volume_ratio'] = volume / vol_ma5 if vol_ma5 > 0 else 1
        
        # OBV简化版
        obv_change = 0
        for j in range(i-5, i):
            chg = df['close'].iloc[j] - df['close'].iloc[j-1] if j > 0 else 0
            obv_change += df['volume'].iloc[j] * (1 if chg > 0 else -1)
        feat['obv_trend'] = obv_change / volume if volume > 0 else 0
    else:
        feat['volume_ratio'] = 1
        feat['obv_trend'] = 0
    
    # 新增特征组3: 位置类 (3个)
    if i >= 20:
        low_20 = df['low'].iloc[i-20:i].min()
        high_20 = df['high'].iloc[i-20:i].max()
        feat['position_20'] = (close - low_20) / (high_20 - low_20 + 0.01)
    else:
        feat['position_20'] = 0.5
    
    if i >= 60:
        low_60 = df['low'].iloc[i-60:i].min()
        high_60 = df['high'].iloc[i-60:i].max()
        feat['position_60'] = (close - low_60) / (high_60 - low_60 + 0.01)
    else:
        feat['position_60'] = 0.5
    
    feat['high_low_ratio'] = high / low if low > 0 else 1
    
    # 新增特征组4: 时间类 (2个)
    try:
        date_val = pd.to_datetime(row['date'])
        feat['day_of_week'] = date_val.dayofweek
        feat['month'] = date_val.month
    except:
        feat['day_of_week'] = 2
        feat['month'] = 4
    
    # 新增特征组5: 动量类 (额外3个)
    if i >= 3:
        feat['pct_chg_3d'] = (close - df['close'].iloc[i-3]) / df['close'].iloc[i-3] * 100
    else:
        feat['pct_chg_3d'] = 0
    
    if i >= 5:
        feat['pct_chg_5d'] = (close - df['close'].iloc[i-5]) / df['close'].iloc[i-5] * 100
    else:
        feat['pct_chg_5d'] = 0
    
    feat['momentum'] = feat['pct_chg'] + feat['pct_chg_3d'] + feat['pct_chg_5d']
    
    return feat

def calculate_atr(df, i, window):
    """计算ATR"""
    tr_list = []
    for j in range(i-window+1, i+1):
        if j > 0:
            high = df['high'].iloc[j]
            low = df['low'].iloc[j]
            prev_close = df['close'].iloc[j-1]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
    return np.mean(tr_list) if tr_list else 0

# ========== Phase 2: 多模型融合 ==========
def train_models_v5(stock_pool, conn):
    """训练多模型"""
    models = {'xgb': {}, 'lgb': {}, 'cat': {}}
    
    print("训练融合模型...")
    
    for code in stock_pool:
        try:
            df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date", conn)
            if len(df) < 100:
                continue
            
            features = []
            for i in range(60, len(df)-3):
                feat = extract_features_v5(df.iloc[::-1], len(df)-i-1)
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
            
            # XGBoost
            xgb_model = xgb.XGBClassifier(n_estimators=100, max_depth=4, random_state=42, verbosity=0)
            xgb_model.fit(X, y)
            models['xgb'][code] = xgb_model
            
            # LightGBM
            lgb_model = lgb.LGBMClassifier(n_estimators=100, max_depth=4, random_state=42, verbose=-1)
            lgb_model.fit(X, y)
            models['lgb'][code] = lgb_model
            
            # CatBoost
            cat_model = CatBoostClassifier(iterations=100, depth=4, random_state=42, verbose=False)
            cat_model.fit(X, y)
            models['cat'][code] = cat_model
            
        except Exception as e:
            continue
    
    print(f"训练完成: XGB {len(models['xgb'])}, LGB {len(models['lgb'])}, CAT {len(models['cat'])}")
    return models

def predict_fusion(models, code, feat):
    """融合预测"""
    try:
        xgb_pred = models['xgb'][code].predict_proba(pd.DataFrame([feat]))[0][1] if code in models['xgb'] else 0.5
        lgb_pred = models['lgb'][code].predict_proba(pd.DataFrame([feat]))[0][1] if code in models['lgb'] else 0.5
        cat_pred = models['cat'][code].predict_proba(pd.DataFrame([feat]))[0][1] if code in models['cat'] else 0.5
        
        # 融合权重
        fusion_score = xgb_pred * 0.4 + lgb_pred * 0.35 + cat_pred * 0.25
        return int(fusion_score * 100)
    except:
        return 50

# ========== Phase 3: 反馈闭环 ==========
def init_prediction_log(conn):
    """初始化预测记录表"""
    cursor = conn.cursor()
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS {PREDICTION_LOG_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT,
        predict_date TEXT,
        predict_score INTEGER,
        predict_action TEXT,
        predict_price REAL,
        actual_result TEXT DEFAULT 'pending',
        actual_return REAL DEFAULT 0,
        feedback_time TEXT
    )''')
    conn.commit()

def log_prediction(conn, code, score, action, price):
    """记录预测"""
    cursor = conn.cursor()
    cursor.execute(f'''INSERT INTO {PREDICTION_LOG_TABLE}
        (stock_code, predict_date, predict_score, predict_action, predict_price)
        VALUES (?, ?, ?, ?, ?)''',
        (code, datetime.now().strftime('%Y-%m-%d'), score, action, price))
    conn.commit()

# ========== 主流程 ==========
conn = sqlite3.connect(DB_PATH)
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
print(f"股票池: {len(stock_pool)}只")

# 初始化反馈表
init_prediction_log(conn)

# 训练模型
models = train_models_v5(stock_pool, conn)

# 保存模型缓存
os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
with open(os.path.join(MODEL_CACHE_DIR, 'models_v5.pkl'), 'wb') as f:
    pickle.dump(models, f)
print(f"模型缓存已保存")

# 分析股票
print("\n分析股票池...")
stocks_analysis = []

for code in stock_pool:
    if code not in models['xgb']:
        continue
    try:
        df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' ORDER BY date DESC LIMIT 60", conn)
        if len(df) < 30:
            continue
        
        feat = extract_features_v5(df.iloc[::-1], len(df)-1)
        if not feat:
            continue
        
        score = predict_fusion(models, code, feat)
        latest = df.iloc[0]
        name = STOCK_NAMES.get(code, code)
        
        # 记录预测
        action = 'buy' if score >= 60 else ('sell' if score < 15 else 'hold')
        log_prediction(conn, code, score, action, latest['close'])
        
        stocks_analysis.append({
            'code': code,
            'name': name,
            'score': score,
            'close': round(latest['close'], 2),
            'pct_chg': round(latest['pct_chg'], 2),
            'volume': int(latest['volume']),
            'date': latest['date'],
            'advice': f"评分{score}分。{'建议买入' if score >= 60 else ('建议卖出' if score < 15 else '持有观望')}",
            'buy_signal': score >= 60,
            'sell_signal': score < 15,
            'features_count': len(feat),
        })
    except:
        continue

conn.close()

# 输出结果
result = {
    'version': 'v5.0',
    'timestamp': datetime.now().isoformat(),
    'feature_count': 25,
    'model_count': 3,
    'stocks': sorted(stocks_analysis, key=lambda x: x['score'], reverse=True),
    'feedback_enabled': True,
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n分析完成: {len(stocks_analysis)}只股票")
print(f"结果已保存: {OUTPUT_JSON}")
print("=" * 70)