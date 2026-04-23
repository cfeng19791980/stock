# 股票预测系统优化 PRD v1.0

## 文档信息

| 项目 | 内容 |
|------|------|
| **文档版本** | v1.0 |
| **创建日期** | 2026-04-18 |
| **项目负责人** | 付郁 |
| **优先级** | P1 - 高优先级 |
| **预计开发周期** | 3-5 工作日 |

---

## 1. 项目背景

### 1.1 现状分析

当前波段股票分析系统（v2.0）预测准确率**不足 70%**，经根因分析发现：

- ❌ **核心问题**：模型缺少大盘走势数据因子
- ❌ **影响**：无法捕捉市场整体趋势对个股的影响
- ❌ **数据现状**：数据库 `index_daily` 表仅有沪深 300 指数 (sh.000300)，**缺少上证指数 (000001.SS)**

### 1.2 优化目标

| 指标 | 当前值 | 目标值 | 提升幅度 |
|------|--------|--------|----------|
| **预测准确率** | < 70% | **75-80%** | +5-10% |
| **数据覆盖** | 仅个股 | 个股 + 大盘 | +100% |
| **特征维度** | ~25 个 | **30-35 个** | +5-10 个 |

---

## 2. 功能需求

### 2.1 大盘数据获取模块

#### 2.1.1 数据源选择

| 优先级 | 数据源 | 代码 | 说明 |
|--------|--------|------|------|
| 🥇 **主数据源** | **上证指数** | `000001.SS` | 反映上海市场整体走势 |
| 🥈 辅助数据源 | 深证成指 | `399001.SZ` | 反映深圳市场走势 |
| 🥉 参考数据源 | 沪深 300 | `000300` | 已存在，可直接使用 |

#### 2.1.2 获取方式

**方案 A：Tushare API（推荐）**
```python
import tushare as ts

# 初始化
ts.set_token('YOUR_TOKEN')
pro = ts.pro_api()

# 获取上证指数日线数据
df = pro.index_daily(ts_code='000001.SS', start_date='20240101')
```

**方案 B：AkShare（免费备选）**
```python
import akshare as ak

# 获取上证指数数据
df = ak.stock_zh_index_daily(symbol="sh000001")
```

**方案 C：新浪财经（快速备份）**
```python
import requests

url = "http://hq.sinajs.cn/sh000001"
response = requests.get(url)
```

#### 2.1.3 更新策略

| 类型 | 频率 | 时间 | 说明 |
|------|------|------|------|
| **盘后更新** | 每日 1 次 | 15:30-17:00 | 获取当日完整数据 |
| **盘中更新** | 每 5 分钟 | 9:30-15:00 | 可选，用于实时预测 |
| **周末补全** | 每周 1 次 | 周六上午 | 检查并补全缺失数据 |

---

### 2.2 特征工程模块

#### 2.2.1 新增大盘特征因子

| 特征名 | 类型 | 计算方式 | 说明 |
|--------|------|----------|------|
| **market_trend** | 趋势 | 上证指数 5 日涨跌幅 | 大盘短期趋势 |
| **market_ma5_ratio** | 位置 | 指数收盘价/MA5 | 相对 5 日线位置 |
| **market_ma20_ratio** | 位置 | 指数收盘价/MA20 | 相对 20 日线位置 |
| **market_volume_ratio** | 量能 | 当日成交量/20 日均量 | 放量/缩量 |
| **market_macd** | 动量 | 指数 MACD 值 | 大盘动能 |
| **market_rsi** | 超买超卖 | 指数 RSI(6) | 大盘超买超卖 |
| **stock_vs_market** | 相对强弱 | 个股涨幅 - 大盘涨幅 | 个股相对表现 |
| **market_correlation** | 相关性 | 个股与大盘 20 日相关系数 | 联动性 |
| **market_beta** | 贝塔系数 | 个股相对大盘的 Beta | 系统性风险 |
| **market_sentiment** | 情绪 | 涨跌家数比或涨停数 | 市场情绪 |

#### 2.2.2 特征计算示例

