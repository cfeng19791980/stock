# -*- coding: utf-8 -*-
"""
买点卖点价格区间预测 v4.0
- 预测具体价格区间（而非时机）
- 买点区间：未来最低价 ± 3%
- 卖点区间：未来最高价 ± 3%
- 区间基于历史波动率动态调整
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import sqlite3
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

class PriceRangePredictor:
    """价格区间预测器"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        self.buy_low_model = None  # 预测未来最低价
        self.sell_high_model = None  # 预测未来最高价
        self.buy_mae = 0
        self.sell_mae = 0
        
    def get_stock_data(self, code, days=250):
        """获取股票数据"""
        sql = '''
            SELECT date, open, close, high, low, volume, pct_chg,
                   ma5, ma10, ma20, ma30, ma60,
                   rsi6, rsi12, rsi24,
                   macd, macd_signal, macd_hist,
                   k, d, j,
                   boll_upper, boll_mid, boll_lower
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
    
    def extract_features(self, df, i):
        """提取特征（优化版）"""
        if i < 20 or i >= len(df):
            return None
        
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        feat = {}
        
        # 价格变化（最重要）
        close = row['close']
        feat['pct_chg'] = row['pct_chg'] if pd.notna(row['pct_chg']) else 0
        
        # 近期涨跌
        feat['pct_chg_3d'] = (close - df.iloc[i-3]['close']) / df.iloc[i-3]['close'] * 100 if i >= 3 else 0
        feat['pct_chg_5d'] = (close - df.iloc[i-5]['close']) / df.iloc[i-5]['close'] * 100 if i >= 5 else 0
        
        # 均线距离
        ma5 = row['ma5'] if pd.notna(row['ma5']) else close
        ma10 = row['ma10'] if pd.notna(row['ma10']) else close
        ma20 = row['ma20'] if pd.notna(row['ma20']) else close
        
        feat['ma5_dist'] = (close - ma5) / ma5 * 100
        feat['ma10_dist'] = (close - ma10) / ma10 * 100
        feat['ma20_dist'] = (close - ma20) / ma20 * 100
        
        # RSI
        feat['rsi6'] = row['rsi6'] if pd.notna(row['rsi6']) else 50
        feat['rsi12'] = row['rsi12'] if pd.notna(row['rsi12']) else 50
        feat['rsi_oversold'] = 1 if feat['rsi6'] < 30 else 0
        feat['rsi_overbought'] = 1 if feat['rsi6'] > 70 else 0
        
        # MACD
        feat['macd_hist'] = row['macd_hist'] if pd.notna(row['macd_hist']) else 0
        feat['macd_hist_change'] = feat['macd_hist'] - (prev['macd_hist'] if pd.notna(prev['macd_hist']) else 0)
        
        # KDJ
        feat['k'] = row['k'] if pd.notna(row['k']) else 50
        feat['d'] = row['d'] if pd.notna(row['d']) else 50
        feat['j'] = row['j'] if pd.notna(row['j']) else 50
        feat['k_d_diff'] = feat['k'] - feat['d']
        
        # 波动率
        if i >= 20:
            closes = df.iloc[i-20:i+1]['close'].values
            returns = np.diff(closes) / closes[:-1]
            feat['volatility'] = np.std(returns) * 100
        else:
            feat['volatility'] = 2
        
        # 成交量比
        volume = row['volume'] if pd.notna(row['volume']) else 0
        vol_ma5 = df.iloc[i-5:i]['volume'].mean() if i >= 5 else volume
        feat['vol_ratio'] = volume / vol_ma5 if vol_ma5 > 0 else 1
        
        # 价格位置
        if i >= 30:
            high_30 = df.iloc[i-30:i+1]['high'].max()
            low_30 = df.iloc[i-30:i+1]['low'].min()
            feat['price_position'] = (close - low_30) / (high_30 - low_30) if high_30 > low_30 else 0.5
        else:
            feat['price_position'] = 0.5
        
        # 涨跌天数
        if i >= 10:
            pct_list = df.iloc[i-10:i]['pct_chg'].values
            valid = [p for p in pct_list if pd.notna(p)]
            feat['up_days'] = len([p for p in valid if p > 0])
            feat['down_days'] = len([p for p in valid if p < 0])
        else:
            feat['up_days'] = 0
            feat['down_days'] = 0
        
        return feat
    
    def train_models(self):
        """训练价格预测模型"""
        print("=" * 60)
        print("训练价格区间预测模型")
        print("=" * 60)
        
        features = []
        buy_targets = []  # 未来最低价
        sell_targets = []  # 未来最高价
        
        lookahead = 10  # 预测未来10天
        
        for code in self.stock_pool:
            df = self.get_stock_data(code, 250)
            if df is None or len(df) < 100:
                continue
            
            print(f"处理 {code}...")
            
            for i in range(30, len(df) - lookahead):
                feat = self.extract_features(df, i)
                if feat is None:
                    continue
                
                # 未来数据
                future = df.iloc[i+1:i+lookahead+1]
                future_low = future['low'].min()
                future_high = future['high'].max()
                current_close = df.iloc[i]['close']
                
                # 目标：价格变化百分比
                buy_targets.append((future_low - current_close) / current_close * 100)
                sell_targets.append((future_high - current_close) / current_close * 100)
                features.append(feat)
        
        print(f"\n样本数: {len(features)}")
        
        # 转换为DataFrame
        feat_df = pd.DataFrame(features).fillna(0)
        
        # 训练买点价格预测（未来最低价）
        print("\n[训练买点价格预测模型...]")
        X = feat_df
        y_buy = np.array(buy_targets)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y_buy, test_size=0.2, random_state=42)
        
        self.buy_low_model = XGBRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        self.buy_low_model.fit(X_train, y_train)
        
        y_pred = self.buy_low_model.predict(X_test)
        self.buy_mae = mean_absolute_error(y_test, y_pred)
        buy_r2 = r2_score(y_test, y_pred)
        
        print(f"买点价格预测 MAE: {self.buy_mae*100:.2f}%")
        print(f"买点价格预测 R²: {buy_r2:.3f}")
        
        # 训练卖点价格预测（未来最高价）
        print("\n[训练卖点价格预测模型...]")
        y_sell = np.array(sell_targets)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y_sell, test_size=0.2, random_state=42)
        
        self.sell_high_model = XGBRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        self.sell_high_model.fit(X_train, y_train)
        
        y_pred = self.sell_high_model.predict(X_test)
        self.sell_mae = mean_absolute_error(y_test, y_pred)
        sell_r2 = r2_score(y_test, y_pred)
        
        print(f"卖点价格预测 MAE: {self.sell_mae*100:.2f}%")
        print(f"卖点价格预测 R²: {sell_r2:.3f}")
        
        print("=" * 60)
        print(f"✓ 模型训练完成")
        print(f"  买点价格误差: ±{self.buy_mae*100:.2f}%")
        print(f"  卖点价格误差: ±{self.sell_mae*100:.2f}%")
        print("=" * 60)
    
    def predict_price_range(self, df, i, volatility=None):
        """预测价格区间"""
        try:
            feat = self.extract_features(df, i)
            if feat is None:
                print(f"    extract_features返回None (i={i}, len={len(df)})")
                return None
            
            current_close = df.iloc[i]['close']
            feat_df = pd.DataFrame([feat]).fillna(0)
            
            # 预测未来最低价比例
            buy_ratio = self.buy_low_model.predict(feat_df)[0]
            
            # 预测未来最高价比例
            sell_ratio = self.sell_high_model.predict(feat_df)[0]
            
            # 计算价格区间
            if volatility is None:
                volatility = feat['volatility_20']
            
            # 区间范围固定为±0.5%（总宽度不超过1%）
            buy_range_pct = 0.005  # 0.5%
            sell_range_pct = 0.005  # 0.5%
            
            # 买点价格区间
            buy_center = current_close * buy_ratio
            buy_low = buy_center * (1 - buy_range_pct)
            buy_high = buy_center * (1 + buy_range_pct)
            
            # 卖点价格区间
            sell_center = current_close * sell_ratio
            # 区间固定±0.5%
            buy_low = buy_center * 0.995
            buy_high = buy_center * 1.005
            sell_low = sell_center * 0.995
            sell_high = sell_center * 1.005
            
            return {
                'date': df.iloc[i]['date'],
                'current_price': current_close,
                'buy_range': {
                    'low': round(buy_low, 2),
                    'high': round(buy_high, 2),
                    'center': round(buy_center, 2),
                    'change_pct': round(buy_change_pct, 2)
                },
                'sell_range': {
                    'low': round(sell_low, 2),
                    'high': round(sell_high, 2),
                    'center': round(sell_center, 2),
                    'change_pct': round(sell_change_pct, 2)
                },
                'volatility': feat['volatility']
            }
        except Exception as e:
            print(f"    predict_price_range错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def predict_for_stock(self, code):
        """预测单只股票的价格区间"""
        df = self.get_stock_data(code, 60)
        
        if df is None:
            print(f"  {code}: get_stock_data返回None")
            return None
        
        if len(df) < 30:
            print(f"  {code}: 数据不足 {len(df)}条")
            return None
        
        # 使用最新数据预测
        try:
            result = self.predict_price_range(df, len(df) - 1)
            
            if result is None:
                print(f"  {code}: predict_price_range返回None")
                return None
            
            result['code'] = code
            return result
        except Exception as e:
            print(f"  {code}: 预测错误 {e}")
            return None
    
    def predict_all(self):
        """预测所有股票"""
        print("\n" + "=" * 60)
        print("价格区间预测结果")
        print("=" * 60)
        
        results = []
        
        for code in self.stock_pool:
            result = self.predict_for_stock(code)
            
            if result is None:
                print(f"{code}: 数据不足或预测失败")
                continue
            
            results.append(result)
            
            # 显示预测结果
            buy = result['buy_range']
            sell = result['sell_range']
            
            print(f"\n{code}:")
            print(f"  当前价格: ¥{result['current_price']:.2f}")
            print(f"  买点区间: ¥{buy['low']:.2f} - ¥{buy['high']:.2f} ({buy['change_pct']:+.2f}%)")
            print(f"  卖点区间: ¥{sell['low']:.2f} - ¥{sell['high']:.2f} ({sell['change_pct']:+.2f}%)")
        
        print(f"\n成功预测: {len(results)}只股票")
        return results
    
    def close(self):
        self.conn.close()


if __name__ == '__main__':
    predictor = PriceRangePredictor()
    predictor.train_models()
    results = predictor.predict_all()
    predictor.close()
    
    print("\n预测完成！")