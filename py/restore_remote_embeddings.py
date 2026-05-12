# -*- coding: utf-8 -*-
"""恢复远程embeddings配置"""
import sys, json, datetime, shutil
sys.stdout.reconfigure(encoding='utf-8')

config_path = r'C:\Users\Administrator\.openclaw\openclaw.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 改用远程embeddings（阿里云百炼）
# 备份
backup_path = config_path + '.backup'
shutil.copy2(config_path, backup_path)

config['agents']['defaults']['memorySearch'] = {
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

# 必须更新meta字段！
config['meta'] = {
    'lastTouchedVersion': '2026.4.15',
    'lastTouchedAt': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
}

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, indent=2, fp=f, ensure_ascii=False)

print("✓ 已恢复远程embeddings配置")
print("  provider: openai (阿里云百炼)")
print("  model: text-embedding-v3")
print("")
print("重启Gateway生效")