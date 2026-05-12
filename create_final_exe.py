# -*- coding: utf-8 -*-
"""
创建真正的单exe - 使用7-Zip自解压
"""

import os
import shutil
import subprocess
from pathlib import Path

PORTABLE_DIR = Path(r"E:\csi10\portable_package")
FINAL_EXE = Path(r"E:\csi10\波段股票分析v4完整版.exe")

print("="*60)
print("创建自解压单exe")
print("="*60)

# 检查7-Zip
seven_zip = Path(r"C:\Program Files\7-Zip\7z.exe")
if not seven_zip.exists():
    seven_zip = Path(r"C:\Program Files (x86)\7-Zip\7z.exe")

if not seven_zip.exists():
    print("7-Zip未找到，尝试下载...")
    # 使用系统zip
    print("使用替代方案：复制便携文件夹")
else:
    print(f"7-Zip: {seven_zip}")

# 创建自解压配置
sfx_config = PORTABLE_DIR / "sfx_config.txt"
sfx_config.write_text("""
;!@Install@!UTF-8
Title="波段股票分析系统 v4.0"
BeginPrompt="是否安装波段股票分析系统？"
ExtractTitle="正在解压..."
ExtractDialogText="请稍候，正在解压文件..."
ExtractPathText="解压路径"
Progress="yes"
GUIMode="auto"
OverwriteMode="auto"
InstallPath="E:\\波段股票分析v4"
RunProgram="hidcon:cmd /c start 启动便携版.bat"
;!@InstallEnd@!
""", encoding='utf-8')

print(f"\n[Step 1] 创建自解压包...")

if seven_zip.exists():
    # 使用7-Zip创建自解压
    cmd = [
        str(seven_zip),
        "a",
        "-sfx7z.sfx",
        str(FINAL_EXE),
        str(PORTABLE_DIR / "*")
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"  成功: {FINAL_EXE}")
        print(f"  大小: {FINAL_EXE.stat().st_size / (1024*1024):.1f}MB")
    else:
        print(f"  失败: {result.stderr}")
else:
    # 无7-Zip，使用PowerShell压缩
    print("  使用PowerShell创建zip...")
    zip_file = Path(r"E:\csi10\波段股票分析v4便携版.zip")
    
    ps_cmd = f"""
    Compress-Archive -Path '{PORTABLE_DIR}\\*' -DestinationPath '{zip_file}' -Force
    """
    
    result = subprocess.run(
        ["powershell", "-Command", ps_cmd],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        print(f"  成功: {zip_file}")
        print(f"  大小: {zip_file.stat().st_size / (1024*1024):.1f}MB")
        
        # 创建解压说明
        readme = Path(r"E:\csi10\使用说明.txt")
        readme.write_text("""
波段股票分析系统 v4.0 便携版使用说明
==========================================

文件：波段股票分析v4便携版.zip

使用方法：
1. 解压到任意目录（如 E:\\波段股票分析v4）
2. 运行 "启动便携版.bat"
3. 首次运行会自动安装Python依赖（需要网络）

包含内容：
- Python 3.11 嵌入版
- Electron界面
- 股票数据库 stocks.db
- 分析模块 analyzer_v4.py

大小：约524MB（解压后）
==========================================
""", encoding='utf-8')
        print(f"  使用说明: {readme}")

print("\n" + "="*60)
print("完成")
print("="*60)

# 列出最终文件
print("\n生成的文件:")
for f in Path(r"E:\csi10").glob("波段股票*"):
    if f.is_file():
        print(f"  {f.name}: {f.stat().st_size/(1024*1024):.1f}MB")