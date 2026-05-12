# -*- coding: utf-8 -*-
"""配置OpenClaw使用本地embedding服务"""
import sys, json, datetime, shutil
sys.stdout.reconfigure(encoding='utf-8')

config_path = r'C:\Users\Administrator\.openclaw\openclaw.json'

# 备份
shutil.copy2(config_path, config_path + '.backup')

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 配置本地embedding服务
config['agents']['defaults']['memorySearch'] = {
    "provider": "openai",
    "model": "all-MiniLM-L6-v2",
    "remote": {
        "baseUrl": "http://127.0.0.1:5001/v1",
        "apiKey": "local"
    },
    "store": {
        "vector": {
            "enabled": True
        }
    }
}

# 更新meta
config['meta'] = {
    'lastTouchedVersion': '2026.4.15',
    'lastTouchedAt': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
}

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, indent=2, fp=f, ensure_ascii=False)

print("✓ 已配置本地embedding服务")
print("  Provider: openai (兼容接口)")
print("  Model: all-MiniLM-L6-v2")
print("  Endpoint: http://127.0.0.1:5001/v1")
print("  Dimension: 384")
print("")
print("⚠️ 需要先启动embedding服务:")
print("  python local_embedding_server.py")
print("")
print("然后重启OpenClaw Gateway生效")