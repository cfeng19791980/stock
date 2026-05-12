# -*- coding: utf-8 -*-
"""更新配置为本地embeddings"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("本地Embeddings配置")
print("=" * 70)

config_path = r'C:\Users\Administrator\.openclaw\openclaw.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 改回本地
new_config = {
    "provider": "local",
    "store": {
        "vector": {
            "enabled": True
        }
    }
}

config['agents']['defaults']['memorySearch'] = new_config

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, indent=2, fp=f, ensure_ascii=False)

print("\n✓ 配置已更新:")
print(f"  provider: local")
print(f"  store.vector.enabled: True")

print("\n" + "=" * 70)
print("完成")
print("=" * 70)

print("""
✅ node-llama-cpp已安装
✅ 配置已改为local

生效方式:
  openclaw restart
""")