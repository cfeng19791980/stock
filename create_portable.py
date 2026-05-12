# -*- coding: utf-8 -*-
"""
创建便携版CSI10 - 嵌入Python环境
方案：使用Python embed版 + 依赖包
"""

import os
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(r"E:\csi10")
PORTABLE_DIR = BASE_DIR / "portable_package"
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"

print("="*60)
print("创建CSI10便携版 - 嵌入Python")
print("="*60)

# 创建便携目录
if PORTABLE_DIR.exists():
    shutil.rmtree(PORTABLE_DIR)
PORTABLE_DIR.mkdir()

print(f"\n[Step 1] 下载Python embed版...")
python_zip = PORTABLE_DIR / "python_embed.zip"

# 使用curl下载
import urllib.request
try:
    urllib.request.urlretrieve(PYTHON_EMBED_URL, python_zip)
    print(f"  下载完成: {python_zip.stat().st_size / 1024:.0f}KB")
except Exception as e:
    print(f"  下载失败: {e}")
    print("  使用本地Python复制依赖...")

# 解压Python embed
import zipfile
if python_zip.exists():
    python_dir = PORTABLE_DIR / "python"
    python_dir.mkdir()
    with zipfile.ZipFile(python_zip, 'r') as zip_ref:
        zip_ref.extractall(python_dir)
    print(f"  解压完成: {python_dir}")
    python_zip.unlink()

print(f"\n[Step 2] 复制项目文件...")

# 复制核心文件
files_to_copy = [
    "analyzer_v4.py",
    "data_fetcher.py",
    "market_index_fetcher.py",
    "main_json.js",
    "index.html",
    "preload.js",
    "package.json",
    "stocks.db",
    "波段股票Top30.csv",
    "holdings.json",
    "result.json",
]

app_dir = PORTABLE_DIR / "app"
app_dir.mkdir()

for f in files_to_copy:
    src = BASE_DIR / f
    dst = app_dir / f
    if src.exists():
        shutil.copy2(src, dst)
        print(f"  {f}")
    else:
        print(f"  {f}: 不存在，跳过")

print(f"\n[Step 3] 复制Node模块...")
# 复制node_modules关键文件
nm_src = BASE_DIR / "node_modules"
nm_dst = app_dir / "node_modules"
if nm_src.exists():
    # 只复制electron核心
    electron_src = nm_src / "electron"
    electron_dst = nm_dst / "electron"
    if electron_src.exists():
        shutil.copytree(electron_src, electron_dst, ignore=shutil.ignore_patterns('*.pdb', '*.obj'))
        print(f"  electron模块已复制")

print(f"\n[Step 4] 创建启动脚本...")

# 创建启动脚本
launcher = PORTABLE_DIR / "启动便携版.bat"
launcher.write_text("""@echo off
chcp 65001 >nul
echo 波段股票分析系统 v4.0 便携版
echo.
echo 正在启动...
cd /d "%~dp0app"
"..\python\python.exe" -m pip install pandas numpy xgboost akshare requests --quiet 2>nul
"..\python\python.exe" data_fetcher.py
"..\python\python.exe" analyzer_v4.py
"..\node_modules\electron\dist\electron.exe" main_json.js
pause
""", encoding='utf-8')

print(f"  启动脚本已创建: {launcher}")

print(f"\n[Step 5] 生成便携exe...")

# 使用7zip或bat2exe创建单exe（可选）
# 这里先创建便携文件夹

print(f"\n便携版目录: {PORTABLE_DIR}")
print(f"\n内容:")
total_size = 0
for f in PORTABLE_DIR.rglob("*"):
    if f.is_file():
        size = f.stat().st_size
        total_size += size
        rel = f.relative_to(PORTABLE_DIR)
        if size > 1024*1024:
            print(f"  {rel}: {size/(1024*1024):.1f}MB")

print(f"\n总大小: {total_size/(1024*1024):.1f}MB")

print("\n" + "="*60)
print("便携版创建完成")
print("="*60)
print("\n使用方法:")
print("  1. 复制 portable_package 到目标电脑")
print("  2. 运行 启动便携版.bat")