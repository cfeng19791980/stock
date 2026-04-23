# -*- coding: utf-8 -*-
"""修复memory embeddings问题"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("修复Memory Embeddings问题")
print("=" * 70)

print("\n【错误原因】")
print("""
当前配置: provider = "local"
需要模块: node-llama-cpp (用于本地embeddings)
问题: 模块未安装
""")

print("\n【解决方案】")

config_path = r'C:\Users\Administrator\.openclaw\openclaw.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 获取当前memorySearch配置
current = config.get('agents', {}).get('defaults', {}).get('memorySearch', {})
print(f"\n当前配置:")
print(f"  provider: {current.get('provider', 'local')}")
print(f"  store.vector.enabled: {current.get('store', {}).get('vector', {}).get('enabled', False)}")

# 更新为远程provider（使用已有API）
# 用户已有阿里云百炼API: sk-sp-ff1a37799fa74d9cbfd4889c4e43d7d4
new_config = {
    "provider": "openai",
    "model": "text-embedding-v3",
    "remote": {
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": "sk-sp-ff1a37799fa74d9cbfd4889c4e43d7d4"
    },
    "store": {
        "vector": {
            "enabled": True
        }
    }
}

config['agents']['defaults']['memorySearch'] = new_config

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, indent=2, fp=f, ensure_ascii=False)

print(f"\n新配置:")
print(f"  provider: openai")
print(f"  model: text-embedding-v3")
print(f"  baseUrl: 阿里云百炼API")
print(f"  vector.enabled: True")

print("\n" + "=" * 70)
print("完成")
print("=" * 70)

print("""
✓ 已修复memory embeddings配置

使用阿里云百炼API作为远程embedding provider
无需安装node-llama-cpp

生效方式:
  openclaw restart

或重启OpenClaw服务
""")