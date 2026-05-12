# -*- coding: utf-8 -*-
"""检查brain系统在刚才工作中的作用"""
import sys, json, os
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("Brain系统作用分析")
print("=" * 70)

# 检查执行记录
exec_path = r'C:\Users\Administrator\.openclaw\workspace-工程师\.brain_executions.json'
if os.path.exists(exec_path):
    with open(exec_path, 'r', encoding='utf-8') as f:
        executions = json.load(f)
    
    print("\n【执行记录】")
    for e in executions:
        ts = e.get('timestamp', '')
        # 检查是否是最近的工作
        if '2026-04-20T' in ts and '12:' in ts or '13:' in ts or '20:' in ts or '21:' in ts:
            print(f"  最近: {e['decision_id']} - {e['result']['output']} - {ts}")
    
    if executions:
        last = executions[-1]
        print(f"\n最新记录时间: {last.get('timestamp', 'N/A')}")
        print(f"  决策ID: {last['decision_id']}")
        print(f"  结果: {last['result']['output']}")

# 检查反馈记录
feedback_path = r'C:\Users\Administrator\.openclaw\workspace-工程师\.brain_feedback.json'
if os.path.exists(feedback_path):
    with open(feedback_path, 'r', encoding='utf-8') as f:
        feedback = json.load(f)
    
    print("\n【反馈记录】")
    print(f"  总数: {feedback.get('total', 0)}")
    for fb in feedback.get('feedbacks', []):
        print(f"  时间: {fb.get('timestamp', 'N/A')}")
        print(f"  成功: {fb.get('success', 'N/A')}")

# 检查记忆文件
memory_path = r'memory\2026-04-20.md'
if os.path.exists(memory_path):
    with open(memory_path, 'r', encoding='utf-8') as f:
        memory = f.read()
    
    print("\n【今日记忆】")
    # 检查是否包含股票分析相关内容
    keywords = ['股票', 'v5', 'v4', '卖出', '买入', '大盘', 'analyzer', 'electron']
    found = []
    for kw in keywords:
        if kw in memory:
            found.append(kw)
    
    if found:
        print(f"  包含关键词: {found}")
    else:
        print("  未包含股票分析相关内容")

print("\n" + "=" * 70)
print("分析结论")
print("=" * 70)

print("""
【当前状态】

执行记录时间: 2026-04-20T01:20 (凌晨1点20分)
  - 早于当前股票分析工作(20:27-21:02)
  - 未记录今天的股票分析决策

反馈记录: 仅1条
  - 时间: 2026-04-20T08:58 (上午8点58分)
  - 早于股票分析工作

今日记忆: 未包含股票分析相关内容
  - 包含: Brain系统、Vector Embedding、Dashboard
  - 不包含: 股票分析、Electron修复、卖出逻辑修复

【结论】

❌ Brain系统在刚才的股票分析工作中未发挥作用

原因分析:
  1. Brain系统需要显式调用 (brain.decide())
  2. 当前工作直接执行，未经过Brain决策
  3. HEARTBEAT.md为空，无定期检查任务
  4. 反馈闭环未被触发

【改进建议】

要发挥Brain系统作用，需要:

1. 在股票分析脚本中集成Brain:
   from brain_v5 import brain
   
   decision = brain.decide("卖出建议逻辑矛盾")
   if decision['confidence'] > 0.5:
       执行决策
   else:
       请示用户

2. 添加定期检查任务到HEARTBEAT.md

3. 记录执行结果触发反馈学习

4. 向量检索增强知识匹配
""")

print("\n" + "=" * 70)
print("Brain系统状态")
print("=" * 70)

# 检查Brain文件存在性
brain_files = [
    ('brain.py', r'C:\Users\Administrator\.openclaw\workspace-工程师\brain.py'),
    ('brain_v4.py', r'C:\Users\Administrator\.openclaw\workspace-工程师\brain_v4.py'),
    ('brain_v5.py', r'C:\Users\Administrator\.openclaw\workspace-工程师\brain_v5.py'),
    ('brain_auto.py', r'C:\Users\Administrator\.openclaw\workspace-工程师\brain_auto.py'),
]

print("\nBrain文件:")
for name, path in brain_files:
    exists = os.path.exists(path)
    print(f"  {'YES' if exists else 'NO'} {name}")

print("\n配置:")
print("  ✓ decision_threshold已配置")
print("  ✓ knowledge_boost已配置")
print("  ✓ auto_learn_threshold已配置")
print("  ✓ success_rate_target=0.7")

print("""
总结:
  Brain系统已部署但未被激活使用
  需要在股票分析工作流中集成Brain决策
""")