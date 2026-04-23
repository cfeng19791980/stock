# -*- coding: utf-8 -*-
"""改用本地embeddings"""
import sys, json, subprocess
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("本地Embeddings配置")
print("=" * 70)

# 检查Node版本
result = subprocess.run(['node', '--version'], capture_output=True, text=True)
node_version = result.stdout.strip()
print(f"\n当前Node版本: {node_version}")

# 检查是否满足要求
if node_version.startswith('v22'):
    print("✓ Node 22 LTS，支持node-llama-cpp")
elif node_version.startswith('v24'):
    print("✓ Node 24，推荐版本")
else:
    print("⚠️ 建议升级到Node 22 LTS或Node 24")

print("\n【安装node-llama-cpp】")

# 安装node-llama-cpp
print("执行: npm install node-llama-cpp")
result = subprocess.run(
    ['npm', 'install', '-g', 'node-llama-cpp'],
    capture_output=True,
    text=True,
    cwd=r'C:\Users\Administrator\AppData\Roaming\npm'
)

if result.returncode == 0:
    print("✓ 安装成功")
else:
    print(f"安装输出: {result.stdout}")
    print(f"安装错误: {result.stderr}")

print("\n【更新配置为local】")

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

print("✓ 配置已改为provider: local")

print("\n" + "=" * 70)
print("完成")
print("=" * 70)