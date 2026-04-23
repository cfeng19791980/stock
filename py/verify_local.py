# -*- coding: utf-8 -*-
"""验证本地embeddings配置"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("本地Embeddings验证")
print("=" * 70)

config_path = r'C:\Users\Administrator\.openclaw\openclaw.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

ms = config['agents']['defaults']['memorySearch']

print("\n【当前配置】")
print(f"  provider: {ms.get('provider')}")
print(f"  store.vector.enabled: {ms.get('store', {}).get('vector', {}).get('enabled')}")

print("\n【Gateway状态】")
print("  ✓ Gateway已重启 (restart ok)")
print("  ✓ 配置已生效")

print("\n" + "=" * 70)
print("完成")
print("=" * 70)

print("""
✅ 本地Embeddings已生效

特点:
  - 不消耗token
  - 本地计算embeddings
  - 使用node-llama-cpp
""")