```python
def extract_market_features(stock_df, market_df, i):
    """提取大盘相关特征"""
    features = {}
    
    # 获取当日大盘数据
    market_row = market_df.iloc[i]
    market_close = market_row['close']
    market_pct_chg = market_row['pct_chg']
    market_volume = market_row['volume']
    
    # 大盘趋势
    if i >= 5:
        market_ma5 = market_df.iloc[i-5:i]['close'].mean()
        features['market_trend'] = (market_close - market_ma5) / market_ma5 * 100
        features['market_ma5_ratio'] = market_close / market_ma5
    else:
        features['market_trend'] = 0
        features['market_ma5_ratio'] = 1
    
    # 大盘位置（20 日线）
    if i >= 20:
        market_ma20 = market_df.iloc[i-20:i]['close'].mean()
        features['market_ma20_ratio'] = market_close / market_ma20
    else:
        features['market_ma20_ratio'] = 1
    
    # 大盘量能
    if i >= 20:
        market_vol_ma = market_df.iloc[i-20:i]['volume'].mean()
        features['market_volume_ratio'] = market_volume / market_vol_ma
    else:
        features['market_volume_ratio'] = 1
    
    # 大盘 MACD（需预先计算）
    features['market_macd'] = market_row.get('macd', 0)
    features['market_rsi'] = market_row.get('rsi6', 50)
    
    # 个股相对大盘表现
    stock_pct = stock_df.iloc[i]['pct_chg']
    features['stock_vs_market'] = stock_pct - market_pct_chg
    
    # 20 日相关系数
    if i >= 20:
        stock_returns = stock_df.iloc[i-20:i]['pct_chg'].values
        market_returns = market_df.iloc[i-20:i]['pct_chg'].values
        features['market_correlation'] = np.corrcoef(stock_returns, market_returns)[0, 1]
    else:
        features['market_correlation'] = 0
    
    return features
```

---

### 2.3 模型训练模块

#### 2.3.1 模型架构调整

**当前模型**：
```
RandomForest(n_estimators=100, max_depth=5)
特征数：~25 个
```

**优化后模型**：
```
RandomForest(n_estimators=150, max_depth=6)
特征数：~35 个（+10 个大盘因子）
```

#### 2.3.2 训练数据划分

| 数据集 | 时间范围 | 比例 | 用途 |
|--------|----------|------|------|
| **训练集** | 2024-01 至 2025-12 | 70% | 模型训练 |
| **验证集** | 2026-01 至 2026-02 | 15% | 超参调优 |
| **测试集** | 2026-03 至 2026-04 | 15% | 效果评估 |

#### 2.3.3 模型评估指标

```python
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# 评估指标
accuracy = accuracy_score(y_true, y_pred)      # 准确率（目标：75-80%）
precision = precision_score(y_true, y_pred)    # 查准率
recall = recall_score(y_true, y_pred)          # 查全率
f1 = f1_score(y_true, y_pred)                  # F1 分数
```

---

## 3. 数据需求

### 3.1 数据库结构

#### 3.1.1 现有表结构

**`index_daily` 表（需扩展）**
```sql
CREATE TABLE index_daily (
    code TEXT,        -- 指数代码 (000001.SS)
    date TEXT,        -- 日期 (YYYY-MM-DD)
    open REAL,        -- 开盘价
    high REAL,        -- 最高价
    low REAL,         -- 最低价
    close REAL,       -- 收盘价
    volume REAL,      -- 成交量
    amount REAL,      -- 成交额
    pct_chg REAL,     -- 涨跌幅
    -- 新增字段 ↓
    macd REAL,        -- MACD 值
    macd_signal REAL, -- MACD 信号线
    macd_hist REAL,   -- MACD 柱状图
    rsi6 REAL,        -- RSI(6)
    ma5 REAL,         -- 5 日均线
    ma10 REAL,        -- 10 日均线
    ma20 REAL         -- 20 日均线
);
```

#### 3.1.2 数据量估算

| 指数 | 数据频率 | 起始日期 | 预计行数 |
|------|----------|----------|----------|
| 上证指数 | 日线 | 2024-01-01 | ~500 行 |
| 深证成指 | 日线 | 2024-01-01 | ~500 行 |
| 沪深 300 | 日线 | 2024-01-01 | ~500 行（已存在） |

---

### 3.2 数据存储策略

#### 3.2.1 存储位置

```
E:\股票\csi500_data\stocks.db
├── stocks          -- 股票基本信息
├── daily_price     -- 个股日线数据（615,477 行）
└── index_daily     -- 指数日线数据（目标：1,500 行）
```

#### 3.2.2 索引优化

```sql
-- 为查询优化添加索引
CREATE INDEX IF NOT EXISTS idx_index_code ON index_daily(code);
CREATE INDEX IF NOT EXISTS idx_index_date ON index_daily(date);
CREATE INDEX IF NOT EXISTS idx_index_code_date ON index_daily(code, date);
```

