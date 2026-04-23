# -*- coding: utf-8 -*-
"""
csi10 双版本架构 - v4生产 + v5预备（轻量自学习）
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
import pickle
import json
import os
from datetime import datetime, timedelta

# 配置
DB_PATH = r'E:\csi10\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
V4_MODEL = r'E:\csi10\model_cache\models.pkl'
V5_MODEL = r'E:\csi10\model_cache_v5_no_leak\models_no_leak.pkl'
FEEDBACK_DB = r'E:\csi10\feedback_learning.db'

print("=" * 60)
print("csi10 双版本架构")
print("v4 = 生产版本 | v5 = 预备版本（自学习）")
print("=" * 60)

class LightweightSelfLearning:
    """轻量级自学习系统"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.feedback_conn = sqlite3.connect(FEEDBACK_DB)
        self._init_feedback_db()
        
        # 加载v4/v5模型
        self.v4_models = self._load_models(V4_MODEL)
        self.v5_models = self._load_models(V5_MODEL)
        
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        print(f"股票池: {len(self.stock_pool)}只")
    
    def _init_feedback_db(self):
        """初始化反馈数据库"""
        self.feedback_conn.execute('''CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY,
            date TEXT, code TEXT, version TEXT,
            score INTEGER, action TEXT, price REAL,
            actual_return REAL, is_correct INTEGER,
            feedback_time TEXT
        )''')
        self.feedback_conn.execute('''CREATE TABLE IF NOT EXISTS training_log (
            id INTEGER PRIMARY KEY,
            date TEXT, version TEXT, samples INTEGER,
            win_rate REAL, duration_seconds REAL
        )''')
        self.feedback_conn.commit()
    
    def _load_models(self, path):
        """加载模型"""
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return pickle.load(f)
        return None
    
    def record_prediction(self, code, version, score, action, price):
        """记录预测（轻量）"""
        self.feedback_conn.execute('''INSERT INTO predictions
            (date, code, version, score, action, price)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (datetime.now().strftime('%Y-%m-%d'), code, version, score, action, price))
        self.feedback_conn.commit()
    
    def update_feedback(self):
        """更新反馈（每日轻量任务）"""
        # 查询3天前的预测
        three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        pending = pd.read_sql(f"SELECT * FROM predictions WHERE date <= '{three_days_ago}' AND actual_return IS NULL", self.feedback_conn)
        
        if len(pending) == 0:
            print("  无待更新预测")
            return
        
        print(f"  更新 {len(pending)} 条预测反馈...")
        
        for row in pending.itertuples():
            try:
                # 获取实际结果
                actual_df = pd.read_sql(f"SELECT close FROM daily_price WHERE code='{row.code}' AND date >= '{row.date}' ORDER BY date LIMIT 4", self.conn)
                
                if len(actual_df) >= 4:
                    actual_price = actual_df.iloc[3]['close']
                    ret = (actual_price - row.price) / row.price * 100
                    is_correct = 1 if ret >= 3 else 0
                    
                    self.feedback_conn.execute('''UPDATE predictions
                        SET actual_return=?, is_correct=?, feedback_time=?
                        WHERE id=?''',
                        (ret, is_correct, datetime.now().isoformat(), row.id))
            except: continue
        
        self.feedback_conn.commit()
    
    def calculate_win_rate(self, version='v5', days=30):
        """计算胜率（轻量）"""
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        result = pd.read_sql(f'''SELECT
            COUNT(*) as total,
            SUM(is_correct) as correct
            FROM predictions
            WHERE version=? AND date >= ? AND is_correct IS NOT NULL''',
            self.feedback_conn, params=(version, start))
        
        if result.iloc[0]['total'] > 0:
            return result.iloc[0]['correct'] / result.iloc[0]['total'] * 100
        return 0
    
    def check_training_trigger(self):
        """检查是否需要触发训练（智能触发）"""
        # 触发条件
        triggers = []
        
        # 1. 胜率下降
        v5_win_rate = self.calculate_win_rate('v5', 30)
        if v5_win_rate < 50:
            triggers.append(f"v5胜率低: {v5_win_rate:.1f}%")
        
        # 2. 新数据积累
        new_samples = pd.read_sql(f"SELECT COUNT(*) FROM predictions WHERE date >= '{(datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d')}'", self.feedback_conn).iloc[0][0]
        if new_samples >= 50:
            triggers.append(f"新样本积累: {new_samples}")
        
        # 3. 周末触发
        if datetime.now().weekday() == 6:  # 周日
            triggers.append("周日定期训练")
        
        return triggers
    
    def incremental_train(self, days_to_add=30):
        """增量训练（轻量）"""
        print(f"\n增量训练: 最近{days_to_add}天数据...")
        
        train_start = (datetime.now() - timedelta(days=days_to_add)).strftime('%Y-%m-%d')
        train_end = datetime.now().strftime('%Y-%m-%d')
        
        new_samples = 0
        start_time = datetime.now()
        
        # 只更新部分模型（轻量）
        for code in self.stock_pool[:10]:  # 只更新10只
            try:
                df = pd.read_sql(f"SELECT * FROM daily_price WHERE code='{code}' AND date BETWEEN '{train_start}' AND '{train_end}' AND ma5 IS NOT NULL ORDER BY date", self.conn)
                
                if len(df) < 20:
                    continue
                
                features = []
                for i in range(20, len(df)-3):
                    feat = self._get_features(df.iloc[i])
                    close = df.iloc[i]['close']
                    close_3d = df.iloc[i+3]['close']
                    rise = (close_3d - close) / close
                    feat['target'] = 1 if rise >= 0.03 else 0
                    features.append(feat)
                
                if len(features) < 5:
                    continue
                
                ds = pd.DataFrame(features)
                X = ds.drop('target', axis=1).astype(float)
                y = ds['target']
                
                # 轻量训练（少迭代）
                model = xgb.XGBClassifier(n_estimators=20, max_depth=3, verbosity=0)
                model.fit(X, y)
                
                new_samples += len(features)
                
            except: continue
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # 记录训练日志
        self.feedback_conn.execute('''INSERT INTO training_log
            (date, version, samples, win_rate, duration_seconds)
            VALUES (?, ?, ?, ?, ?)''',
            (datetime.now().strftime('%Y-%m-%d'), 'v5_incremental', new_samples, 0, duration))
        self.feedback_conn.commit()
        
        print(f"  完成: {new_samples} 样本, {duration:.1f}秒")
        return new_samples
    
    def _get_features(self, row):
        """特征提取"""
        c = row['close']
        return {
            'pct_chg': float(row['pct_chg']),
            'ma5_ratio': float(c/max(row['ma5'] or c, 0.01)),
            'ma10_ratio': float(c/max(row['ma10'] or c, 0.01)),
            'rsi6': float(row['rsi6'] or 50), 'macd': float(row['macd'] or 0),
            'ma20_ratio': float(c/max(row['ma20'] or c, 0.01)),
            'k': float(row['k'] or 50), 'd': float(row['d'] or 50),
            'boll_ratio': float(c/max(row['boll_upper'] or c, 0.01)),
            'bias10': float(row['bias10'] or 0), 'vr': float(row['vr'] or 1),
            'amplitude': float(row['amplitude'] or 0),
            'atr_5': 0.0, 'atr_20': 0.0, 'volatility_ratio': 1.0,
            'amplitude_10_mean': 0.0, 'volume_ratio': 1.0, 'obv_trend': 0.0,
            'position_20': 0.5, 'position_60': 0.5, 'high_low_ratio': 1.0,
            'day_of_week': 2.0, 'month': 4.0, 'pct_chg_3d': 0.0, 'pct_chg_5d': 0.0,
            'momentum': float(row['pct_chg']),
        }
    
    def generate_report(self):
        """生成报告"""
        v4_rate = self.calculate_win_rate('v4', 30)
        v5_rate = self.calculate_win_rate('v5', 30)
        
        triggers = self.check_training_trigger()
        
        print("\n" + "=" * 60)
        print("双版本系统报告")
        print("=" * 60)
        print(f"v4胜率: {v4_rate:.1f}%")
        print(f"v5胜率: {v5_rate:.1f}%")
        
        if triggers:
            print(f"\n训练触发条件:")
            for t in triggers:
                print(f"  - {t}")
        else:
            print("\n暂无训练触发")
        
        # 保存报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'v4_win_rate': round(v4_rate, 2),
            'v5_win_rate': round(v5_rate, 2),
            'triggers': triggers,
        }
        
        with open(r'E:\csi10\dual_version_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("=" * 60)

# 主流程
if __name__ == '__main__':
    system = LightweightSelfLearning()
    
    # 1. 更新反馈
    print("\n[1] 更新反馈...")
    system.update_feedback()
    
    # 2. 检查训练触发
    print("\n[2] 检查训练触发...")
    triggers = system.check_training_trigger()
    
    # 3. 如果触发，执行增量训练
    if triggers:
        print("\n[3] 执行增量训练...")
        system.incremental_train(30)
    
    # 4. 生成报告
    system.generate_report()
    
    system.conn.close()
    system.feedback_conn.close()

print("\n双版本系统就绪！")