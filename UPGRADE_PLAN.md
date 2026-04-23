# csi10 大步优化方案 (2026-04-23)

## 用户确认
- csi10是应用级程序，可以走大步子
- 核心：备份回滚 + 回测验证 + 反馈闭环

---

## Phase 1: 数据+特征大升级 (预计3天)

### 1.1 数据源扩展

| 数据类型 | 来源 | 用途 |
|----------|------|------|
| 分钟K线 | 腾讯/新浪 | 实时捕捉 |
| 资金流向 | 东方财富 | 主力动向 |
| 板块数据 | 同花顺 | 行业联动 |
| 北向资金 | 港交所 | 外资动向 |

### 1.2 特征大扩展 (12→25+)

**新增特征组1: 资金类**
```python
- net_inflow       # 主力净流入
- north_change     # 北向持股变化
- big_order_ratio  # 大单占比
- small_order_ratio # 小单占比
```

**新增特征组2: 波动类**
```python
- atr_5           # 5日ATR
- atr_20          # 20日ATR
- volatility_ratio # 波动率比
- amplitude_10    # 10日振幅均值
```

**新增特征组3: 板块类**
```python
- sector_pct_chg  # 板块涨跌
- sector_rank     # 板块内排名
- leader_pct      # 龙头股涨跌
- sector_corr     # 板块相关性
```

**新增特征组4: 时间类**
```python
- day_of_week     # 周几
- month           # 月份
- is_first_week   # 月初
- is_last_week    # 月末
```

**新增特征组5: 历史类**
```python
- recent_band_count  # 近期波段次数
- band_success_rate  # 波段成功率
- avg_band_amplitude # 平均波段幅度
```

---

## Phase 2: 模型大升级 (预计2天)

### 2.1 多模型融合

| 模型 | 用途 | 权重 |
|------|------|------|
| XGBoost | 主模型 | 40% |
| LightGBM | 快速模型 | 30% |
| CatBoost | 类别特征 | 20% |
| LSTM | 时序捕捉 | 10% |

### 2.2 融合策略
```python
final_score = (
    xgb_pred * 0.4 +
    lgb_pred * 0.3 +
    cat_pred * 0.2 +
    lstm_pred * 0.1
)
```

---

## Phase 3: 反馈闭环系统 (预计2天)

### 3.1 预测记录表
```sql
CREATE TABLE prediction_logs (
    id INTEGER PRIMARY KEY,
    stock_code TEXT,
    predict_date TEXT,
    predict_score INTEGER,
    predict_action TEXT,  -- 'buy'/'hold'/'sell'
    actual_result TEXT,   -- 'success'/'fail'
    actual_return REAL,   -- 实际收益%
    feedback_time TEXT
);
```

### 3.2 每日反馈流程
```
1. 开盘前: 记录昨日预测
2. 收盘后: 记录实际结果
3. 夜间: 自动计算准确率
4. 周末: 模型增量训练
```

### 3.3 准确率监控
```python
class AccuracyMonitor:
    def daily_check(self):
        # 计算当日准确率
        # 低于阈值触发警报
        
    def weekly_report(self):
        # 生成周报
        # 分析失败案例
        # 提取改进Pattern
```

---

## Phase 4: 回测系统 (预计1天)

### 4.1 回测框架
```python
class Backtester:
    def run(self, start_date, end_date):
        # 模拟历史交易
        # 计算收益率、胜率、最大回撤
        
    def compare(self, old_model, new_model):
        # 对比新旧模型表现
        # 新模型必须优于旧模型
```

### 4.2 验收标准
| 指标 | 旧模型 | 新模型目标 |
|------|--------|-----------|
| 准确率 | ~65% | ≥70% |
| 胜率 | ~55% | ≥60% |
| 最大回撤 | ~15% | ≤12% |
| 夏普比率 | ~1.2 | ≥1.5 |

---

## Phase 5: 备份回滚机制 (预计1天)

### 5.1 自动备份
```python
def backup_before_upgrade():
    # 1. 备份数据库
    shutil.copy('stocks.db', f'socks.db.bak.{datetime.now():%Y%m%d}')
    
    # 2. 备份模型缓存
    shutil.copytree('model_cache', f'model_cache.bak.{datetime.now():%Y%m%d}')
    
    # 3. 备份代码
    git commit -am "backup before upgrade"
    git tag f"backup-{datetime.now():%Y%m%d-%H%M}"
```

### 5.2 快速回滚
```python
def rollback():
    # 1. 恢复数据库
    # 2. 恢复模型
    # 3. Git revert
```

---

## 实施计划

### Day 1: 数据+特征
- [ ] 分钟数据获取接口
- [ ] 资金流向接口
- [ ] 板块数据接口
- [ ] 25个特征计算函数

### Day 2: 模型融合
- [ ] LightGBM训练
- [ ] CatBoost训练
- [ ] LSTM模型
- [ ] 融合评分函数

### Day 3: 回测+反馈
- [ ] 回测框架
- [ ] 预测记录表
- [ ] 准确率监控
- [ ] 周报生成

### Day 4: 备份+验证
- [ ] 自动备份脚本
- [ ] 回滚脚本
- [ ] 全量回测验证
- [ ] 上线发布

---

## OPT-REQ 模板

```
OPT-REQ-009: csi10大步升级-数据特征
风险级别: 中风险（应用级）
备份机制: Git tag + DB备份
验收标准: 回测准确率≥70%

OPT-REQ-010: csi10大步升级-模型融合
风险级别: 中风险
备份机制: 模型缓存备份
验收标准: 融合模型优于单模型

OPT-REQ-011: csi10大步升级-反馈闭环
风险级别: 低风险
验收标准: 每日自动记录预测结果
```

---

**署名**: 付郁 (cfeng19791980, 10341731@qq.com)
**时间**: 2026-04-23 20:02