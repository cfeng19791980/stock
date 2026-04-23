# 波段股票分析系统 v2.1

## 系统架构（根目录统一版）

```
e:\csi10\
├── 启动.bat              # 统一启动脚本
├── final_v2_clean.py     # Python后端 (v2.1 XGBoost + 43特征)
├── data_fetcher.py       # 数据获取脚本
├── main.js               # Electron主进程
├── preload.js            # IPC桥接
├── index.html            # 前端界面
├── package.json          # 项目配置
├── 波段股票Top30.csv     # 股票池CSV
├── stocks.db             # SQLite数据库 (250MB)
├── README.md             # 说明文档
├── node_modules/         # npm依赖
├── backup/               # 备份目录
└── py/                   # 历史/测试文件归档
```

## 启动方式

直接双击 `启动.bat` 或命令行：

```powershell
e:\csi10\启动.bat
```

启动流程：
1. 清理端口5000占用
2. 检查并安装npm依赖
3. 启动Electron桌面应用
4. Electron自动启动Python后端

## 技术规格

| 项目 | 版本 |
|------|------|
| **Python后端** | v2.1-xgboost-43features |
| **ML模型** | XGBoost |
| **特征数** | 43个 |
| **平均准确率** | 74.24% |
| **最高准确率** | 85.23% |
| **前端** | Electron |
| **通讯** | IPC + HTTP API |

## API接口

| API | 说明 |
|------|------|
| `/api/status` | 系统状态 |
| `/api/accuracy` | 准确率报告 |
| `/api/all` | 全部股票分析 |
| `/api/buy` | 买入推荐 |
| `/api/sell` | 卖出信号 |
| `/api/refresh` | 刷新数据 |

## 特征清单 (43个)

| 类别 | 特征数 | 特征名称 |
|------|--------|---------|
| **价格动量** | 3 | pct_chg, pct_chg_5d, pct_chg_10d |
| **均线系统** | 7 | ma5_ratio, ma10_ratio, ma20_ratio, ma30_ratio, ma5_ma10_diff, ma10_ma20_diff, ma5_slope |
| **RSI系统** | 6 | rsi6, rsi12, rsi24, rsi6_rsi12_diff, rsi_oversold, rsi_overbought |
| **MACD系统** | 5 | macd, macd_hist, macd_signal, macd_cross_up, macd_cross_down |
| **KDJ系统** | 4 | k, d, j, kdj_cross |
| **量价关系** | 2 | vol_ratio, vol_price_trend |
| **波动率** | 2 | volatility_20, volatility_30 |
| **价格位置** | 1 | price_position_60 |
| **涨跌统计** | 4 | up_days_5, down_days_5, up_days_10, down_days_10 |
| **日内波动** | 1 | intraday_range |
| **大盘因子** | 7 | index_pct_chg, index_ma5_ratio, index_rsi6, index_rsi12, index_macd, index_macd_hist, stock_vs_index |

## 优化历史

| 版本 | 模型 | 特征数 | 准确率 | 日期 |
|------|------|--------|--------|------|
| v1.0 | RandomForest | 16 | <70% | 2026-04-17 |
| v2.0 | RandomForest | 22 | 71.82% | 2026-04-18 |
| v2.1 | XGBoost | 43 | **74.24%** | 2026-04-18 |

---

**所有文件统一在根目录下，开发优化更方便！** 🦞

_Last updated: 2026-04-18 13:15_