# -*- coding: utf-8 -*-
"""
买点卖点预测准确率回测
- 计算预测买点/卖点与实际最低/最高点的偏离度
- 偏离度 < 3% = 高准确
- 偏离度 < 5% = 中准确
- 偏离度 < 10% = 低准确
- 偏离度 >= 10% = 失败
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import sqlite3
import numpy as np
from datetime import datetime, timedelta

# 导入ML预测器
import buysell_ml_predictor

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

class BuySellBacktest:
    """买点卖点回测器"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        self.ml_predictor = buysell_ml_predictor.BuySellMLPredictor()
        self.ml_predictor.train_models()
        
    def get_stock_data(self, code, days=120):
        """获取股票历史数据"""
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
    
    def find_actual_extremes(self, df, window=20):
        """找到实际波段高低点"""
        extremes = []
        
        for i in range(window, len(df) - window):
            # 检查是否是局部最低点（买点）
            left_low = df.iloc[i-window:i]['low'].min()
            right_low = df.iloc[i+1:i+window+1]['low'].min()
            current_low = df.iloc[i]['low']
            
            if current_low <= left_low and current_low <= right_low:
                extremes.append({
                    'date': df.iloc[i]['date'],
                    'type': 'buy',
                    'actual_price': current_low,
                    'index': i
                })
            
            # 检查是否是局部最高点（卖点）
            left_high = df.iloc[i-window:i]['high'].max()
            right_high = df.iloc[i+1:i+window+1]['high'].max()
            current_high = df.iloc[i]['high']
            
            if current_high >= left_high and current_high >= right_high:
                extremes.append({
                    'date': df.iloc[i]['date'],
                    'type': 'sell',
                    'actual_price': current_high,
                    'index': i
                })
        
        return extremes
    
    def predict_signal(self, df, index):
        """预测某天的买卖信号 - 使用ML预测器"""
        result = self.ml_predictor.predict_signal(df, index)
        if result:
            return result['signal']
        return 'hold'
    
    def calculate_deviation(self, actual_price, predicted_date, df, signal_type, window=10):
        """计算偏离度"""
        # 找预测日期附近的实际极值
        pred_index = df[df['date'] == predicted_date].index
        if len(pred_index) == 0:
            return None
        
        pred_index = pred_index[0]
        
        # 在预测日期前后window天内找实际极值
        start_idx = max(0, pred_index - window)
        end_idx = min(len(df), pred_index + window + 1)
        
        window_data = df.iloc[start_idx:end_idx]
        
        if signal_type == 'buy':
            actual_extreme = window_data['low'].min()
        else:
            actual_extreme = window_data['high'].max()
        
        # 偏离度 = |预测价格 - 实际极值| / 实际极值 * 100
        # 这里预测价格用预测日期的价格
        predicted_price = df.iloc[pred_index]['close']
        deviation = abs(predicted_price - actual_extreme) / actual_extreme * 100
        
        return deviation
    
    def backtest_stock(self, code):
        """回测单只股票"""
        df = self.get_stock_data(code, 120)
        if df is None or len(df) < 60:
            return None
        
        # 找实际波段点
        extremes = self.find_actual_extremes(df, window=10)
        
        results = {
            'code': code,
            'buy_predictions': [],
            'sell_predictions': [],
            'buy_accuracy': {'high': 0, 'medium': 0, 'low': 0, 'fail': 0},
            'sell_accuracy': {'high': 0, 'medium': 0, 'low': 0, 'fail': 0},
            'total_signals': 0
        }
        
        # 对每个时间点预测
        for i in range(20, len(df) - 10):
            signal = self.predict_signal(df, i)
            
            if signal == 'buy':
                deviation = self.calculate_deviation(
                    df.iloc[i]['low'], df.iloc[i]['date'], df, 'buy', window=10
                )
                
                if deviation is not None:
                    results['buy_predictions'].append({
                        'date': df.iloc[i]['date'],
                        'price': df.iloc[i]['close'],
                        'deviation': deviation
                    })
                    
                    if deviation < 3:
                        results['buy_accuracy']['high'] += 1
                    elif deviation < 5:
                        results['buy_accuracy']['medium'] += 1
                    elif deviation < 10:
                        results['buy_accuracy']['low'] += 1
                    else:
                        results['buy_accuracy']['fail'] += 1
                    
                    results['total_signals'] += 1
            
            elif signal == 'sell':
                deviation = self.calculate_deviation(
                    df.iloc[i]['high'], df.iloc[i]['date'], df, 'sell', window=10
                )
                
                if deviation is not None:
                    results['sell_predictions'].append({
                        'date': df.iloc[i]['date'],
                        'price': df.iloc[i]['close'],
                        'deviation': deviation
                    })
                    
                    if deviation < 3:
                        results['sell_accuracy']['high'] += 1
                    elif deviation < 5:
                        results['sell_accuracy']['medium'] += 1
                    elif deviation < 10:
                        results['sell_accuracy']['low'] += 1
                    else:
                        results['sell_accuracy']['fail'] += 1
                    
                    results['total_signals'] += 1
        
        return results
    
    def backtest_all(self):
        """回测所有股票"""
        all_results = []
        
        print("=" * 60)
        print("买点卖点预测准确率回测")
        print("=" * 60)
        
        for code in self.stock_pool:
            result = self.backtest_stock(code)
            if result:
                all_results.append(result)
        
        # 统计总体准确率
        total_buy = {'high': 0, 'medium': 0, 'low': 0, 'fail': 0}
        total_sell = {'high': 0, 'medium': 0, 'low': 0, 'fail': 0}
        
        for r in all_results:
            for level in ['high', 'medium', 'low', 'fail']:
                total_buy[level] += r['buy_accuracy'][level]
                total_sell[level] += r['sell_accuracy'][level]
        
        total_buy_signals = sum(total_buy.values())
        total_sell_signals = sum(total_sell.values())
        
        print(f"\n买点预测统计 (共{total_buy_signals}次信号):")
        if total_buy_signals > 0:
            print(f"  高准确(偏离<3%): {total_buy['high']} ({total_buy['high']/total_buy_signals*100:.1f}%)")
            print(f"  中准确(偏离<5%): {total_buy['medium']} ({total_buy['medium']/total_buy_signals*100:.1f}%)")
            print(f"  低准确(偏离<10%): {total_buy['low']} ({total_buy['low']/total_buy_signals*100:.1f}%)")
            print(f"  失败(偏离>=10%): {total_buy['fail']} ({total_buy['fail']/total_buy_signals*100:.1f}%)")
            
            buy_accuracy_rate = (total_buy['high'] + total_buy['medium']) / total_buy_signals * 100
            print(f"  ✓ 买点准确率: {buy_accuracy_rate:.1f}%")
        
        print(f"\n卖点预测统计 (共{total_sell_signals}次信号):")
        if total_sell_signals > 0:
            print(f"  高准确(偏离<3%): {total_sell['high']} ({total_sell['high']/total_sell_signals*100:.1f}%)")
            print(f"  中准确(偏离<5%): {total_sell['medium']} ({total_sell['medium']/total_sell_signals*100:.1f}%)")
            print(f"  低准确(偏离<10%): {total_sell['low']} ({total_sell['low']/total_sell_signals*100:.1f}%)")
            print(f"  失败(偏离>=10%): {total_sell['fail']} ({total_sell['fail']/total_sell_signals*100:.1f}%)")
            
            sell_accuracy_rate = (total_sell['high'] + total_sell['medium']) / total_sell_signals * 100
            print(f"  ✓ 卖点准确率: {sell_accuracy_rate:.1f}%")
        
        print("\n" + "=" * 60)
        
        return {
            'buy': total_buy,
            'sell': total_sell,
            'buy_accuracy_rate': buy_accuracy_rate if total_buy_signals > 0 else 0,
            'sell_accuracy_rate': sell_accuracy_rate if total_sell_signals > 0 else 0,
            'details': all_results
        }
    
    def close(self):
        self.conn.close()
        self.ml_predictor.close()


if __name__ == '__main__':
    backtest = BuySellBacktest()
    results = backtest.backtest_all()
    backtest.close()
    
    print("\n回测完成！")