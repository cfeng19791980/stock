# -*- coding: utf-8 -*-
"""测试Brain Hook API"""
import sys, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("Brain Hook API测试")
print("=" * 70)

# 测试决策API
test_queries = [
    "修复卖出建议逻辑",
    "更新Electron配置",
    "删除所有文件",  # P3高风险
    "查询股票数据"
]

for query in test_queries:
    data = json.dumps({"query": query}).encode('utf-8')
    
    try:
        req = urllib.request.Request(
            'http://localhost:5000/decide',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            
            print(f"\n查询: {query}")
            print(f"  decision_id: {result['decision_id']}")
            print(f"  confidence: {result['confidence']}")
            print(f"  action: {result['action']}")
            print(f"  reason: {result['reason']}")
            
    except Exception as e:
        print(f"\n查询: {query}")
        print(f"  ❌ 错误: {e}")

print("\n" + "=" * 70)
print("完成")
print("=" * 70)