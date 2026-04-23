# -*- coding: utf-8 -*-
"""系统级Review - 检查关联文件同步状态"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

print("="*70)
print("系统级Review - csi10多指数系统")
print("="*70)

# 1. 检查analyzer_v4.py的输出字段
print("\n[1] analyzer_v4.py输出字段")
with open(r'E:\csi10\analyzer_v4.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
    # 检查market字段
    required_fields = [
        'status', 'pct_5d', 'factor', 'buy_threshold', 
        'sell_threshold', 'stop_profit', 'stop_loss', 'suggest_position',
        'indices', 'recent_zz500'
    ]
    
    missing_fields = []
    for field in required_fields:
        if f"'{field}'" not in content and f'"{field}"' not in content:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"✗ Missing fields in analyzer_v4.py: {missing_fields}")
    else:
        print("✓ All required fields present in analyzer_v4.py")

# 2. 检查index.html的元素ID
print("\n[2] index.html元素ID")
with open(r'E:\csi10\index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()
    
    required_ids = [
        'marketStatus', 'marketPct', 'marketFactor', 'marketThreshold',
        'sellThreshold', 'stopProfit', 'stopLoss', 'suggestPosition',
        'hs300Pct', 'zz500Pct', 'divergence', 'hs300Latest', 'zz500Latest', 'dominant'
    ]
    
    missing_ids = []
    for id in required_ids:
        if f"id='{id}'" not in html_content and f'id="{id}"' not in html_content:
            missing_ids.append(id)
    
    if missing_ids:
        print(f"✗ Missing element IDs in index.html: {missing_ids}")
    else:
        print("✓ All required element IDs present in index.html")

# 3. 检查index.html的displayMarket函数
print("\n[3] index.html displayMarket函数")
with open(r'E:\csi10\index.html', 'r', encoding='utf-8') as f:
    content = f.read()
    
    if 'getElementById(\'sellThreshold\')' in content:
        print("✓ displayMarket has sellThreshold")
    else:
        print("✗ displayMarket missing sellThreshold")
    
    if 'getElementById(\'hs300Pct\')' in content:
        print("✓ displayMarket has hs300Pct")
    else:
        print("✗ displayMarket missing hs300Pct")
    
    if 'getElementById(\'zz500Pct\')' in content:
        print("✓ displayMarket has zz500Pct")
    else:
        print("✗ displayMarket missing zz500Pct")

# 4. 检查result.json实际数据
print("\n[4] result.json实际数据")
try:
    data = json.load(open(r'E:\csi10\result.json', 'r', encoding='utf-8'))
    market = data.get('market', {})
    
    # 检查market字段
    for field in ['status', 'pct_5d', 'factor', 'buy_threshold', 'sell_threshold', 
                   'stop_profit', 'stop_loss', 'suggest_position', 'indices']:
        value = market.get(field)
        if value is None or value == 0 and field in ['sell_threshold', 'stop_profit', 'stop_loss', 'suggest_position']:
            print(f"⚠ market.{field} = {value} (may be missing)")
        else:
            print(f"✓ market.{field} = {value}")
    
    # 检查indices字段
    indices = market.get('indices', {})
    for field in ['hs300', 'zz500', 'composite', 'divergence', 'dominant']:
        value = indices.get(field)
        if value:
            print(f"✓ indices.{field} = {value}")
        else:
            print(f"✗ indices.{field} missing or empty")
            
except Exception as e:
    print(f"✗ Error reading result.json: {e}")

# 5. 检查数据库中证500数据
print("\n[5] 数据库中证500数据")
import sqlite3
try:
    conn = sqlite3.connect(r'E:\csi10\stocks.db')
    cursor = conn.cursor()
    
    # 检查中证500数据
    cursor.execute("SELECT COUNT(*) FROM index_daily WHERE code='sh.000905'")
    count = cursor.fetchone()[0]
    print(f"ZZ500 records in DB: {count}")
    
    if count > 0:
        cursor.execute("SELECT date, close, pct_chg FROM index_daily WHERE code='sh.000905' ORDER BY date DESC LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(f"  {row[0]}: close={row[1]}, pct_chg={row[2]}")
    else:
        print("✗ No ZZ500 data in database")
    
    conn.close()
except Exception as e:
    print(f"✗ Database error: {e}")

# 6. 字段映射一致性检查
print("\n[6] 字段映射一致性")
mappings = [
    ("market.sell_threshold", "sellThreshold"),
    ("market.stop_profit", "stopProfit"),
    ("market.stop_loss", "stopLoss"),
    ("market.suggest_position", "suggestPosition"),
    ("indices.hs300.pct_5d", "hs300Pct"),
    ("indices.zz500.pct_5d", "zz500Pct"),
    ("indices.divergence", "divergence"),
]

for backend_field, frontend_id in mappings:
    print(f"  {backend_field} → {frontend_id}")

print("\n[7] 系统文件清单")
files = [
    ('analyzer_v4.py', '后端分析引擎'),
    ('index.html', '前端界面'),
    ('market_index_enhanced.py', '多指数计算模块'),
    ('fetch_zz500_data.py', '中证500数据获取'),
    ('clean_zz500.py', '数据清理脚本'),
    ('result.json', '数据输出文件'),
    ('stocks.db', 'SQLite数据库'),
]

for filename, desc in files:
    print(f"  {filename:25} - {desc}")

print("\n" + "="*70)
print("Review Complete")
print("="*70)