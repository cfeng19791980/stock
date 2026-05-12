# -*- coding: utf-8 -*-
"""检查skills和hooks结构"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("Brain系统集成方案设计")
print("=" * 70)

# 检查skills目录
skills_dir = r'C:\Users\Administrator\.openclaw\workspace-工程师\skills'
if os.path.exists(skills_dir):
    print("\n【Skills目录】")
    for item in os.listdir(skills_dir):
        print(f"  {item}")
else:
    print("\nSkills目录不存在")

# 检查现有hooks配置
config_path = r'C:\Users\Administrator\.openclaw\openclaw.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

print("\n【现有Hooks】")
hooks = config.get('hooks', {}).get('internal', {}).get('entries', {})
for name, cfg in hooks.items():
    enabled = cfg.get('enabled', True)
    print(f"  {'ON' if enabled else 'OFF'} {name}")

print("\n【现有Skills】")
skills = config.get('skills', {}).get('entries', {})
for name, cfg in skills.items():
    enabled = cfg.get('enabled', True)
    print(f"  {'ON' if enabled else 'OFF'} {name}")

print("\n【systemPromptOverride】")
prompt = config.get('agents', {}).get('defaults', {}).get('systemPromptOverride', '')
print(f"  已包含: {'brain系统' in prompt}")

print("\n" + "=" * 70)
print("实现方案")
print("=" * 70)

print("""
目标: 任何指令都能触发brain系统工作

方案A: Hook机制（推荐）
  - 创建brain-hook插件
  - 在请求入口处拦截
  - 自动调用brain.decide()
  - 根据置信度决定执行或请示

方案B: Skill机制
  - 创建brain-router skill
  - 模型调用skill时自动触发Brain

方案C: 系统提示强化
  - 在systemPromptOverride中添加强制Brain调用规则
  - 每次回复前必须调用Brain
""")

print("\n" + "=" * 70)
print("方案A实现步骤（Hook机制）")
print("=" * 70)

print("""
步骤1: 创建brain-hook.js插件
  位置: ~/.openclaw/extensions/brain-hook/
  
  功能:
    - 监听每个用户请求
    - 调用brain_api_server.py
    - 返回决策结果给模型
    - 记录执行结果触发反馈

步骤2: 配置hooks
  在openclaw.json中添加:
  {
    "hooks": {
      "internal": {
        "entries": {
          "brain-router": {
            "enabled": true,
            "priority": "high"
          }
        }
      }
    }
  }

步骤3: 启动Brain API服务
  python brain_api_server.py --port 5000
  
  API:
    POST /decide
    Body: {"query": "用户指令"}
    Response: {"decision": "...", "confidence": 0.8}
""")

print("\n" + "=" * 70)
print("简化方案（立即可用）")
print("=" * 70)

print("""
最快实现方式:

1. 更新systemPromptOverride添加强制规则:
   ```
   ⚠️ MANDATORY BRAIN FLOW:
   1. 接收任何用户指令后，必须先调用memory_search搜索相关知识
   2. 根据检索结果评估confidence
   3. confidence<0.5时请示用户
   4. 执行后记录结果到memory
   ```

2. 在SOUL.md中添加Brain强制流程:
   ```
   ## Brain决策流程（强制）
   
   用户请求 → memory_search → 评估置信度 → 决策 → 执行 → 反馈
   
   P3任务必须:
   - confidence < 0.5 → 请示用户
   - 涉及删除/修改 → 请示用户
   ```

3. 模型每次回复会自动遵守这些规则

优点:
  - 无需创建新插件
  - 立即可用
  - 已有memory_search工具
  
缺点:
  - 依赖模型自觉遵守
  - 无强制拦截机制
""")

print("\n是否立即实现简化方案？")