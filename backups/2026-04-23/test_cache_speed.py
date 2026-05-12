# -*- coding: utf-8 -*-
"""测量模型缓存效果"""

import subprocess
import time

print("测量analyzer_v4.py运行时间...")
print("="*60)

# 删除缓存测试首次运行时间
import os
import shutil
cache_dir = r'E:\csi10\model_cache'
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)
    print("已删除缓存")

# 首次运行（无缓存）
print("\n首次运行（重新训练）:")
start = time.time()
result = subprocess.run(['python', r'E:\csi10\analyzer_v4.py'], capture_output=True)
first_time = time.time() - start
print(f"耗时: {first_time:.1f}秒")

# 第二次运行（有缓存）
print("\n第二次运行（使用缓存）:")
start = time.time()
result = subprocess.run(['python', r'E:\csi10\analyzer_v4.py'], capture_output=True)
second_time = time.time() - start
print(f"耗时: {second_time:.1f}秒")

print("\n" + "="*60)
print("优化效果:")
print("="*60)
print(f"首次运行: {first_time:.1f}秒")
print(f"缓存运行: {second_time:.1f}秒")
print(f"改进: {(first_time-second_time)/first_time*100:.1f}%")