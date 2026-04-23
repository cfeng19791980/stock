# -*- coding: utf-8 -*-
"""
csi10 反馈监控系统 - 跟踪预测准确率
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta

DB_PATH = r'E:\csi10\stocks.db'
PREDICTION_TABLE = 'prediction_logs_v5'

print("=" * 60)
print("csi10 反馈监控系统")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)

# 初始化表（如果不存在）
conn.execute(f'''CREATE TABLE IF NOT EXISTS {PREDICTION_TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT,
    predict_date TEXT,
    predict_score INTEGER,
    predict_action TEXT,
    predict_price REAL,
    actual_result TEXT DEFAULT 'pending',
    actual_return REAL DEFAULT 0,
    feedback_time TEXT
)''')

def update_feedback():
    """更新预测反馈"""
    cursor = conn.cursor()
    
    # 获取pending状态的预测（3天前的）
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    
    cursor.execute(f'''SELECT id, stock_code, predict_date, predict_price
        FROM {PREDICTION_TABLE}
        WHERE actual_result = 'pending' AND predict_date <= ?''',
        (three_days_ago,))
    
    pending = cursor.fetchall()
    
    print(f"\n待更新预测: {len(pending)}条")
    
    for pred_id, code, pred_date, pred_price in pending:
        try:
            # 获取实际收盘价（3天后）
            cursor.execute(f'''SELECT close FROM daily_price
                WHERE code = ? AND date >= ?
                ORDER BY date LIMIT 1''',
                (code.split('.')[0], pred_date))
            
            result = cursor.fetchone()
            if result:
                actual_price = result[0]
                actual_return = (actual_price - pred_price) / pred_price * 100
                
                # 判断成功
                actual_result = 'success' if actual_return >= 3 else 'fail'
                
                # 更新记录
                cursor.execute(f'''UPDATE {PREDICTION_TABLE}
                    SET actual_result = ?, actual_return = ?, feedback_time = ?
                    WHERE id = ?''',
                    (actual_result, actual_return, datetime.now().isoformat(), pred_id))
                
                print(f"  {code}: {pred_date} -> {actual_result} ({actual_return:.1f}%)")
        
        except Exception as e:
            continue
    
    conn.commit()

def calculate_accuracy(days=30):
    """计算准确率"""
    cursor = conn.cursor()
    
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    cursor.execute(f'''SELECT
        predict_action,
        actual_result,
        COUNT(*) as count
        FROM {PREDICTION_TABLE}
        WHERE predict_date >= ? AND actual_result != 'pending'
        GROUP BY predict_action, actual_result''',
        (start_date,))
    
    results = cursor.fetchall()
    
    print(f"\n最近{days}天准确率统计:")
    
    buy_success = 0
    buy_fail = 0
    total_success = 0
    total_fail = 0
    
    for action, result, count in results:
        print(f"  {action} - {result}: {count}次")
        if action == 'buy':
            if result == 'success':
                buy_success += count
            else:
                buy_fail += count
        total_success += count if result == 'success' else 0
        total_fail += count if result == 'fail' else 0
    
    if buy_success + buy_fail > 0:
        buy_accuracy = buy_success / (buy_success + buy_fail) * 100
        print(f"\n买入信号准确率: {buy_accuracy:.1f}% ({buy_success}/{buy_success+buy_fail})")
    
    if total_success + total_fail > 0:
        total_accuracy = total_success / (total_success + total_fail) * 100
        print(f"总体准确率: {total_accuracy:.1f}% ({total_success}/{total_success+total_fail})")
    
    return buy_accuracy if buy_success + buy_fail > 0 else 0

def generate_report():
    """生成报告"""
    cursor = conn.cursor()
    
    cursor.execute(f'''SELECT
        predict_date,
        COUNT(*) as total,
        SUM(CASE WHEN actual_result = 'success' THEN 1 ELSE 0 END) as success,
        AVG(actual_return) as avg_return
        FROM {PREDICTION_TABLE}
        WHERE actual_result != 'pending'
        GROUP BY predict_date
        ORDER BY predict_date DESC
        LIMIT 7''')
    
    recent = cursor.fetchall()
    
    print("\n最近7天预测表现:")
    print("日期       | 预测数 | 成功数 | 平均收益")
    print("-" * 40)
    for date, total, success, avg_ret in recent:
        print(f"{date} | {total}     | {success}     | {avg_ret:.1f}%")
    
    # 保存报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'recent_7d': [{
            'date': r[0],
            'total': r[1],
            'success': r[2],
            'avg_return': round(r[3], 2) if r[3] else 0
        } for r in recent],
    }
    
    with open(r'E:\csi10\feedback_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n报告已保存: feedback_report.json")

# 执行
update_feedback()
accuracy = calculate_accuracy(30)
generate_report()

# 准确率警报
if accuracy < 55:
    print(f"\n⚠️ 警报: 买入准确率低于55% ({accuracy:.1f}%)")
    print("  建议: 检查模型参数或暂停交易")

conn.close()
print("=" * 60)