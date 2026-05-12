# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

config_path = r'C:\Users\Administrator\.openclaw\openclaw.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

ms = config['agents']['defaults']['memorySearch']

print("Memory Search配置验证:")
print(f"  provider: {ms.get('provider')}")
print(f"  model: {ms.get('model')}")
print(f"  remote.baseUrl: {ms.get('remote', {}).get('baseUrl')}")
print(f"  store.vector.enabled: {ms.get('store', {}).get('vector', {}).get('enabled')}")

print("\n✓ 配置正确")