# -*- coding: utf-8 -*-
"""
买点卖点预测优化 v3.0 - 机器学习版
- XGBoost分类器预测买卖信号
- 趋势过滤
- 止盈止损逻辑
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import sqlite3
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

class BuySellMLPredictor:
    """ML买卖信号预测器"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        self.buy_model = None
        self.sell_model = None
        self.buy_accuracy = 0
        self.sell_accuracy = 0
        
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
        """提取特征"""
        if i < 20 or i >= len(df) - 10:
            return None
        
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        feat = {}
        
        # 价格特征
        close = row['close']
        high = row['high']
        low = row['low']
        open_p = row['open']
        
        feat['close'] = close
        feat['pct_chg'] = row['pct_chg'] if pd.notna(row['pct_chg']) else 0
        feat['intraday_range'] = (high - low) / low * 100 if low > 0 else 0
        feat['gap'] = (open_p - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
        
        # 均线特征
        ma5 = row['ma5'] if pd.notna(row['ma5']) else close
        ma10 = row['ma10'] if pd.notna(row['ma10']) else close
        ma20 = row['ma20'] if pd.notna(row['ma20']) else close
        ma30 = row['ma30'] if pd.notna(row['ma30']) else close
        
        feat['ma5_ratio'] = close / ma5 if ma5 > 0 else 1
        feat['ma10_ratio'] = close / ma10 if ma10 > 0 else 1
        feat['ma20_ratio'] = close / ma20 if ma20 > 0 else 1
        feat['ma5_slope'] = (ma5 - df.iloc[i-5]['ma5']) / df.iloc[i-5]['ma5'] * 100 if pd.notna(df.iloc[i-5]['ma5']) else 0
        feat['ma10_slope'] = (ma10 - df.iloc[i-10]['ma10']) / df.iloc[i-10]['ma10'] * 100 if pd.notna(df.iloc[i-10]['ma10']) else 0
        
        # 均线距离
        feat['ma5_ma10_dist'] = (ma5 - ma10) / ma10 * 100 if ma10 > 0 else 0
        feat['ma10_ma20_dist'] = (ma10 - ma20) / ma20 * 100 if ma20 > 0 else 0
        
        # 均线排列
        feat['ma_alignment_up'] = 1 if close > ma5 and ma5 > ma10 and ma10 > ma20 else 0
        feat['ma_alignment_down'] = 1 if close < ma5 and ma5 < ma10 and ma10 < ma20 else 0
        
        # RSI特征
        feat['rsi6'] = row['rsi6'] if pd.notna(row['rsi6']) else 50
        feat['rsi12'] = row['rsi12'] if pd.notna(row['rsi12']) else 50
        feat['rsi24'] = row['rsi24'] if pd.notna(row['rsi24']) else 50
        feat['rsi6_rsi12_diff'] = feat['rsi6'] - feat['rsi12']
        feat['rsi_oversold'] = 1 if feat['rsi6'] < 30 else 0
        feat['rsi_overbought'] = 1 if feat['rsi6'] > 70 else 0
        
        # RSI趋势
        feat['rsi6_slope'] = feat['rsi6'] - (prev['rsi6'] if pd.notna(prev['rsi6']) else feat['rsi6'])
        
        # MACD特征
        feat['macd'] = row['macd'] if pd.notna(row['macd']) else 0
        feat['macd_hist'] = row['macd_hist'] if pd.notna(row['macd_hist']) else 0
        feat['macd_signal'] = row['macd_signal'] if pd.notna(row['macd_signal']) else 0
        
        feat['macd_cross_up'] = 1 if feat['macd_hist'] > 0 and (prev['macd_hist'] if pd.notna(prev['macd_hist']) else 0) <= 0 else 0
        feat['macd_cross_down'] = 1 if feat['macd_hist'] < 0 and (prev['macd_hist'] if pd.notna(prev['macd_hist']) else 0) >= 0 else 0
        
        feat['macd_hist_slope'] = feat['macd_hist'] - (prev['macd_hist'] if pd.notna(prev['macd_hist']) else feat['macd_hist'])
        
        # KDJ特征
        feat['k'] = row['k'] if pd.notna(row['k']) else 50
        feat['d'] = row['d'] if pd.notna(row['d']) else 50
        feat['j'] = row['j'] if pd.notna(row['j']) else 50
        
        feat['kdj_cross_up'] = 1 if feat['k'] > feat['d'] and (prev['k'] if pd.notna(prev['k']) else feat['k']) <= (prev['d'] if pd.notna(prev['d']) else feat['d']) else 0
        feat['kdj_cross_down'] = 1 if feat['k'] < feat['d'] and (prev['k'] if pd.notna(prev['k']) else feat['k']) >= (prev['d'] if pd.notna(prev['d']) else feat['d']) else 0
        
        feat['j_extreme_low'] = 1 if feat['j'] < 10 else 0
        feat['j_extreme_high'] = 1 if feat['j'] > 100 else 0
        
        # 布林带特征
        boll_upper = row['boll_upper'] if pd.notna(row['boll_upper']) else close * 1.05
        boll_lower = row['boll_lower'] if pd.notna(row['boll_lower']) else close * 0.95
        boll_mid = row['boll_mid'] if pd.notna(row['boll_mid']) else close
        
        feat['boll_position'] = (close - boll_lower) / (boll_upper - boll_lower) if boll_upper > boll_lower else 0.5
        feat['boll_width'] = (boll_upper - boll_lower) / boll_mid * 100 if boll_mid > 0 else 0
        feat['boll_break_upper'] = 1 if close > boll_upper else 0
        feat['boll_break_lower'] = 1 if close < boll_lower else 0
        
        # 成交量特征
        volume = row['volume'] if pd.notna(row['volume']) else 0
        vol_ma5 = df.iloc[i-5:i]['volume'].mean() if i >= 5 else volume
        vol_ma10 = df.iloc[i-10:i]['volume'].mean() if i >= 10 else volume
        
        feat['vol_ratio'] = volume / vol_ma5 if vol_ma5 > 0 else 1
        feat['vol_ratio_10'] = volume / vol_ma10 if vol_ma10 > 0 else 1
        
        # 量价配合
        feat['vol_price_up'] = 1 if feat['pct_chg'] > 0 and feat['vol_ratio'] > 1.5 else 0
        feat['vol_price_down'] = 1 if feat['pct_chg'] < 0 and feat['vol_ratio'] > 1.5 else 0
        
        # 波动率
        if i >= 20:
            closes20 = df.iloc[i-20:i+1]['close'].values
            returns20 = np.diff(closes20) / closes20[:-1]
            feat['volatility_20'] = np.std(returns20) * 100
        else:
            feat['volatility_20'] = 2
        
        # 价格位置（相对于60日高低）
        if i >= 60:
            high_60 = df.iloc[i-60:i+1]['high'].max()
            low_60 = df.iloc[i-60:i+1]['low'].min()
            feat['price_position_60'] = (close - low_60) / (high_60 - low_60) if high_60 > low_60 else 0.5
        else:
            feat['price_position_60'] = 0.5
        
        # 涨跌统计
        if i >= 10:
            pct_list = df.iloc[i-10:i]['pct_chg'].values
            feat['up_days_10'] = len([p for p in pct_list if p > 0])
            feat['down_days_10'] = len([p for p in pct_list if p < 0])
            feat['avg_pct_10'] = np.mean(pct_list)
            feat['max_up_10'] = max(pct_list)
            feat['max_down_10'] = min(pct_list)
        else:
            feat['up_days_10'] = 0
            feat['down_days_10'] = 0
            feat['avg_pct_10'] = 0
            feat['max_up_10'] = 0
            feat['max_down_10'] = 0
        
        # 连续涨跌天数
        consecutive_up = 0
        consecutive_down = 0
        for j in range(i-1, max(0, i-10), -1):
            pct = df.iloc[j]['pct_chg']
            if pd.notna(pct):
                if pct > 0:
                    consecutive_up += 1
                    if consecutive_down > 0:
                        break
                else:
                    consecutive_down += 1
                    if consecutive_up > 0:
                        break
        
        feat['consecutive_up'] = consecutive_up
        feat['consecutive_down'] = consecutive_down
        
        return feat
    
    def create_labels(self, df, i, lookahead=10):
        """创建标签 - 改进版"""
        if i >= len(df) - lookahead:
            return None
        
        # 未来lookahead天的数据
        future = df.iloc[i+1:i+lookahead+1]
        
        # 未来最低点和最高点
        future_low = future['low'].min()
        future_high = future['high'].max()
        current_close = df.iloc[i]['close']
        
        # 计算未来涨跌幅度
        rise_potential = (future_high - current_close) / current_close * 100
        fall_potential = (future_low - current_close) / current_close * 100
        
        # 买点标签：当前价格接近未来最低点（偏离<3%）
        buy_label = 1 if abs(fall_potential) < 3 else 0
        
        # 卖点标签：当前价格接近未来最高点（偏离<3%）
        sell_label = 1 if rise_potential < 3 else 0
        
        return {'buy': buy_label, 'sell': sell_label}
    
    def train_models(self):
        """训练买点和卖点模型"""
        print("=" * 60)
        print("训练买点卖点预测模型")
        print("=" * 60)
        
        # 收集训练数据
        buy_features = []
        buy_labels = []
        sell_features = []
        sell_labels = []
        
        for code in self.stock_pool:
            df = self.get_stock_data(code, 250)
            if df is None or len(df) < 100:
                continue
            
            print(f"处理 {code}...")
            
            for i in range(30, len(df) - 15):
                feat = self.extract_features(df, i)
                if feat is None:
                    continue
                
                label = self.create_labels(df, i, lookahead=10)
                if label is None:
                    continue
                
                buy_features.append(feat)
                buy_labels.append(label['buy'])
                
                # 卖点特征：反转部分指标
                sell_feat = feat.copy()
                sell_feat['rsi_oversold'] = feat['rsi_overbought']
                sell_feat['rsi_overbought'] = feat['rsi_oversold']
                sell_feat['macd_cross_up'] = feat['macd_cross_down']
                sell_feat['macd_cross_down'] = feat['macd_cross_up']
                sell_feat['kdj_cross_up'] = feat['kdj_cross_down']
                sell_feat['kdj_cross_down'] = feat['kdj_cross_up']
                
                sell_features.append(sell_feat)
                sell_labels.append(label['sell'])
        
        print(f"\n样本数: 买点 {len(buy_labels)}, 卖点 {len(sell_labels)}")
        
        # 转换为DataFrame
        buy_df = pd.DataFrame(buy_features)
        sell_df = pd.DataFrame(sell_features)
        
        # 训练买点模型
        print("\n[训练买点模型...]")
        X_buy = buy_df.fillna(0)
        y_buy = np.array(buy_labels)
        
        X_train, X_test, y_train, y_test = train_test_split(X_buy, y_buy, test_size=0.2, random_state=42)
        
        self.buy_model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )
        
        self.buy_model.fit(X_train, y_train)
        
        y_pred = self.buy_model.predict(X_test)
        self.buy_accuracy = accuracy_score(y_test, y_pred)
        
        print(f"买点模型准确率: {self.buy_accuracy*100:.2f}%")
        print(classification_report(y_test, y_pred, target_names=['非买点', '买点']))
        
        # 训练卖点模型
        print("\n[训练卖点模型...]")
        X_sell = sell_df.fillna(0)
        y_sell = np.array(sell_labels)
        
        # 计算样本权重（处理不平衡）
        sell_pos_count = np.sum(y_sell)
        sell_neg_count = len(y_sell) - sell_pos_count
        print(f"  卖点样本: {sell_pos_count}, 非卖点样本: {sell_neg_count}")
        
        X_train, X_test, y_train, y_test = train_test_split(X_sell, y_sell, test_size=0.2, random_state=42)
        
        # 使用scale_pos_weight处理样本不平衡
        scale_pos_weight = sell_neg_count / sell_pos_count if sell_pos_count > 0 else 1
        
        self.sell_model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss',
            scale_pos_weight=scale_pos_weight  # 处理不平衡
        )
        
        self.sell_model.fit(X_train, y_train)
        
        y_pred = self.sell_model.predict(X_test)
        self.sell_accuracy = accuracy_score(y_test, y_pred)
        
        print(f"卖点模型准确率: {self.sell_accuracy*100:.2f}%")
        print(classification_report(y_test, y_pred, target_names=['非卖点', '卖点']))
        
        print("=" * 60)
        print(f"✓ 模型训练完成")
        print(f"  买点准确率: {self.buy_accuracy*100:.2f}%")
        print(f"  卖点准确率: {self.sell_accuracy*100:.2f}%")
        print("=" * 60)
    
    def predict_signal(self, df, i):
        """预测买卖信号"""
        feat = self.extract_features(df, i)
        if feat is None:
            return None
        
        feat_df = pd.DataFrame([feat]).fillna(0)
        
        # 买点预测
        buy_prob = self.buy_model.predict_proba(feat_df)[0][1] if self.buy_model else 0
        
        # 卖点预测
        sell_feat = feat.copy()
        sell_feat['rsi_oversold'] = feat['rsi_overbought']
        sell_feat['rsi_overbought'] = feat['rsi_oversold']
        sell_feat['macd_cross_up'] = feat['macd_cross_down']
        sell_feat['macd_cross_down'] = feat['macd_cross_up']
        
        sell_df = pd.DataFrame([sell_feat]).fillna(0)
        sell_prob = self.sell_model.predict_proba(sell_df)[0][1] if self.sell_model else 0
        
        # 综合判断
        if buy_prob > 0.6 and buy_prob > sell_prob:
            return {
                'signal': 'buy',
                'probability': buy_prob,
                'price': df.iloc[i]['close'],
                'date': df.iloc[i]['date']
            }
        elif sell_prob > 0.6 and sell_prob > buy_prob:
            return {
                'signal': 'sell',
                'probability': sell_prob,
                'price': df.iloc[i]['close'],
                'date': df.iloc[i]['date']
            }
        
        return None
    
    def close(self):
        self.conn.close()


if __name__ == '__main__':
    predictor = BuySellMLPredictor()
    predictor.train_models()
    predictor.close()
    
    print("\n训练完成！")