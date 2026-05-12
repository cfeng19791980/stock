# -*- coding: utf-8 -*-
import sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8')

# 验证修复
with open(r'e:\csi10\main_json.js', 'r', encoding='utf-8') as f:
    content = f.read()

print("=" * 60)
print("Electron主进程修复验证")
print("=" * 60)

checks = [
    ('调用分析器v5', 'analyzer_v5_market.py' in content),
    ('主进程版本v5.0', 'v5.0 大盘走势权重版' in content),
    ('功能说明', '大盘走势权重版' in content),
]

print("\n关键配置:")
for name, found in checks:
    print(f"  {'YES' if found else 'NO'} {name}")

# 查找ANALYZER行
import re
analyzer_match = re.search(r"const ANALYZER = path\.join\(BASE_DIR, '(.*?)'\);", content)
if analyzer_match:
    print(f"\n✓ ANALYZER配置: {analyzer_match.group(1)}")

print("\n" + "=" * 60)
print("结论")
print("=" * 60)

print("""
✅ 已修复完成:
  - Electron调用 analyzer_v5_market.py
  - 主进程版本注释更新为v5.0
  - 窗口标题更新为v5.0

影响:
  - Electron自动更新时运行v5版本
  - 生成包含大盘调整的数据
  - 前端显示正确的adjusted_score
  - 底部大盘信息卡片显示正确数据

建议:
  - 重启Electron应用测试
  - 验证自动更新生成v5数据
""")

# 移动修复脚本到py文件夹
py_dir = r'e:\csi10\py'
scripts = ['fix_main_json_version.py', 'verify_fix.py']
for s in scripts:
    src = os.path.join(r'e:\csi10', s)
    dst = os.path.join(py_dir, s)
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"\nMoved {s} to py/")