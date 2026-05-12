# -*- coding: utf-8 -*-
"""
大盘指数数据获取模块 - 增强版
功能: 支持多指数查询（沪深300、中证500、上证指数）+ 分层匹配 + 综合指数计算
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import requests

DB_PATH = r'E:\csi10\stocks.db'

class MarketIndexEnhanced:
    """大盘指数数据增强版 - 三指数体系"""
    
    # 大盘指数代码映射（扩展版）
    INDEX_CODES = {
        'sh.000001': {'name': '上证指数', 'secid': '1.000001', 'tencent': 'sh000001', 'type': 'composite'},
        'sh.000300': {'name': '沪深300', 'secid': '1.000300', 'tencent': 'sh000300', 'type': 'large_cap'},
        'sh.000905': {'name': '中证500', 'secid': '1.000905', 'tencent': 'sh000905', 'type': 'mid_cap'},
    }
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        
    def fetch_all_indices(self):
        """获取所有指数的最新数据"""
        indices_data = {}
        
        # 从数据库查询
        for code in ['sh.000300', 'sh.000905', 'sh.000001']:
            df = pd.read_sql(
                f"SELECT * FROM index_daily WHERE code='{code}' ORDER BY date DESC LIMIT 20",
                self.conn
            )
            
            if len(df) > 0:
                name = self.INDEX_CODES.get(code, {}).get('name', code)
                indices_data[code] = {
                    'name': name,
                    'type': self.INDEX_CODES.get(code, {}).get('type', 'unknown'),
                    'latest': df.iloc[0].to_dict(),
                    'recent_5d': df.head(5).to_dict('records'),
                    'recent_20d': df.to_dict('records'),
                }
        
        return indices_data
    
    def calculate_5d_trend(self, df):
        """计算5日涨跌幅"""
        if len(df) < 5:
            return 0
        
        first_close = df.iloc[4]['close']  # 5天前的收盘价
        last_close = df.iloc[0]['close']   # 最新收盘价
        pct_5d = (last_close - first_close) / first_close * 100
        
        return round(pct_5d, 2)
    
    def calculate_20d_trend(self, df):
        """计算20日涨跌幅"""
        if len(df) < 20:
            return 0
        
        first_close = df.iloc[19]['close']  # 20天前的收盘价
        last_close = df.iloc[0]['close']    # 最新收盘价
        pct_20d = (last_close - first_close) / first_close * 100
        
        return round(pct_20d, 2)
    
    def get_composite_trend(self, indices_data):
        """计算综合趋势（沪深60% + 中证40%）"""
        hs300_data = indices_data.get('sh.000300', {})
        zz500_data = indices_data.get('sh.000905', {})
        
        hs300_5d = 0
        zz500_5d = 0
        
        if hs300_data.get('recent_5d'):
            hs300_df = pd.DataFrame(hs300_data['recent_5d'])
            hs300_5d = self.calculate_5d_trend(hs300_df)
        
        if zz500_data.get('recent_5d'):
            zz500_df = pd.DataFrame(zz500_data['recent_5d'])
            zz500_5d = self.calculate_5d_trend(zz500_df)
        
        # 权重分配：大盘股60%，中小盘40%
        composite_5d = hs300_5d * 0.6 + zz500_5d * 0.4
        
        # 计算分歧度（大盘vs中小盘差异）
        divergence = abs(hs300_5d - zz500_5d)
        
        return {
            'hs300_5d': hs300_5d,
            'zz500_5d': zz500_5d,
            'composite_5d': round(composite_5d, 2),
            'divergence': round(divergence, 2),
            'dominant': '大盘股' if hs300_5d > zz500_5d else '中小盘',
        }
    
    def classify_stock_type(self, market_cap=None, industry=None):
        """根据股票特征分类"""
        # 简化版分类规则
        # 大盘股：市值>500亿，传统行业（银行、能源、保险）
        # 中小盘：市值<500亿，新兴产业（科技、医药、新能源）
        
        large_cap_industries = ['银行', '保险', '石油', '煤炭', '电力', '基建', '房地产']
        mid_cap_industries = ['半导体', '新能源', '医药', '军工', '科技', '消费']
        
        if market_cap and market_cap > 500:
            return 'large_cap'
        elif market_cap and market_cap < 200:
            return 'mid_cap'
        elif industry and industry in large_cap_industries:
            return 'large_cap'
        elif industry and industry in mid_cap_industries:
            return 'mid_cap'
        else:
            return 'composite'  # 默认使用综合指数
    
    def select_index_for_stock(self, stock_type):
        """根据股票类型选择对应指数"""
        if stock_type == 'large_cap':
            return 'sh.000300'  # 沪深300
        elif stock_type == 'mid_cap':
            return 'sh.000905'  # 中证500
        else:
            return 'composite'  # 综合指数
    
    def get_market_adjustment_enhanced(self):
        """获取大盘调整参数 - 增强版"""
        try:
            indices_data = self.fetch_all_indices()
            composite_trend = self.get_composite_trend(indices_data)
            
            # 默认使用综合指数
            market_pct = composite_trend['composite_5d']
            
            # 判断市场状态（5档）
            if market_pct >= 3:
                factor = 1.05; status = "强势市场"
                buy_threshold = 55; sell_threshold = 20
                stop_profit = 30; stop_loss = -8
                suggest_position = 0.25
            elif market_pct >= 1:
                factor = 1.02; status = "偏强市场"
                buy_threshold = 58; sell_threshold = 18
                stop_profit = 25; stop_loss = -10
                suggest_position = 0.20
            elif market_pct >= -1:
                factor = 1.0; status = "震荡市场"
                buy_threshold = 60; sell_threshold = 15
                stop_profit = 20; stop_loss = -10
                suggest_position = 0.15
            elif market_pct >= -3:
                factor = 0.85; status = "偏弱市场"
                buy_threshold = 65; sell_threshold = 10
                stop_profit = 15; stop_loss = -8
                suggest_position = 0.10
            else:
                factor = 0.75; status = "弱势市场"
                buy_threshold = 70; sell_threshold = 5
                stop_profit = 10; stop_loss = -5
                suggest_position = 0.05
            
            # 返回增强版数据
            return {
                'factor': factor,
                'market_pct': market_pct,
                'status': status,
                'buy_threshold': buy_threshold,
                'sell_threshold': sell_threshold,
                'stop_profit': stop_profit,
                'stop_loss': stop_loss,
                'suggest_position': suggest_position,
                'indices': indices_data,
                'composite': composite_trend,
            }
            
        except Exception as e:
            return {
                'factor': 1.0,
                'market_pct': 0,
                'status': "数据异常",
                'buy_threshold': 60,
                'sell_threshold': 15,
                'stop_profit': 25,
                'stop_loss': -10,
                'suggest_position': 0.15,
                'indices': {},
                'composite': {},
                'error': str(e),
            }

# 单独测试
if __name__ == '__main__':
    enhancer = MarketIndexEnhanced()
    result = enhancer.get_market_adjustment_enhanced()
    
    print("="*60)
    print("大盘指数增强版测试")
    print("="*60)
    print(f"综合趋势: {result['composite']}")
    print(f"市场状态: {result['status']}")
    print(f"5日涨跌: {result['market_pct']:+.2f}%")
    print(f"买入阈值: {result['buy_threshold']}分")
    print(f"仓位建议: {result['suggest_position']*100:.0f}%")
    print("="*60)