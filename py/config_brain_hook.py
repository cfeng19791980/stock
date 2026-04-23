# -*- coding: utf-8 -*-
"""配置启用Brain Hook插件"""
import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("配置Brain Hook插件")
print("=" * 70)

config_path = r'C:\Users\Administrator\.openclaw\openclaw.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 添加brain-hook到plugins
if 'brain-hook' not in config.get('plugins', {}).get('allow', []):
    config['plugins']['allow'].append('brain-hook')
    print("✓ 添加brain-hook到plugins.allow")

# 添加Hook配置
if 'hooks' not in config:
    config['hooks'] = {}

if 'external' not in config['hooks']:
    config['hooks']['external'] = {}

if 'entries' not in config['hooks']['external']:
    config['hooks']['external']['entries'] = {}

config['hooks']['external']['entries']['brain-hook'] = {
    "enabled": True,
    "priority": "high",
    "path": r'C:\Users\Administrator\.openclaw\extensions\brain-hook'
}
print("✓ 配置hooks.external.entries.brain-hook")

# 添加插件安装记录
if 'installs' not in config['plugins']:
    config['plugins']['installs'] = {}

config['plugins']['installs']['brain-hook'] = {
    "source": "path",
    "spec": "brain-hook",
    "installPath": r'C:\Users\Administrator\.openclaw\extensions\brain-hook',
    "installedAt": "2026-04-20T13:47:00.000Z"
}
print("✓ 添加installs记录")

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, indent=2, fp=f, ensure_ascii=False)

print("\n" + "=" * 70)
print("完成")
print("=" * 70)

print("""
✅ Brain Hook插件已配置

生效步骤:
  1. 启动Brain API服务器: python brain_api_server.py --port 5000
  2. 重启OpenClaw
  3. 测试Hook拦截

架构:
  用户请求 → Brain Hook拦截 → Brain API决策 → 执行 → 反馈
""")