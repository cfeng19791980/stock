# -*- coding: utf-8 -*-
"""
项目全面审查报告 - 以准确性为最高原则
审查时间: 2026-04-18 17:03
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import json
import os

print("=" * 70)
print("股票分析系统全面审查报告")
print("最高原则: 准确性第一")
print("=" * 70)

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
JSON_PATH = r'e:\csi10\result.json'

# ========================================
# 审查1: 数据实时性
# ========================================
print("\n【审查1】数据库数据实时性")
print("-" * 70)

conn = sqlite3.connect(DB_PATH)

# 检查最新数据日期
query = "SELECT MAX(date) as max_date FROM daily_price"
max_date = conn.execute(query).fetchone()[0]
print(f"数据库最新日期: {max_date}")

today = datetime.now().strftime('%Y-%m-%d')
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

if max_date == today:
    print("✅ 数据已更新到今天（实时）")
elif max_date == yesterday:
    print("⚠️ 数据更新到昨天（可能是非交易日）")
else:
    print(f"❌ 数据滞后！最新日期: {max_date}，今天: {today}")
    print("   建议：立即运行数据更新程序")

# 检查数据覆盖范围
query = """
SELECT date, COUNT(DISTINCT code) as stock_count, COUNT(*) as total_records
FROM daily_price
WHERE date >= '2026-04-01'
GROUP BY date
ORDER BY date DESC
LIMIT 20
"""
recent_data = pd.read_sql(query, conn)
print("\n最近20天数据覆盖:")
print(recent_data.to_string(index=False))

# 检查股票池覆盖
stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
query = f"""
SELECT code, MAX(date) as latest_date, COUNT(*) as data_count
FROM daily_price
WHERE code IN ({','.join([f"'{c}'" for c in stock_pool])})
GROUP BY code
ORDER BY latest_date DESC
"""
stock_coverage = pd.read_sql(query, conn)
print(f"\n股票池覆盖检查（{len(stock_pool)}只）:")
outdated_stocks = stock_coverage[stock_coverage['latest_date'] < today]
if len(outdated_stocks) > 0:
    print(f"❌ 数据滞后的股票: {len(outdated_stocks)}只")
    print(outdated_stocks.to_string(index=False))
else:
    print("✅ 所有股票数据都已更新到今天")

conn.close()

# ========================================
# 审查2: 模型版本和准确率
# ========================================
print("\n【审查2】模型版本和准确率")
print("-" * 70)

# 检查分析引擎文件
files = [
    ('analyzer_json.py', '简化版（已废弃）'),
    ('analyzer_json_full.py', '完整版（当前）'),
    ('final_v2_clean.py', 'Flask版（旧架构）'),
    ('buysell_predictor_v5.py', '买点卖点预测器')
]

print("\n分析引擎文件:")
for filename, desc in files:
    filepath = f'e:/csi10/{filename}'
    if os.path.exists(filepath):
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        size = os.path.getsize(filepath)
        print(f"  {filename}: {size}字节, 更新时间: {mtime}")
    else:
        print(f"  {filename}: ❌ 不存在")

# 检查当前使用的版本
if os.path.exists('e:/csi10/main_json.js'):
    with open('e:/csi10/main_json.js', 'r', encoding='utf-8') as f:
        content = f.read()
        if 'analyzer_json_full.py' in content:
            print("✅ Electron使用完整版（analyzer_json_full.py）")
        elif 'analyzer_json.py' in content:
            print("❌ Electron使用简化版（需立即修复）")

# 检查JSON输出准确率
if os.path.exists(JSON_PATH):
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n当前JSON输出准确率: {data['avg_accuracy']:.2%}")
    print(f"买点MAE: {data['buysell_buy_mae']}%")
    print(f"卖点MAE: {data['buysell_sell_mae']}%")
    
    # 检查特征数量
    if data['stocks'][0]:
        print(f"股票数量: {data['stock_count']}只")
        print(f"买入信号: {data['buy_count']}只")
        print(f"卖出信号: {data['sell_count']}只")

# ========================================
# 审查3: 功能完整性
# ========================================
print("\n【审查3】功能完整性检查")
print("-" * 70)

# 必备功能清单
required_features = {
    '43特征XGBoost模型': 'analyzer_json_full.py',
    '买点卖点预测': 'buysell_predictor_v5.py',
    '大盘因子': 'index_daily表',
    '实时数据更新': 'data_fetcher.py',
    '股票名称映射': 'stock_names.py',
}

for feature, source in required_features.items():
    if source.endswith('.py'):
        if os.path.exists(f'e:/csi10/{source}'):
            print(f"✅ {feature}: {source}")
        else:
            print(f"❌ {feature}: {source} 缺失")
    elif source.endswith('表'):
        conn = sqlite3.connect(DB_PATH)
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {source.split('表')[0]}").fetchone()[0]
            print(f"✅ {feature}: {source} ({count}条)")
        except:
            print(f"❌ {feature}: {source} 不存在或无数据")
        conn.close()

# ========================================
# 审查4: 实时数据计算流程
# ========================================
print("\n【审查4】实时数据计算流程")
print("-" * 70)

print("\n启动流程检查:")
print("1. Electron启动 → 运行analyzer_json_full.py")
print("2. analyzer_json_full.py → 从数据库读取最新数据")
print("3. 使用完整43特征进行预测")
print("4. 买点卖点预测器计算最优价格")
print("5. 输出result.json（实时数据）")
print("6. Electron前端读取result.json显示")

# 检查是否有缓存机制影响实时性
print("\n⚠️ 潜在问题:")
print("  1. 如果数据库未更新，分析结果会滞后")
print("  2. 刷新按钮会重新运行分析引擎（实时）")
print("  3. 启动时会同步运行分析引擎（实时）")

# ========================================
# 审查5: 数据更新机制
# ========================================
print("\n【审查5】数据更新机制")
print("-" * 70)

# 检查数据更新脚本
update_scripts = ['data_fetcher.py', 'update_data.py', 'fetch_daily.py']
existing_scripts = []
for script in update_scripts:
    if os.path.exists(f'e:/csi10/{script}'):
        existing_scripts.append(script)

if existing_scripts:
    print(f"✅ 数据更新脚本: {existing_scripts}")
else:
    print("❌ 无数据更新脚本！")

# 检查是否有定时更新机制
cron_files = ['start.bat', '启动.bat', 'run.bat']
print("\n启动脚本检查:")
for script in cron_files:
    if os.path.exists(f'e:/csi10/{script}'):
        print(f"  {script}: 存在")

# ========================================
# 总结和建议
# ========================================
print("\n" + "=" * 70)
print("审查总结")
print("=" * 70)

issues = []
recommendations = []

# 检查问题
if max_date < today:
    issues.append(f"❌ 数据滞后: {max_date} < {today}")

if 'analyzer_json_full.py' not in content:
    issues.append("❌ 使用简化版分析引擎")

# 生成建议
recommendations = [
    "1. 每交易日开盘前自动更新数据库",
    "2. 使用完整版分析引擎（43特征）",
    "3. 每次启动强制重新计算（无缓存）",
    "4. 添加数据更新定时任务",
    "5. 前端显示数据更新时间提醒用户",
]

print("\n发现问题:")
for issue in issues:
    print(f"  {issue}")

print("\n改进建议:")
for rec in recommendations:
    print(f"  {rec}")

print("\n" + "=" * 70)
print("审查完成")
print("=" * 70)