---

## 4. 技术需求

### 4.1 文件修改清单

| 文件 | 修改类型 | 优先级 | 说明 |
|------|----------|--------|------|
| **data_fetcher.py** | 修改 + 新增 | P0 | 添加大盘数据获取函数 |
| **final_analysis_system_v2.py** | 修改 | P0 | 整合大盘特征到模型 |
| **market_data_fetcher.py** | 新增 | P1 | 独立的大盘数据获取模块 |
| **feature_engineering.py** | 新增 | P1 | 特征计算工具类 |

---

### 4.2 新增函数清单

#### 4.2.1 `data_fetcher.py` 新增

```python
class DataFetcher:
    # 现有函数...
    
    # === 新增函数 ===
    
    def get_market_index_data(self, ts_code='000001.SS', start_date='20240101'):
        """获取大盘指数数据"""
        pass
    
    def update_index_daily(self):
        """更新指数日线数据到数据库"""
        pass
    
    def calculate_index_indicators(self, df):
        """计算指数技术指标（MA/MACD/RSI）"""
        pass
```

#### 4.2.2 `final_analysis_system_v2.py` 修改

```python
class FinalAnalyzerV2:
    # 现有函数...
    
    # === 修改函数 ===
    
    def _train_model(self, code):
        # 修改：加载大盘数据并传入特征提取
        market_df = self._load_market_data()
        model_data = self._train_model_with_market(code, market_df)
        
    def _extract_features(self, df, i):
        # 修改：增加大盘特征参数
        def _extract_features(self, df, market_df, i):
            # 原有特征...
            # 新增大盘特征...
    
    # === 新增函数 ===
    
    def _load_market_data(self):
        """加载大盘数据"""
        sql = '''
            SELECT * FROM index_daily 
            WHERE code = '000001.SS' 
            ORDER BY date ASC
        '''
        return pd.read_sql_query(sql, self.conn)
    
    def _calculate_market_features(self, stock_df, market_df, i):
        """计算大盘相关特征"""
        pass
```

---

### 4.3 代码实现示例

#### 4.3.1 大盘数据获取器（新增文件）

```python
# -*- coding: utf-8 -*-
"""
大盘数据获取模块
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import sqlite3
import tushare as ts
from datetime import datetime

DB_PATH = r'E:\股票\csi500_data\stocks.db'

class MarketDataFetcher:
    """大盘数据获取器"""
    
    def __init__(self, tushare_token=None):
        self.conn = sqlite3.connect(DB_PATH)
        if tushare_token:
            ts.set_token(tushare_token)
            self.pro = ts.pro_api()
        else:
            self.pro = None
    
    def fetch_shanghai_index(self, start_date='20240101', end_date=None):
        """获取上证指数数据"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        if self.pro:
            # 使用 Tushare
            df = self.pro.index_daily(
                ts_code='000001.SS',
                start_date=start_date,
                end_date=end_date
            )
        else:
            # 使用 AkShare（备选）
            import akshare as ak
            df = ak.stock_zh_index_daily(symbol="sh000001")
            df = self._format_akshare_data(df)
        
        # 计算技术指标
        df = self._calculate_indicators(df)
        
        return df
    
    def _format_akshare_data(self, df):
        """格式化 AkShare 数据为统一格式"""
        df = df.rename(columns={
            'date': 'trade_date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'vol'
        })
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
        df['ts_code'] = '000001.SS'
        return df
    
    def _calculate_indicators(self, df):
        """计算技术指标"""
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        # 均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(6).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(6).mean()
        rs = gain / loss
        df['rsi6'] = 100 - (100 / (1 + rs))
        
        return df
    
    def save_to_db(self, df):
        """保存到数据库"""
        df.to_sql('index_daily', self.conn, if_exists='append', index=False)
        print(f"已保存 {len(df)} 条指数数据")
    
    def close(self):
        self.conn.close()
```

---

## 5. 性能需求

### 5.1 准确率目标

| 场景 | 当前准确率 | 目标准确率 | 验证方式 |
|------|-----------|-----------|----------|
| **整体预测** | < 70% | **75-80%** | 回测测试集 |
| **买入信号** | ~65% | **75%+** | 实盘跟踪 |
| **卖出信号** | ~68% | **72%+** | 回测验证 |
| **持有信号** | ~70% | **78%+** | 历史回测 |

