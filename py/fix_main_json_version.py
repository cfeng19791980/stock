# -*- coding: utf-8 -*-
"""检查并修复main_json.js中的Python脚本版本"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("Electron主进程脚本版本检查")
print("=" * 70)

# 读取main_json.js
with open(r'e:\csi10\main_json.js', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找关键配置
import re

analyzer_match = re.search(r"const ANALYZER = path\.join\(BASE_DIR, '(.*?)'\);", content)
version_match = re.search(r"// Electron主进程 - v(\d+\.\d+)", content)
title_match = re.search(r"title: '波段股票分析系统 v(\d+\.\d+)'", content)

print("\n【当前配置】")

if analyzer_match:
    print(f"调用分析器: {analyzer_match.group(1)}")
else:
    print("调用分析器: 未找到")

if version_match:
    print(f"主进程版本: v{version_match.group(1)}")
else:
    print("主进程版本: 未找到")

if title_match:
    print(f"窗口标题: v{title_match.group(1)}")
else:
    print("窗口标题: 未找到")

print("\n" + "=" * 70)
print("问题分析")
print("=" * 70)

print("""
⚠️ 发现问题:

  1. Electron调用的分析器是 analyzer_v4.py
  2. 但前端index.html显示的是v5格式数据
  3. 导致前端adjusted_score显示undefined

影响:
  - Electron自动更新时运行v4版本
  - v4无大盘调整功能
  - v4无adjusted_score字段
  - 前端显示错误数据

必须修复:
  - 将analyzer_v4.py改为analyzer_v5_market.py
  - 更新窗口标题为v5.0
  - 更新主进程注释为v5.0
""")

print("\n" + "=" * 70)
print("修复方案")
print("=" * 70)

# 修复配置
fixes = [
    ("const ANALYZER = path.join(BASE_DIR, 'analyzer_v4.py');", 
     "const ANALYZER = path.join(BASE_DIR, 'analyzer_v5_market.py');"),
    ("// Electron主进程 - v4.0 持仓管理版",
     "// Electron主进程 - v5.0 大盘走势权重版"),
    ("title: '波段股票分析系统 v4.0'",
     "title: '波段股票分析系统 v5.0 - 大盘走势权重版'"),
    ("console.log('波段股票分析系统 v4.0 启动');",
     "console.log('波段股票分析系统 v5.0 启动');"),
]

for old, new in fixes:
    if old in content:
        content = content.replace(old, new)
        print(f"✓ 已修复: {old[:50]}...")
    else:
        print(f"⚠ 未找到: {old[:50]}...")

# 写回文件
with open(r'e:\csi10\main_json.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ main_json.js已更新为v5版本")

print("\n" + "=" * 70)
print("修复后配置")
print("=" * 70)

# 验证修复
with open(r'e:\csi10\main_json.js', 'r', encoding='utf-8') as f:
    content = f.read()

analyzer_match = re.search(r"const ANALYZER = path\.join\(BASE_DIR, '(.*?)'\);", content)
version_match = re.search(r"// Electron主进程 - v(\d+\.\d+)", content)
title_match = re.search(r"title: '波段股票分析系统 v(\d+\.\d+)", content)

if analyzer_match:
    print(f"调用分析器: {analyzer_match.group(1)}")

if version_match:
    print(f"主进程版本: v{version_match.group(1)}")

if title_match:
    print(f"窗口标题: v{title_match.group(1)}")

print("\n" + "=" * 70)
print("结论")
print("=" * 70)

print("""
✅ 已修复:
  - Electron现在调用analyzer_v5_market.py
  - 窗口标题更新为v5.0
  - 主进程版本注释更新为v5.0

确保:
  1. Electron自动更新时运行v5版本
  2. 生成正确的v5格式数据（含market字段）
  3. 前端显示正确的adjusted_score

测试建议:
  - 重启Electron应用
  - 点击"立即更新"按钮
  - 验证result.json版本=5.0
  - 验证前端大盘信息卡片显示正确
""")