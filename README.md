# 波段股票分析系统 v5.0

## Electron运行环境

程序运行在Electron环境中，Python脚本由Electron主进程调用。

## 核心文件（根目录）

| 文件 | 功能 | 必须保留 |
|-----|------|---------|
| analyzer_v5_market.py | 主分析引擎v5.0 | ★ |
| analyzer_v4.py | 分析引擎v4.0（备用） | ★ |
| data_fetcher.py | 实时数据获取 | ★ |
| market_index_fetcher.py | 大盘指数数据获取 | ★ |
| index.html | 前端界面（Electron渲染） | ★ |
| result.json | 分析输出（v5格式） | ★ |
| holdings.json | 用户持仓数据 | ★ |
| 波段股票Top30.csv | 股票池配置 | ★ |
| main_json.js | Electron主进程 | ★ |
| preload.js | Electron桥接层 | ★ |

## py文件夹（测试/辅助脚本）

所有测试、回测、调试脚本放入py文件夹：

- 回测脚本 (market_backtest.py, full_backtest.py)
- 测试脚本 (check_*.py, verify_*.py)
- 临时脚本 (fix_*.py, update_*.py)
- 辅助文档 (VERSION-GUIDE.md, INTEGRATION-REPORT.md)

## 更新优化规则

**每次更新必须遵守：**

1. 核心脚本保持在根目录
2. 测试脚本放入py文件夹
3. 更新后测试Python独立运行
4. 更新后测试Electron完整流程
5. 确保result.json结构正确
6. 更新version字段

## 使用流程

```bash
# 更新大盘数据（每日）
python market_index_fetcher.py

# 运行分析
python analyzer_v5_market.py

# Electron启动
运行启动.bat 或 Electron应用
```

## 架构

```
Electron应用
    ↓
index.html (前端)
    ↓
preload.js (桥接)
    ↓
main_json.js (主进程)
    ↓
Python脚本调用
    ↓
result.json
    ↓
前端显示
```

## 详细指南

查看 ELECTRON-RUN-GUIDE.md 了解完整规范。