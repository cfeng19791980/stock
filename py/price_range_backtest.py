# -*- coding: utf-8 -*-
"""
价格区间预测回测
验证预测的买点卖点价格是否准确
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import sqlite3

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

# 导入预测器
import price_range_predictor

class PriceRangeBacktest:
    """价格区间回测器"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        self.predictor = price_range_predictor.PriceRangePredictor()
        self.predictor.train_models()
    
    def get_stock_data(self, code, days=120):
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
    
    def backtest_stock(self, code):
        """回测单只股票"""
        df = self.get_stock_data(code, 120)
        if df is None or len(df) < 50:
            return None
        
        lookahead = 10  # 验证未来10天
        
        results = []
        
        # 对历史数据回测
        for i in range(30, len(df) - lookahead):
            # 预测
            pred = self.predictor.predict_price_range(df, i)
            if pred is None:
                continue
            
            # 实际未来数据
            future = df.iloc[i+1:i+lookahead+1]
            actual_low = future['low'].min()
            actual_high = future['high'].max()
            
            # 预测买点
            pred_buy_low = pred['buy_range']['low']
            pred_buy_high = pred['buy_range']['high']
            pred_buy_center = pred['buy_range']['center']
            
            # 预测卖点
            pred_sell_low = pred['sell_range']['low']
            pred_sell_high = pred['sell_range']['high']
            pred_sell_center = pred['sell_range']['center']
            
            # 买点准确率
            # 实际最低价落在预测区间内？
            buy_hit = actual_low >= pred_buy_low and actual_low <= pred_buy_high
            buy_deviation = abs(pred_buy_center - actual_low) / actual_low * 100
            
            # 卖点准确率
            # 实际最高价落在预测区间内？
            sell_hit = actual_high >= pred_sell_low and actual_high <= pred_sell_high
            sell_deviation = abs(pred_sell_center - actual_high) / actual_high * 100
            
            results.append({
                'date': df.iloc[i]['date'],
                'buy_pred_center': pred_buy_center,
                'buy_pred_range': f"{pred_buy_low}-{pred_buy_high}",
                'actual_low': actual_low,
                'buy_hit': buy_hit,
                'buy_deviation': buy_deviation,
                'sell_pred_center': pred_sell_center,
                'sell_pred_range': f"{pred_sell_low}-{pred_sell_high}",
                'actual_high': actual_high,
                'sell_hit': sell_hit,
                'sell_deviation': sell_deviation
            })
        
        return results
    
    def backtest_all(self):
        """回测所有股票"""
        print("\n" + "=" * 60)
        print("价格区间预测回测")
        print("=" * 60)
        
        all_results = []
        
        for code in self.stock_pool[:10]:  # 先测试10只
            print(f"\n回测 {code}...")
            results = self.backtest_stock(code)
            if results:
                all_results.extend(results)
        
        # 统计准确率
        buy_hits = sum([r['buy_hit'] for r in all_results])
        sell_hits = sum([r['sell_hit'] for r in all_results])
        total = len(all_results)
        
        buy_avg_deviation = np.mean([r['buy_deviation'] for r in all_results])
        sell_avg_deviation = np.mean([r['sell_deviation'] for r in all_results])
        
        print("\n" + "=" * 60)
        print(f"回测样本数: {total}")
        print("=" * 60)
        
        print(f"\n买点预测准确率:")
        print(f"  区间命中率: {buy_hits}/{total} ({buy_hits/total*100:.1f}%)")
        print(f"  平均偏离度: {buy_avg_deviation:.2f}%")
        print(f"  偏离度分布:")
        print(f"    <1%: {len([r for r in all_results if r['buy_deviation']<1])}次")
        print(f"    <2%: {len([r for r in all_results if r['buy_deviation']<2])}次")
        print(f"    <3%: {len([r for r in all_results if r['buy_deviation']<3])}次")
        print(f"    <5%: {len([r for r in all_results if r['buy_deviation']<5])}次")
        print(f"    >=5%: {len([r for r in all_results if r['buy_deviation']>=5])}次")
        
        print(f"\n卖点预测准确率:")
        print(f"  区间命中率: {sell_hits}/{total} ({sell_hits/total*100:.1f}%)")
        print(f"  平均偏离度: {sell_avg_deviation:.2f}%")
        print(f"  偏离度分布:")
        print(f"    <2%: {len([r for r in all_results if r['sell_deviation']<2])}次")
        print(f"    <5%: {len([r for r in all_results if r['sell_deviation']<5])}次")
        print(f"    <7%: {len([r for r in all_results if r['sell_deviation']<7])}次")
        print(f"    <10%: {len([r for r in all_results if r['sell_deviation']<10])}次")
        print(f"    >=10%: {len([r for r in all_results if r['sell_deviation']>=10])}次")
        
        # 显示部分预测结果
        print("\n" + "=" * 60)
        print("预测示例（前5个）:")
        print("=" * 60)
        for r in all_results[:5]:
            print(f"\n{r['date']}:")
            print(f"  买点预测: {r['buy_pred_range']} (中心{r['buy_pred_center']:.2f})")
            print(f"  实际最低: {r['actual_low']:.2f} (偏离{r['buy_deviation']:.2f}%) {'✓命中' if r['buy_hit'] else '✗未中'}")
            print(f"  卖点预测: {r['sell_pred_range']} (中心{r['sell_pred_center']:.2f})")
            print(f"  实际最高: {r['actual_high']:.2f} (偏离{r['sell_deviation']:.2f}%) {'✓命中' if r['sell_hit'] else '✗未中'}")
        
        return all_results
    
    def close(self):
        self.conn.close()
        self.predictor.close()


if __name__ == '__main__':
    backtest = PriceRangeBacktest()
    results = backtest.backtest_all()
    backtest.close()
    
    print("\n回测完成！")