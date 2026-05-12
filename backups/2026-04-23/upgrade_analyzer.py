# -*- coding: utf-8 -*-
"""升级analyzer_v4.py支持多指数"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 读取原文件
with open(r'E:\csi10\analyzer_v4.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到get_market_adjustment函数并替换
old_func_start = 'def get_market_adjustment(conn):'
old_func_end = 'return 1.0, 0, "数据获取异常", 60, 15, 25, -10, 0.15, []'

# 新函数代码
new_func = '''def get_market_adjustment(conn):
    """获取大盘调整参数和状态 - 增强版（多指数支持）"""
    try:
        # 查询沪深300
        hs300_df = pd.read_sql(
            "SELECT * FROM index_daily WHERE code='sh.000300' ORDER BY date DESC LIMIT 5",
            conn
        )
        
        # 查询中证500
        zz500_df = pd.read_sql(
            "SELECT * FROM index_daily WHERE code='sh.000905' ORDER BY date DESC LIMIT 5",
            conn
        )
        
        if len(hs300_df) < 5:
            return 1.0, 0, "无大盘数据", 60, 15, 25, -10, 0.15, [], {}, {}
        
        # 计算5日涨跌幅
        hs300_pct = (hs300_df.iloc[0]['close'] - hs300_df.iloc[4]['close']) / hs300_df.iloc[4]['close'] * 100
        
        # 中证500涨跌幅（如果有数据）
        zz500_pct = 0
        if len(zz500_df) >= 5:
            zz500_pct = (zz500_df.iloc[0]['close'] - zz500_df.iloc[4]['close']) / zz500_df.iloc[4]['close'] * 100
        
        # 综合指数（沪深60% + 中证40%）
        market_pct = hs300_pct * 0.6 + zz500_pct * 0.4
        
        # 计算分歧度
        divergence = abs(hs300_pct - zz500_pct)
        
        # 自适应阈值（基于综合指数）
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
        
        # 返回增强数据
        recent_hs300 = hs300_df[['date', 'close', 'pct_chg']].iloc[::-1].to_dict('records')
        recent_zz500 = zz500_df[['date', 'close', 'pct_chg']].iloc[::-1].to_dict('records') if len(zz500_df) >= 5 else []
        
        indices_data = {
            'hs300': {'name': '沪深300', 'pct_5d': round(hs300_pct, 2), 'latest': hs300_df.iloc[0]['close']},
            'zz500': {'name': '中证500', 'pct_5d': round(zz500_pct, 2), 'latest': zz500_df.iloc[0]['close'] if len(zz500_df) > 0 else 0},
            'composite': {'name': '综合指数', 'pct_5d': round(market_pct, 2)},
            'divergence': round(divergence, 2),
            'dominant': '大盘股' if hs300_pct > zz500_pct else '中小盘',
        }
        
        return factor, round(market_pct, 2), status, buy_threshold, sell_threshold, stop_profit, stop_loss, suggest_position, recent_hs300, indices_data, recent_zz500
        
    except Exception as e:
        return 1.0, 0, "数据获取异常", 60, 15, 25, -10, 0.15, [], {}, {}'''

# 替换函数（使用正则匹配）
import re
pattern = r'def get_market_adjustment\(conn\):.*?return 1\.0, 0, "数据获取异常", 60, 15, 25, -10, 0\.15, \[\]'
match = re.search(pattern, content, re.DOTALL)

if match:
    content = content[:match.start()] + new_func + content[match.end():]
    print("✓ get_market_adjustment replaced successfully")
else:
    print("✗ Pattern not found")
    # 备用方案：直接插入
    if old_func_start in content:
        insert_pos = content.find(old_func_start)
        # 找到函数结束位置（下一个def或class）
        next_def = content.find('\ndef ', insert_pos + 1)
        if next_def > 0:
            content = content[:insert_pos] + new_func + content[next_def:]
            print("✓ Function replaced by insertion")

# 修改调用处（line 168）
# 从：factor, market_pct, market_status, buy_threshold, sell_threshold, stop_profit, stop_loss, suggest_position, recent_5d = get_market_adjustment(conn)
# 改为：factor, market_pct, market_status, buy_threshold, sell_threshold, stop_profit, stop_loss, suggest_position, recent_5d, indices_data, recent_zz500 = get_market_adjustment(conn)

old_call = '''factor, market_pct, market_status, buy_threshold, sell_threshold, stop_profit, stop_loss, suggest_position, recent_5d = get_market_adjustment(conn)'''
new_call = '''factor, market_pct, market_status, buy_threshold, sell_threshold, stop_profit, stop_loss, suggest_position, recent_5d, indices_data, recent_zz500 = get_market_adjustment(conn)'''

if old_call in content:
    content = content.replace(old_call, new_call)
    print("✓ Call updated to receive new parameters")

# 修改result.json输出部分（添加indices数据）
if "'market':" in content:
    # 在market部分添加indices和zz500数据
    old_market = '''    'market': {
        'status': market_status,
        'pct_5d': round(market_pct, 2),
        'factor': factor,
        'buy_threshold': buy_threshold,
        'sell_threshold': sell_threshold,
        'stop_profit': stop_profit,
        'stop_loss': stop_loss,
        'suggest_position': round(suggest_position * 100, 0),
        'recent_5d': recent_5d,
    },'''
    
    new_market = '''    'market': {
        'status': market_status,
        'pct_5d': round(market_pct, 2),
        'factor': factor,
        'buy_threshold': buy_threshold,
        'sell_threshold': sell_threshold,
        'stop_profit': stop_profit,
        'stop_loss': stop_loss,
        'suggest_position': round(suggest_position * 100, 0),
        'recent_5d': recent_5d,
        'indices': indices_data,
        'recent_zz500': recent_zz500,
    },'''
    
    content = content.replace(old_market, new_market)
    print("✓ Market output enhanced with indices data")

# 写回文件
with open(r'E:\csi10\analyzer_v4.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ analyzer_v4.py upgraded successfully!")
print("Next: Test analyzer_v4.py to verify changes")