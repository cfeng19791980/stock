# -*- coding: utf-8 -*-
"""
PyInstaller打包脚本 - csi10项目Python模块
打包所有Python文件为独立exe
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

BASE_DIR = Path(r"E:\csi10")
DIST_DIR = BASE_DIR / "py_dist"

print("="*60)
print("PyInstaller打包 - 波段股票分析Python模块")
print("="*60)

# Python文件列表
PYTHON_FILES = [
    "analyzer_v4.py",
    "data_fetcher.py",
    "market_index_fetcher.py",
]

# 数据文件
DATA_FILES = [
    "stocks.db",
    "波段股票Top30.csv",
    "holdings.json",
    "result.json",
]

# 创建输出目录
if DIST_DIR.exists():
    shutil.rmtree(DIST_DIR)
DIST_DIR.mkdir()

print(f"\n[Step 1] 检查依赖...")
dependencies = [
    "pandas", "numpy", "xgboost", "akshare", 
    "sqlite3", "requests", "datetime"
]

for dep in dependencies:
    try:
        __import__(dep if dep != "sqlite3" else "sqlite3")
        print(f"  {dep}: OK")
    except ImportError:
        print(f"  {dep}: MISSING - 需要安装")

print(f"\n[Step 2] 打包Python文件...")

for py_file in PYTHON_FILES:
    src = BASE_DIR / py_file
    
    if not src.exists():
        print(f"  {py_file}: 文件不存在，跳过")
        continue
    
    print(f"\n  打包: {py_file}")
    
    # PyInstaller命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # 单文件
        "--console",  # 控制台应用
        "--clean",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BASE_DIR / "build_temp"),
        "--specpath", str(BASE_DIR),
        
        # 添加数据文件
        "--add-data", f"{BASE_DIR / 'stocks.db'};.",
        "--add-data", f"{BASE_DIR / '波段股票Top30.csv'};.",
        
        # 隐藏导入
        "--hidden-import", "pandas",
        "--hidden-import", "numpy",
        "--hidden-import", "xgboost",
        "--hidden-import", "akshare",
        "--hidden-import", "requests",
        "--hidden-import", "sqlite3",
        "--hidden-import", "json",
        "--hidden-import", "datetime",
        
        str(src)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        exe_name = py_file.replace(".py", ".exe")
        exe_path = DIST_DIR / exe_name
        if exe_path.exists():
            print(f"    成功: {exe_name} ({exe_path.stat().st_size / 1024:.0f}KB)")
        else:
            print(f"    失败: exe未生成")
    else:
        print(f"    错误: {result.stderr[:200]}")

# 清理临时文件
build_temp = BASE_DIR / "build_temp"
if build_temp.exists():
    shutil.rmtree(build_temp)

for spec in BASE_DIR.glob("*.spec"):
    spec.unlink()

print(f"\n[Step 3] 复制数据文件...")
for data_file in DATA_FILES:
    src = BASE_DIR / data_file
    dst = DIST_DIR / data_file
    if src.exists():
        shutil.copy(src, dst)
        print(f"  {data_file}: 已复制")

print(f"\n[Step 4] 生成结果...")
print(f"\n输出目录: {DIST_DIR}")
print(f"\n生成的exe文件:")

for f in DIST_DIR.glob("*.exe"):
    size_mb = f.stat().st_size / (1024*1024)
    print(f"  {f.name}: {size_mb:.2f}MB")

print("\n" + "="*60)
print("打包完成")
print("="*60)