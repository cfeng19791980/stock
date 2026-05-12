# -*- coding: utf-8 -*-
"""
买点卖点预测回测 v5.0
验证预测准确率
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import sqlite3

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

import buysell_predictor_v5

class Backtest:
    """回测器"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        self.predictor = buysell_predictor_v5.BuySellPredictor()
        self.predictor.train_models()
    
    def get_stock_data(self, code, days=150):
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
    
    def get_index_data(self, days=150):
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
    
    def backtest_stock(self, code):
        """回测单只股票"""
        df = self.get_stock_data(code, 150)
        if df is None or len(df) < 50:
            return None
        
        index_df = self.get_index_data(150)
        
        results = []
        lookahead = 3  # 最短窗口
        
        for i in range(30, len(df) - lookahead):
            date = df.iloc[i]['date']
            
            # 匹配大盘
            idx_i = None
            if index_df is not None:
                match = index_df[index_df['date'] == date]
                if len(match) > 0:
                    idx_i = match.index[0]
            
            feat = self.predictor.extract_features(df, i, index_df, idx_i)
            if feat is None:
                continue
            
            feat_df = pd.DataFrame([feat]).fillna(0)
            
            # 预测
            buy_pred = self.predictor.buy_model.predict(feat_df)[0]
            sell_pred = self.predictor.sell_model.predict(feat_df)[0]
            
            # 实际
            future = df.iloc[i+1:i+lookahead+1]
            actual_low = future['low'].min()
            actual_high = future['high'].max()
            current_close = df.iloc[i]['close']
            
            actual_buy_change = (actual_low - current_close) / current_close * 100
            actual_sell_change = (actual_high - current_close) / current_close * 100
            
            # 偏离度
            buy_deviation = abs(buy_pred - actual_buy_change)
            sell_deviation = abs(sell_pred - actual_sell_change)
            
            # 是否在MAE范围内
            buy_ok = buy_deviation <= self.predictor.buy_mae
            sell_ok = sell_deviation <= self.predictor.sell_mae
            
            results.append({
                'date': date,
                'buy_pred': buy_pred,
                'buy_actual': actual_buy_change,
                'buy_deviation': buy_deviation,
                'buy_ok': buy_ok,
                'sell_pred': sell_pred,
                'sell_actual': actual_sell_change,
                'sell_deviation': sell_deviation,
                'sell_ok': sell_ok
            })
        
        return results
    
    def backtest_all(self):
        """回测所有股票"""
        print("\n" + "=" * 60)
        print("买点卖点预测回测")
        print("=" * 60)
        
        all_results = []
        
        for code in self.stock_pool[:10]:
            print(f"\n回测 {code}...")
            results = self.backtest_stock(code)
            if results:
                all_results.extend(results)
        
        total = len(all_results)
        
        # 统计
        buy_ok_count = sum([r['buy_ok'] for r in all_results])
        sell_ok_count = sum([r['sell_ok'] for r in all_results])
        
        buy_avg_dev = np.mean([r['buy_deviation'] for r in all_results])
        sell_avg_dev = np.mean([r['sell_deviation'] for r in all_results])
        
        print("\n" + "=" * 60)
        print(f"回测样本数: {total}")
        print("=" * 60)
        
        print(f"\n买点预测:")
        print(f"  MAE范围内: {buy_ok_count}/{total} ({buy_ok_count/total*100:.1f}%)")
        print(f"  平均偏离: {buy_avg_dev:.2f}%")
        print(f"  偏离分布:")
        for threshold in [1, 2, 3, 5, 10]:
            count = len([r for r in all_results if r['buy_deviation'] <= threshold])
            print(f"    ≤{threshold}%: {count}次 ({count/total*100:.1f}%)")
        
        print(f"\n卖点预测:")
        print(f"  MAE范围内: {sell_ok_count}/{total} ({sell_ok_count/total*100:.1f}%)")
        print(f"  平均偏离: {sell_avg_dev:.2f}%")
        print(f"  偏离分布:")
        for threshold in [2, 5, 8, 10, 15]:
            count = len([r for r in all_results if r['sell_deviation'] <= threshold])
            print(f"    ≤{threshold}%: {count}次 ({count/total*100:.1f}%)")
        
        # 示例
        print("\n" + "=" * 60)
        print("预测示例（最近5个）:")
        print("=" * 60)
        for r in all_results[-5:]:
            print(f"\n{r['date']}:")
            print(f"  买点预测: {r['buy_pred']:.2f}% 实际: {r['buy_actual']:.2f}% 偏离: {r['buy_deviation']:.2f}% {'✓' if r['buy_ok'] else '✗'}")
            print(f"  卖点预测: {r['sell_pred']:.2f}% 实际: {r['sell_actual']:.2f}% 偏离: {r['sell_deviation']:.2f}% {'✓' if r['sell_ok'] else '✗'}")
        
        return all_results
    
    def close(self):
        self.conn.close()
        self.predictor.close()


if __name__ == '__main__':
    backtest = Backtest()
    results = backtest.backtest_all()
    backtest.close()
    
    print("\n回测完成！")