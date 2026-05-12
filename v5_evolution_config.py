# -*- coding: utf-8 -*-
"""
v5进化目标配置
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from datetime import datetime

# v5进化目标配置
V5_CONFIG = {
    "version": "v5",
    "status": "预备版本",
    "role": "自学习进化",
    
    # 进化目标
    "evolution_target": {
        "win_rate_target": 75.0,  # 目标胜率 >75%
        "current_win_rate": 49.4,  # 当前最佳胜率（优化后）
        "gap": 30.8,  # 差距
        "milestones": [
            {"stage": "Phase 1", "target": 60.0, "priority": "P0"},
            {"stage": "Phase 2", "target": 70.0, "priority": "P1"},
            {"stage": "Phase 3", "target": 75.0, "priority": "P2"},
        ]
    },
    
    # 训练调度
    "schedule": {
        "daily_feedback": "17:00",  # 每日反馈记录
        "incremental_train": "17:00",  # 增量训练（下午5点）
        "full_train": "每月1日 17:00",  # 月度完整训练
        "backtest": "每周日 17:00",  # 回测验证
    },
    
    # 当前优化计划
    "optimization_plan": [
        {
            "id": "OPT-001",
            "name": "调整融合权重",
            "desc": "优化XGB/LGB/CAT权重比例",
            "expected_gain": "+5-10%",
            "risk": "低",
            "priority": "P0"
        },
        {
            "id": "OPT-002",
            "name": "降低买入阈值",
            "desc": "从50分降到40分测试",
            "expected_gain": "+3-5%",
            "risk": "低",
            "priority": "P0"
        },
        {
            "id": "OPT-003",
            "name": "增加有效特征",
            "desc": "筛选高相关性特征",
            "expected_gain": "+5%",
            "risk": "中",
            "priority": "P1"
        },
        {
            "id": "OPT-004",
            "name": "优化训练目标",
            "desc": "调整涨幅阈值(2%而非3%)",
            "expected_gain": "+8%",
            "risk": "中",
            "priority": "P1"
        },
        {
            "id": "OPT-005",
            "name": "增加训练数据",
            "desc": "扩展到2020年开始",
            "expected_gain": "+3%",
            "risk": "低",
            "priority": "P2"
        },
    ],
    
    # 性能基准
    "baseline": {
        "v4_win_rate": 75.0,
        "v5_current": 44.2,
        "target_first": 60.0,  # 首阶段目标
    },
    
    # 记录
    "created": datetime.now().isoformat(),
    "author": "付郁 (cfeng19791980, 10341731@qq.com)"
}

# 保存配置
with open(r'E:\csi10\v5_evolution_config.json', 'w', encoding='utf-8') as f:
    json.dump(V5_CONFIG, f, ensure_ascii=False, indent=2)

print("=" * 60)
print("v5进化目标配置")
print("=" * 60)

print("\n【进化目标】")
print(f"  目标胜率: >{V5_CONFIG['evolution_target']['win_rate_target']}%")
print(f"  当前胜率: {V5_CONFIG['evolution_target']['current_win_rate']}%")
print(f"  差距: {V5_CONFIG['evolution_target']['gap']}%")

print("\n【里程碑】")
for m in V5_CONFIG['evolution_target']['milestones']:
    print(f"  {m['stage']}: {m['target']}% ({m['priority']})")

print("\n【训练调度】")
for k, v in V5_CONFIG['schedule'].items():
    print(f"  {k}: {v}")

print("\n【优化计划】")
for opt in V5_CONFIG['optimization_plan']:
    print(f"  {opt['id']}: {opt['name']} - 预期{opt['expected_gain']} ({opt['priority']})")

print("\n【首阶段目标】")
print(f"  从{V5_CONFIG['baseline']['v5_current']}%提升到{V5_CONFIG['baseline']['target_first']}%")
print(f"  需提升: {V5_CONFIG['baseline']['target_first'] - V5_CONFIG['baseline']['v5_current']}%")

print("=" * 60)