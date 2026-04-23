# -*- coding: utf-8 -*-
"""
大盘走势权重调整模块
功能: 根据大盘走势调整个股评分
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import pandas as pd

DB_PATH = r'E:\股票\csi500_data\stocks.db'

def get_market_adjustment():
    """获取大盘调整因子和状态"""
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # 读取沪深300最近5日数据
        df = pd.read_sql(
            "SELECT * FROM index_daily WHERE code='sh.000300' ORDER BY date DESC LIMIT 5",
            conn
        )
        
        if len(df) < 5:
            return 1.0, 0, "无大盘数据", []
        
        # 计算5日涨幅
        first_close = df.iloc[-1]['close']
        last_close = df.iloc[0]['close']
        market_pct = (last_close - first_close) / first_close * 100
        
        # 计算调整因子
        if market_pct >= 3:
            factor = 1.10
            status = "强势市场"
        elif market_pct >= 1:
            factor = 1.05
            status = "偏强市场"
        elif market_pct >= -1:
            factor = 1.0
            status = "震荡市场"
        elif market_pct >= -3:
            factor = 0.95
            status = "偏弱市场"
        else:
            factor = 0.85
            status = "弱势市场"
        
        # 返回最近5日数据
        recent = df[['date', 'close', 'pct_chg']].iloc[::-1].to_dict('records')
        
        return factor, market_pct, status, recent
    
    finally:
        conn.close()

def adjust_score(original_score, factor):
    """调整评分"""
    adjusted = int(original_score * factor)
    return min(100, max(0, adjusted))  # 限制在0-100

# 测试
print("=" * 60)
print("大盘走势权重调整测试")
print("=" * 60)

factor, market_pct, status, recent = get_market_adjustment()

print(f"\n大盘状态: {status}")
print(f"沪深300 5日涨跌: {market_pct:.2f}%")
print(f"调整因子: {factor}")

if recent:
    print(f"\n最近5日走势:")
    for r in recent:
        print(f"  {r['date']} 收盘:{r['close']:.2f} 涨跌:{r['pct_chg']:.2f}%")

# 模拟评分调整
test_scores = [75, 60, 45, 80, 30]
print(f"\n评分调整示例:")
for s in test_scores:
    adj = adjust_score(s, factor)
    change = adj - s
    print(f"  原评分{s} -> 新评分{adj} (变化{change:+d})")

print("\n" + "=" * 60)
print("权重调整逻辑")
print("=" * 60)
print("""
大盘5日涨幅  |  调整因子  |  影响
>= +3%      |   1.10    |  评分+10%
>= +1%      |   1.05    |  评分+5%
-1% ~ +1%   |   1.00    |  不调整
>= -3%      |   0.95    |  评分-5%
< -3%       |   0.85    |  评分-15%

示例:
个股评分75分 + 大盘涨幅+2.5% = 新评分78分(提升)
个股评分60分 + 大盘涨幅-2.8% = 新评分57分(降低)
""")