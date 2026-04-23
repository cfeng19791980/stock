# -*- coding: utf-8 -*-
"""继续整理并创建Electron运行指南"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import shutil

base = r'e:\csi10'
py_dir = os.path.join(base, 'py')

# 继续移动非核心文件
extra_files = [
    'cleanup_folder.py',
    '大盘走势权重方案.py',
    'INTEGRATION-REPORT.md',
    'VERSION-GUIDE.md',
    'full_backtest_result.json',
    'market_backtest_result.json',
    'market_segment_test.json',
    'quick_backtest.json',
]

moved = 0
for f in extra_files:
    src = os.path.join(base, f)
    dst = os.path.join(py_dir, f)
    
    if os.path.exists(src):
        shutil.move(src, dst)
        moved += 1
        print(f"✓ 移动: {f}")

print(f"\n移动 {moved} 个额外文件")

# 创建Electron运行指南
guide = """# -*- coding: utf-8 -*-
"""
波段股票分析系统 - Electron运行环境指南
========================================

⚠️ 核心原则: 程序运行在Electron环境中，必须保证Python脚本版本正确

一、Electron架构
----------------
┌─────────────────────────────────────────────┐
│          Electron应用架构                    │
├─────────────────────────────────────────────┤
│                                             │
│   index.html (前端界面)                     │
│        ↓                                    │
│   preload.js (桥接层)                       │
│        ↓                                    │
│   main.js / main_json.js (主进程)           │
│        ↓                                    │
│   Python脚本调用                            │
│        ↓                                    │
│   result.json → 前端显示                    │
│                                             │
└─────────────────────────────────────────────┘

二、核心Python脚本（必须保持正确）
---------------------------------
✓ analyzer_v5_market.py
  - 位置: e:\\csi10\\analyzer_v5_market.py
  - 功能: 主分析引擎（v5.0大盘权重版）
  - 调用: Electron主进程调用
  - 输出: result.json

✓ data_fetcher.py
  - 位置: e:\\csi10\\data_fetcher.py
  - 功能: 实时数据获取
  - 调用: 按需调用（实时刷新）

✓ market_index_fetcher.py
  - 位置: e:\\csi10\\market_index_fetcher.py
  - 功能: 大盘指数数据获取
  - 调用: 每日收盘后调用

三、更新优化流程（严格遵守）
---------------------------
每次更新必须:

1. ✅ 更新核心Python脚本
   - analyzer_v5_market.py
   - 保持数据库路径正确
   
2. ✅ 测试Python脚本独立运行
   python analyzer_v5_market.py
   - 确保能独立正确执行
   
3. ✅ 验证输出result.json
   - 检查version字段=5.0
   - 检查market字段存在
   - 检查adjusted_score存在
   
4. ✅ 测试Electron完整流程
   - 运行Electron应用
   - 验证前端显示正确
   
5. ✅ 保持前端index.html兼容
   - 添加容错逻辑
   - 不破坏现有功能

四、禁止事项
-----------
❌ 不要随意更改数据库路径
❌ 不要删除核心Python脚本
❌ 不要改变result.json结构（破坏前端）
❌ 不要在核心脚本中使用相对路径
❌ 不要忘记更新版本号

五、文件位置规则
---------------
根目录（e:\\csi10\\）:
  ✓ 只保留核心文件
  ✓ analyzer_v5_market.py
  ✓ data_fetcher.py  
  ✓ market_index_fetcher.py
  ✓ index.html
  ✓ result.json
  ✓ holdings.json

py文件夹（e:\\csi10\\py\\）:
  ✓ 测试脚本
  ✓ 回测脚本
  ✓ 临时脚本
  ✓ 开发调试脚本

六、更新示例
-----------
正确更新流程:

# 1. 开发新功能
python e:\\csi10\\py\\test_new_feature.py

# 2. 测试通过后集成到核心脚本
更新 analyzer_v5_market.py

# 3. 独立测试核心脚本
python e:\\csi10\\analyzer_v5_market.py

# 4. 验证输出
检查 result.json 结构

# 5. 测试Electron
运行Electron应用验证

# 6. 提交更新
记录版本号和更新内容

七、版本号规则
-------------
v5.0: 大盘走势权重版
v5.1: 下一次更新版本
v6.0: 重大架构变更

每次更新必须更新version字段

八、检查清单
-----------
每次提交前检查:

□ 核心脚本位置正确（根目录）
□ 数据库路径绝对路径
□ result.json结构完整
□ version字段更新
□ 前端容错逻辑添加
□ Electron测试通过
□ py文件夹整理（非核心文件）

九、联系方式
-----------
问题反馈: 记录在py\\README.md
版本历史: 记录在VERSION-GUIDE.md
"""

guide_path = os.path.join(base, 'ELECTRON-RUN-GUIDE.md')
with open(guide_path, 'w', encoding='utf-8') as f:
    f.write(guide)

print(f"\n✓ 创建: {guide_path}")

# 最终文件列表
print("\n" + "=" * 60)
print("最终根目录文件")
print("=" * 60)

for f in sorted(os.listdir(base)):
    if os.path.isfile(os.path.join(base, f)):
        print(f"  {f}")

print("\n" + "=" * 60)
print("核心文件确认")
print("=" * 60)

core_check = [
    ('analyzer_v5_market.py', os.path.exists(os.path.join(base, 'analyzer_v5_market.py'))),
    ('data_fetcher.py', os.path.exists(os.path.join(base, 'data_fetcher.py'))),
    ('market_index_fetcher.py', os.path.exists(os.path.join(base, 'market_index_fetcher.py'))),
    ('index.html', os.path.exists(os.path.join(base, 'index.html'))),
    ('result.json', os.path.exists(os.path.join(base, 'result.json'))),
    ('holdings.json', os.path.exists(os.path.join(base, 'holdings.json'))),
    ('波段股票Top30.csv', os.path.exists(os.path.join(base, '波段股票Top30.csv'))),
]

for name, exists in core_check:
    print(f"  {'✓' if exists else '❌'} {name}")

print("\n✅ 所有核心文件已确认")