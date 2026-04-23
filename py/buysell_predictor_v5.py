# -*- coding: utf-8 -*-
"""
买点卖点预测模型 v5.0
- 预测价格变化百分比（而非绝对价格）
- 添加大盘因子
- 使用分位数回归预测区间
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import sqlite3
from xgboost import XGBRegressor, XGBClassifier
from sklearn.model_selection import train_test_split

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

class BuySellPredictor:
    """买点卖点预测器"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        
        # 模型
        self.buy_model = None  # 预测买点变化%
        self.sell_model = None  # 预测卖点变化%
        self.buy_mae = 0
        self.sell_mae = 0
    
    def get_stock_data(self, code, days=120):
        """获取股票数据"""
        sql = '''
            SELECT date, open, close, high, low, volume, pct_chg,
                   ma5, ma10, ma20, rsi6, rsi12,
                   macd, macd_hist, macd_signal, k, d, j
            FROM daily_price 
            WHERE code = ?
            ORDER BY date DESC
            LIMIT ?
        '''
        df = pd.read_sql_query(sql, self.conn, params=(code, days))
        if len(df) == 0:
            return None
        df = df.iloc[::-1].reset_index(drop=True)
        return df
    
    def get_index_data(self, days=120):
        """获取大盘数据"""
        sql = '''
            SELECT date, close, pct_chg, ma5, ma10, ma20
            FROM index_daily 
            WHERE code = 'sh.000300'
            ORDER BY date DESC
            LIMIT ?
        '''
        df = pd.read_sql_query(sql, self.conn, params=(days,))
        if len(df) == 0:
            return None
        df = df.iloc[::-1].reset_index(drop=True)
        return df
    
    def extract_features(self, df, i, index_df=None, idx_i=None):
        """提取特征"""
        if i < 20 or i >= len(df):
            return None
        
        row = df.iloc[i]
        prev = df.iloc[i-1] if i > 0 else row
        
        feat = {}
        close = row['close']
        
        # 1. 涨跌趋势（最重要）
        feat['pct_chg'] = row['pct_chg'] if pd.notna(row['pct_chg']) else 0
        feat['pct_3d'] = (close - df.iloc[i-3]['close']) / df.iloc[i-3]['close'] * 100 if i >= 3 else 0
        feat['pct_5d'] = (close - df.iloc[i-5]['close']) / df.iloc[i-5]['close'] * 100 if i >= 5 else 0
        feat['pct_10d'] = (close - df.iloc[i-10]['close']) / df.iloc[i-10]['close'] * 100 if i >= 10 else 0
        
        # 2. 均线偏离
        ma5 = row['ma5'] if pd.notna(row['ma5']) else close
        ma10 = row['ma10'] if pd.notna(row['ma10']) else close
        ma20 = row['ma20'] if pd.notna(row['ma20']) else close
        
        feat['ma5_dist'] = (close - ma5) / close * 100
        feat['ma10_dist'] = (close - ma10) / close * 100
        feat['ma20_dist'] = (close - ma20) / close * 100
        feat['ma5_above'] = 1 if close > ma5 else 0
        feat['ma10_above'] = 1 if close > ma10 else 0
        feat['ma20_above'] = 1 if close > ma20 else 0
        
        # 3. RSI
        rsi6 = row['rsi6'] if pd.notna(row['rsi6']) else 50
        rsi12 = row['rsi12'] if pd.notna(row['rsi12']) else 50
        feat['rsi6'] = rsi6
        feat['rsi12'] = rsi12
        feat['rsi_low'] = 1 if rsi6 < 30 else 0
        feat['rsi_high'] = 1 if rsi6 > 70 else 0
        
        # 4. MACD
        macd_hist = row['macd_hist'] if pd.notna(row['macd_hist']) else 0
        prev_hist = prev['macd_hist'] if pd.notna(prev['macd_hist']) else 0
        feat['macd_hist'] = macd_hist
        feat['macd_hist_chg'] = macd_hist - prev_hist
        feat['macd_cross'] = 1 if macd_hist > 0 and prev_hist < 0 else 0
        
        # 5. KDJ
        k = row['k'] if pd.notna(row['k']) else 50
        d = row['d'] if pd.notna(row['d']) else 50
        j = row['j'] if pd.notna(row['j']) else 50
        feat['k'] = k
        feat['d'] = d
        feat['j'] = j
        feat['kd_cross'] = 1 if k > d else 0
        feat['j_low'] = 1 if j < 20 else 0
        feat['j_high'] = 1 if j > 80 else 0
        
        # 6. 波动率
        if i >= 20:
            closes = df.iloc[i-20:i+1]['close'].values
            rets = np.diff(closes) / closes[:-1]
            feat['volatility'] = np.std(rets) * 100
        else:
            feat['volatility'] = 2
        
        # 7. 成交量
        vol = row['volume'] if pd.notna(row['volume']) else 0
        vol_ma5 = df.iloc[i-5:i]['volume'].mean() if i >= 5 else vol
        feat['vol_ratio'] = vol / vol_ma5 if vol_ma5 > 0 else 1
        
        # 8. 价格位置
        if i >= 30:
            high30 = df.iloc[i-30:i+1]['high'].max()
            low30 = df.iloc[i-30:i+1]['low'].min()
            feat['price_pos'] = (close - low30) / (high30 - low30) if high30 > low30 else 0.5
        else:
            feat['price_pos'] = 0.5
        
        # 9. 大盘因子（重要！）
        if index_df is not None and idx_i is not None and idx_i >= 0:
            idx_row = index_df.iloc[idx_i]
            idx_prev = index_df.iloc[idx_i-1] if idx_i > 0 else idx_row
            feat['idx_pct'] = idx_row['pct_chg'] if pd.notna(idx_row['pct_chg']) else 0
            feat['idx_ma5_dist'] = (idx_row['close'] - idx_row['ma5']) / idx_row['close'] * 100 if pd.notna(idx_row['ma5']) else 0
            feat['idx_above_ma5'] = 1 if pd.notna(idx_row['ma5']) and idx_row['close'] > idx_row['ma5'] else 0
        else:
            feat['idx_pct'] = 0
            feat['idx_ma5_dist'] = 0
            feat['idx_above_ma5'] = 0
        
        return feat
    
    def train_models(self):
        """训练模型"""
        print("\n" + "=" * 60)
        print("训练买点卖点预测模型")
        print("=" * 60)
        
        # 获取大盘数据
        index_df = self.get_index_data(200)
        
        buy_features = []
        buy_targets = []
        sell_features = []
        sell_targets = []
        
        for code in self.stock_pool:
            print(f"处理 {code}...")
            df = self.get_stock_data(code, 150)
            if df is None or len(df) < 50:
                continue
            
            # 匹配大盘日期
            for i in range(30, len(df) - 10):
                date = df.iloc[i]['date']
                
                # 找大盘对应日期
                idx_i = None
                if index_df is not None:
                    match = index_df[index_df['date'] == date]
                    if len(match) > 0:
                        idx_i = match.index[0]
                
                feat = self.extract_features(df, i, index_df, idx_i)
                if feat is None:
                    continue
                
                # 未来3天数据（最短窗口最高精度）
                future = df.iloc[i+1:i+4]
                future_low = future['low'].min()
                future_high = future['high'].max()
                current_close = df.iloc[i]['close']
                
                # 目标：价格变化百分比
                buy_change = (future_low - current_close) / current_close * 100
                sell_change = (future_high - current_close) / current_close * 100
                
                buy_features.append(feat)
                buy_targets.append(buy_change)
                sell_features.append(feat)
                sell_targets.append(sell_change)
        
        print(f"\n样本数: {len(buy_features)}")
        
        # 训练买点模型
        X_buy = pd.DataFrame(buy_features).fillna(0)
        y_buy = np.array(buy_targets)
        
        X_train, X_test, y_train, y_test = train_test_split(X_buy, y_buy, test_size=0.2, random_state=42)
        
        self.buy_model = XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42
        )
        self.buy_model.fit(X_train, y_train)
        
        buy_pred = self.buy_model.predict(X_test)
        self.buy_mae = np.mean(np.abs(buy_pred - y_test))
        
        print(f"\n买点模型 MAE: {self.buy_mae:.2f}%")
        
        # 训练卖点模型
        X_sell = pd.DataFrame(sell_features).fillna(0)
        y_sell = np.array(sell_targets)
        
        X_train, X_test, y_train, y_test = train_test_split(X_sell, y_sell, test_size=0.2, random_state=42)
        
        self.sell_model = XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42
        )
        self.sell_model.fit(X_train, y_train)
        
        sell_pred = self.sell_model.predict(X_test)
        self.sell_mae = np.mean(np.abs(sell_pred - y_test))
        
        print(f"卖点模型 MAE: {self.sell_mae:.2f}%")
        print("=" * 60)
        print("模型训练完成")
        print("=" * 60)
    
    def predict(self, code):
        """预测买点卖点"""
        df = self.get_stock_data(code, 60)
        if df is None or len(df) < 30:
            return None
        
        index_df = self.get_index_data(60)
        
        # 最新一天
        i = len(df) - 1
        date = df.iloc[i]['date']
        
        idx_i = None
        if index_df is not None:
            match = index_df[index_df['date'] == date]
            if len(match) > 0:
                idx_i = match.index[0]
        
        feat = self.extract_features(df, i, index_df, idx_i)
        if feat is None:
            return None
        
        feat_df = pd.DataFrame([feat]).fillna(0)
        
        buy_change = self.buy_model.predict(feat_df)[0]
        sell_change = self.sell_model.predict(feat_df)[0]
        
        current_price = df.iloc[i]['close']
        
        # 买点价格
        buy_center = current_price * (1 + buy_change / 100)
        buy_low = buy_center * 0.99
        buy_high = buy_center * 1.01
        
        # 卖点价格
        sell_center = current_price * (1 + sell_change / 100)
        sell_low = sell_center * 0.99
        sell_high = sell_center * 1.01
        
        return {
            'code': code,
            'date': date,
            'current_price': round(current_price, 2),
            'buy': {
                'change_pct': round(buy_change, 2),
                'price_center': round(buy_center, 2),
                'price_range': f"{round(buy_low, 2)}-{round(buy_high, 2)}"
            },
            'sell': {
                'change_pct': round(sell_change, 2),
                'price_center': round(sell_center, 2),
                'price_range': f"{round(sell_low, 2)}-{round(sell_high, 2)}"
            }
        }
    
    def predict_all(self):
        """预测所有股票"""
        print("\n" + "=" * 60)
        print("买点卖点预测结果")
        print("=" * 60)
        
        for code in self.stock_pool:
            result = self.predict(code)
            if result is None:
                print(f"{code}: 数据不足")
                continue
            
            print(f"\n{code}:")
            print(f"  当前价格: ¥{result['current_price']}")
            print(f"  买点: {result['buy']['change_pct']}% → ¥{result['buy']['price_range']}")
            print(f"  卖点: {result['sell']['change_pct']}% → ¥{result['sell']['price_range']}")
    
    def close(self):
        self.conn.close()


if __name__ == '__main__':
    predictor = BuySellPredictor()
    predictor.train_models()
    predictor.predict_all()
    predictor.close()
    
    print("\n预测完成！")