### 5.2 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **预测延迟** | < 5 秒 | 单只股票预测时间 |
| **全量分析** | < 3 分钟 | 30 只股票完整分析 |
| **数据更新** | < 30 秒 | 大盘数据获取 + 入库 |
| **内存占用** | < 500MB | 峰值内存使用 |

### 5.3 验证方案

```python
def validate_improvement():
    """验证优化效果"""
    
    # 1. 回测历史数据
    backtest_results = backtest_period(
        start='2026-03-01',
        end='2026-04-15',
        use_market_features=True
    )
    
    # 2. 对比基线
    baseline_results = backtest_period(
        start='2026-03-01',
        end='2026-04-15',
        use_market_features=False
    )
    
    # 3. 计算提升
    improvement = (
        backtest_results['accuracy'] - baseline_results['accuracy']
    ) / baseline_results['accuracy']
    
    print(f"准确率提升：{improvement:.2%}")
    print(f"目标达成：{'✅' if improvement >= 0.07 else '❌'}")
    
    return {
        'baseline_accuracy': baseline_results['accuracy'],
        'optimized_accuracy': backtest_results['accuracy'],
        'improvement': improvement,
        'target_met': improvement >= 0.07
    }
```

---

## 6. 开发计划

### 6.1 里程碑

| 阶段 | 任务 | 预计工时 | 交付物 |
|------|------|----------|--------|
| **Phase 1** | 大盘数据获取模块 | 1 天 | `market_data_fetcher.py` |
| **Phase 2** | 特征工程实现 | 1-2 天 | 特征计算函数 |
| **Phase 3** | 模型整合训练 | 1 天 | 优化后模型 |
| **Phase 4** | 回测验证 | 1 天 | 验证报告 |
| **Phase 5** | 部署上线 | 0.5 天 | 生产环境 |

### 6.2 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 数据源不稳定 | 中 | 高 | 多数据源备份（Tushare+AkShare+ 新浪） |
| 准确率提升不足 | 中 | 高 | 增加特征工程、调参优化 |
| 性能下降 | 低 | 中 | 优化数据库索引、缓存大盘数据 |
| 过拟合 | 中 | 中 | 交叉验证、正则化、简化模型 |

---

## 7. 验收标准

### 7.1 功能验收

- [ ] 大盘数据可正常获取并入库
- [ ] 大盘特征可正确计算
- [ ] 模型训练包含大盘因子
- [ ] 预测结果可展示大盘影响

### 7.2 性能验收

- [ ] 回测准确率 ≥ 75%
- [ ] 预测延迟 < 5 秒/股
- [ ] 内存占用 < 500MB
- [ ] 数据更新 < 30 秒

### 7.3 代码验收

- [ ] 代码审查通过
- [ ] 单元测试覆盖 > 80%
- [ ] 文档完整
- [ ] UTF-8 编码设置正确

---

## 8. 附录

### 8.1 参考文档

- Tushare API 文档：https://tushare.pro/document/2
- AkShare 文档：https://akshare.akfamily.xyz/
- sklearn 随机森林：https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html

### 8.2 相关文件

| 文件路径 | 说明 |
|----------|------|
| `e:\csi10\final_analysis_system_v2.py` | 主分析系统 |
| `e:\csi10\data_fetcher.py` | 数据获取器 |
| `E:\股票\csi500_data\stocks.db` | 数据库 |
| `e:\csi10\market_data_fetcher.py` | 大盘数据获取器（待创建） |
| `e:\csi10\feature_engineering.py` | 特征工程（待创建） |

---

## 9. 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-04-18 | 初始版本 | 付郁 |

---

**文档结束**

---

## 快速实施清单

```bash
# 1. 安装依赖
pip install tushare akshare

# 2. 创建大盘数据获取器
# 文件：e:\csi10\market_data_fetcher.py

# 3. 创建特征工程模块
# 文件：e:\csi10\feature_engineering.py

# 4. 修改主分析系统
# 文件：e:\csi10\final_analysis_system_v2.py
# 修改点：_extract_features(), _train_model()

# 5. 获取历史大盘数据
python e:\csi10\market_data_fetcher.py

# 6. 回测验证
python e:\csi10\backtest_validation.py

# 7. 部署上线
python e:\csi10\final_analysis_system_v2.py
```

---

**批准签字:**

| 角色 | 姓名 | 日期 | 签字 |
|------|------|------|------|
| 产品负责人 | | | |
| 技术负责人 | | | |
| 开发负责人 | | | |
