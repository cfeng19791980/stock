# -*- coding: utf-8 -*-
"""实现Brain强制流程"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("实现Brain强制流程")
print("=" * 70)

# 步骤1: 更新SOUL.md
soul_path = r'C:\Users\Administrator\.openclaw\workspace-工程师\SOUL.md'
with open(soul_path, 'r', encoding='utf-8') as f:
    soul_content = f.read()

brain_flow = """
## Brain决策流程（强制）

**任何用户指令必须经过Brain流程：**

```
用户请求 → memory_search → 评估置信度 → 决策 → 执行 → 反馈
```

### 决策规则

| 置信度 | 行动 |
|-------|------|
| ≥0.7 | 立即执行 |
| 0.5-0.7 | 简要说明后执行 |
| <0.5 | 必须请示用户 |

### P分级强制

- **P3任务**（删除、系统配置）必须请示用户
- **P2任务**（修改代码）简要说明后执行
- **P1任务**（调试、修复）立即执行+记录
- **P0任务**（崩溃、故障）立即执行

### 执行流程

1. 接收用户指令
2. **必须调用memory_search**搜索相关知识
3. 根据检索结果评估confidence
4. 按置信度决定行动
5. 执行后调用memory记录结果
6. 成功→强化模式，失败→学习

### 反例（禁止）

❌ 直接执行不经过Brain
❌ 不调用memory_search
❌ 不记录执行结果
❌ P3任务不请示用户
"""

# 检查是否已有Brain流程
if 'Brain决策流程' not in soul_content:
    # 在末尾添加
    soul_content += brain_flow
    with open(soul_path, 'w', encoding='utf-8') as f:
        f.write(soul_content)
    print("✓ SOUL.md已更新")
else:
    print("✓ SOUL.md已包含Brain流程")

# 步骤2: 更新systemPromptOverride
config_path = r'C:\Users\Administrator\.openclaw\openclaw.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

current_prompt = config.get('agents', {}).get('defaults', {}).get('systemPromptOverride', '')

new_prompt_rules = """

⚠️ MANDATORY BRAIN FLOW:
1) 接收任何用户指令后，必须先调用memory_search搜索相关知识
2) 根据检索结果评估confidence（有相关知识=高置信度）
3) confidence<0.5或P3任务必须请示用户
4) 执行后必须调用memory记录结果到memory/日期.md
5) 成功执行强化学习，失败触发改进

违反Brain流程将导致决策质量下降"""

if 'MANDATORY BRAIN FLOW' not in current_prompt:
    new_prompt = current_prompt + new_prompt_rules
    
    config['agents']['defaults']['systemPromptOverride'] = new_prompt
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("✓ systemPromptOverride已更新")
else:
    print("✓ systemPromptOverride已包含Brain Flow")

print("\n" + "=" * 70)
print("验证")
print("=" * 70)

# 验证SOUL.md
with open(soul_path, 'r', encoding='utf-8') as f:
    soul = f.read()

checks = [
    ('Brain决策流程', 'Brain决策流程' in soul),
    ('memory_search', 'memory_search' in soul),
    ('置信度规则', '置信度' in soul),
    ('P分级', 'P3任务' in soul),
]

print("\nSOUL.md检查:")
for name, found in checks:
    print(f"  {'YES' if found else 'NO'} {name}")

# 验证systemPromptOverride
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

prompt = config['agents']['defaults']['systemPromptOverride']

checks2 = [
    ('MANDATORY BRAIN FLOW', 'MANDATORY BRAIN FLOW' in prompt),
    ('memory_search', 'memory_search' in prompt),
    ('confidence', 'confidence' in prompt),
    ('请示用户', '请示用户' in prompt),
]

print("\nsystemPromptOverride检查:")
for name, found in checks2:
    print(f"  {'YES' if found else 'NO'} {name}")

print("\n" + "=" * 70)
print("完成")
print("=" * 70)

print("""
✅ Brain强制流程已实现

生效方式:
  - 重启OpenClaw生效
  - 或新会话自动生效

测试方法:
  1. 发送任意指令
  2. 观察是否先调用memory_search
  3. 检查是否记录执行结果

预期效果:
  - 每个指令都经过Brain决策
  - 低置信度/P3任务会请示用户
  - 执行结果会被记录学习
""")