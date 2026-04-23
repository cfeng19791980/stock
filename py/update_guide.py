# -*- coding: utf-8 -*-
"""
更新Electron运行指南 - 记录最佳实践
"""
import sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("最佳实践更新")
print("=" * 70)

print("\n用户建议:")
print("""
下次更新策略（更好的方案）:

1. 备份原文件到py文件夹
   analyzer_v4.py → py/analyzer_v4_backup_20260420.py

2. 直接在原文件内修改
   analyzer_v4.py 内部更新为v5内容
   保持文件名不变

3. 关联文件无需修改
   main_json.js 仍调用 analyzer_v4.py
   文件名不变，引用不变

优点:
  ✅ 不需要修改关联文件
  ✅ 减少维护成本
  ✅ 降低出错风险
  ✅ 保持Electron配置稳定
""")

# 更新ELECTRON-RUN-GUIDE.md
guide_path = r'e:\csi10\ELECTRON-RUN-GUIDE.md'

new_content = """# 波段股票分析系统 - Electron运行环境指南

## 核心原则
程序运行在Electron环境中，必须保证Python脚本版本正确

---

## 一、Electron架构

```
index.html (前端界面)
     ↓
preload.js (桥接层)
     ↓
main_json.js (主进程)
     ↓
Python脚本调用
     ↓
result.json → 前端显示
```

---

## 二、核心Python脚本（必须保持正确）

| 脚本 | 位置 | 功能 | 输出 |
|-----|------|------|------|
| **analyzer_v4.py** | 根目录 | 主分析引擎 | result.json |
| **data_fetcher.py** | 根目录 | 实时数据获取 | 更新数据库 |
| **market_index_fetcher.py** | 根目录 | 大盘数据获取 | index_daily表 |

---

## 三、更新优化最佳实践（严格遵守）

### ⭐ 最佳策略：在原文件内修改

**下次更新流程：**

1. **备份原文件**
   ```bash
   # 备份到py文件夹
   analyzer_v4.py → py/analyzer_v4_backup_YYYYMMDD.py
   ```

2. **直接在原文件修改**
   ```bash
   # 保持文件名不变
   analyzer_v4.py 内部更新为新版本内容
   ```

3. **关联文件无需修改**
   ```bash
   # main_json.js 仍调用 analyzer_v4.py
   # 文件名不变，引用不变
   ```

**优点：**
- ✅ 不需要修改关联文件
- ✅ 减少维护成本
- ✅ 降低出错风险
- ✅ 保持Electron配置稳定

---

### 禁止事项

- ❌ 不要创建新文件名（如analyzer_v5.py）
- ❌ 不要随意更改数据库路径
- ❌ 不要改变result.json结构
- ❌ 不要在核心脚本中使用相对路径

---

## 四、文件位置规则

**根目录（e:\csi10\）**:
```
analyzer_v4.py         ★核心（文件名不变）
data_fetcher.py        ★核心
market_index_fetcher.py ★核心
index.html             ★前端
result.json            ★输出
holdings.json          ★持仓
波段股票Top30.csv       ★股票池
```

**py文件夹（e:\csi10\py\）**:
```
analyzer_v4_backup_YYYYMMDD.py  （备份）
测试脚本
回测脚本
临时脚本
```

---

## 五、检查清单

每次提交前检查：

- [ ] 备份原文件到py文件夹
- [ ] 在原文件内修改（保持文件名不变）
- [ ] 数据库路径使用绝对路径
- [ ] result.json结构完整
- [ ] version字段已更新
- [ ] 前端容错逻辑添加
- [ ] Electron测试通过

---

## 六、版本号规则

- 在文件内部更新version字段
- 文件名保持不变（analyzer_v4.py）
- 备份文件带日期后缀（py/analyzer_v4_backup_20260420.py）

每次更新必须在result.json中更新version字段

---

**重要**: 
1. 核心文件永远在根目录
2. 文件名保持不变
3. 备份文件放入py文件夹
4. 所有测试脚本放入py文件夹"""

with open(guide_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("\n✓ 已更新: ELECTRON-RUN-GUIDE.md")

print("\n" + "=" * 70)
print("当前状态")
print("=" * 70)

print("""
当前配置（已正确）:
  - main_json.js → analyzer_v5_market.py
  - 已完成v5升级
  - 前端显示正确

下次更新策略:
  - 备份 analyzer_v5_market.py → py/analyzer_v5_backup_YYYYMMDD.py
  - 直接在 analyzer_v5_market.py 内修改
  - 保持文件名不变
  - main_json.js 无需修改
""")

# 移动临时脚本
tmp = r'e:\csi10\update_guide.py'
if os.path.exists(tmp):
    shutil.move(tmp, r'e:\csi10\py\update_guide.py')

print("\n✅ 最佳实践已记录")