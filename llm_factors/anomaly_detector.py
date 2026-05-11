# -*- coding: utf-8 -*-
"""
异动规则引擎 v1.0
量化标准，触发任意一条 → 判定为异动 → 丢给LLM分析

量化阈值（散户版，嫌严嫌松随便改数字）:
1. 涨跌幅异动: >= +3% / <= -3%
2. 量能异动: >= 1.8倍 / <= 0.5倍
3. 急速异动: >= +2.5% / <= -2.5%
4. 价格位置: 突破/跌破5日均线
5. 涨跌停边缘: >= +8% / <= -8%
"""

import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ============================================================
# 量化阈值（硬编码，可直接调参）
# ============================================================

THRESHOLDS = {
    # 1. 涨跌幅异动
    "pct_change_up": 3.0,      # 涨幅 >= +3%
    "pct_change_down": -3.0,   # 跌幅 <= -3%

    # 2. 量能异动
    "vol_ratio_up": 1.8,       # 放量 >= 1.8倍
    "vol_ratio_down": 0.5,     # 缩量 <= 0.5倍

    # 3. 急速异动（5分钟区间）
    "rapid_rise": 2.5,         # 快速拉升 >= +2.5%
    "rapid_fall": -2.5,        # 快速跳水 <= -2.5%

    # 4. 涨跌停边缘
    "limit_edge_up": 8.0,      # 接近涨停 >= +8%
    "limit_edge_down": -8.0,   # 接近跌停 <= -8%
}


# ============================================================
# 数据结构
# ============================================================

@dataclass
class AnomalyResult:
    """异动判定结果"""
    is_anomaly: bool = False
    reasons: List[str] = field(default_factory=list)
    severity: str = "none"       # high / medium / low / none
    details: Dict = field(default_factory=dict)


def detect_anomaly(
    current_price: float,
    prev_price: float,          # 5分钟前价格
    current_volume: float,      # 当前成交量
    avg_volume_5min: float,     # 5分钟平均成交量
    ma5: float = 0,             # 5日均线
    prev_close: float = 0,      # 昨收
    code: str = "",
) -> AnomalyResult:
    """
    接收单只股票行情字典，返回异动判定结果。

    参数:
        current_price: 当前价格
        prev_price: 5分钟前价格
        current_volume: 当前成交量
        avg_volume_5min: 5分钟平均成交量
        ma5: 5日均线
        prev_close: 昨收

    返回:
        AnomalyResult { is_anomaly, reasons, severity, details }
    """
    reasons = []
    severity = "none"
    details = {}

    # ========== 1. 涨跌幅异动 ==========
    if prev_price > 0:
        pct_change = (current_price - prev_price) / prev_price * 100
        details["pct_change"] = round(pct_change, 2)

        if pct_change >= THRESHOLDS["pct_change_up"]:
            reasons.append(f"涨幅异动({pct_change:+.2f}%)")
            severity = "high"
        elif pct_change <= THRESHOLDS["pct_change_down"]:
            reasons.append(f"跌幅异动({pct_change:+.2f}%)")
            severity = "high"
    else:
        details["pct_change"] = 0

    # ========== 2. 量能异动 ==========
    if avg_volume_5min > 0 and current_volume > 0:
        vol_ratio = current_volume / avg_volume_5min
        details["vol_ratio"] = round(vol_ratio, 2)

        if vol_ratio >= THRESHOLDS["vol_ratio_up"]:
            reasons.append(f"放量异动({vol_ratio:.1f}倍)")
            if severity != "high":
                severity = "medium"
        elif vol_ratio <= THRESHOLDS["vol_ratio_down"]:
            reasons.append(f"缩量观望({vol_ratio:.1f}倍)")
            if severity == "none":
                severity = "low"
    else:
        details["vol_ratio"] = 0

    # ========== 3. 急速异动 ==========
    if prev_price > 0:
        rapid_change = (current_price - prev_price) / prev_price * 100
        details["rapid_change"] = round(rapid_change, 2)

        if rapid_change >= THRESHOLDS["rapid_rise"]:
            reasons.append(f"急速拉升({rapid_change:+.2f}%)")
            severity = "high"
        elif rapid_change <= THRESHOLDS["rapid_fall"]:
            reasons.append(f"急速跳水({rapid_change:+.2f}%)")
            severity = "high"

    # ========== 4. 价格位置异动 ==========
    if ma5 and ma5 > 0 and current_price > 0:
        details["ma5"] = round(ma5, 2)

        pct_to_ma5 = (current_price - ma5) / ma5 * 100
        details["pct_to_ma5"] = round(pct_to_ma5, 2)

        # 从下方突破5日均线
        if prev_price > 0 and current_price > ma5 and prev_price <= ma5:
            reasons.append(f"突破5日均线({current_price:.2f}>{ma5:.2f})")
            if severity != "high":
                severity = "medium"
        # 从上方跌破5日均线
        elif prev_price > 0 and current_price < ma5 and prev_price >= ma5:
            reasons.append(f"跌破5日均线({current_price:.2f}<{ma5:.2f})")
            if severity != "high":
                severity = "medium"

    # ========== 5. 涨跌停边缘 ==========
    if prev_close > 0:
        daily_pct = (current_price - prev_close) / prev_close * 100
        details["daily_pct"] = round(daily_pct, 2)

        if daily_pct >= THRESHOLDS["limit_edge_up"]:
            reasons.append(f"涨停边缘({daily_pct:+.2f}%)")
            severity = "high"
        elif daily_pct <= THRESHOLDS["limit_edge_down"]:
            reasons.append(f"跌停边缘({daily_pct:+.2f}%)")
            severity = "high"

    # ========== 判定 ==========
    is_anomaly = len(reasons) > 0
    if not is_anomaly:
        severity = "none"

    return AnomalyResult(
        is_anomaly=is_anomaly,
        reasons=reasons,
        severity=severity,
        details=details,
    )


def detect_from_dict(stock: Dict) -> AnomalyResult:
    """
    从行情字典检测异动。
    可接受的字段名（大小写不敏感）:
        code, price, prev_price, volume, avg_vol_5min, ma5, prev_close
    """
    def _get(key: str, default=0):
        val = stock.get(key, stock.get(key.lower(), default))
        return val if val else default

    return detect_anomaly(
        current_price=_get("price"),
        prev_price=_get("prev_price", _get("prevPrice", _get("open_price", 0))),
        current_volume=_get("volume"),
        avg_volume_5min=_get("avg_vol_5min", _get("avgVolume5min", 0)),
        ma5=_get("ma5"),
        prev_close=_get("prev_close", _get("prevClose", 0)),
        code=_get("code", ""),
    )


def batch_detect(stocks: List[Dict]) -> List[Dict]:
    """
    批量检测异动。

    输入: [{'code':'000034','price':42.91,'prev_price':40.55,...}, ...]
    输出: [{'code':'000034','is_anomaly':True,'reasons':[...],'severity':'high'}, ...]
    """
    results = []
    for stock in stocks:
        anomaly = detect_from_dict(stock)
        if anomaly.is_anomaly:
            results.append({
                "code": stock.get("code", ""),
                "is_anomaly": True,
                "reasons": anomaly.reasons,
                "severity": anomaly.severity,
                "details": anomaly.details,
            })
            # 添加到原始 dict 方便后续使用
            stock["anomaly_flag"] = 1
            stock["anomaly_reasons"] = json.dumps(anomaly.reasons, ensure_ascii=False)
            stock["anomaly_severity"] = anomaly.severity
        else:
            stock["anomaly_flag"] = 0

    return results


def format_llm_prompt(stock: Dict, anomaly: AnomalyResult) -> str:
    """生成 LLM 分析提示词"""
    code = stock.get("code", "?")
    name = stock.get("name", code)
    price = stock.get("price", 0)
    reasons_str = "；".join(anomaly.reasons)
    pct = anomaly.details.get("pct_change", 0)
    vol_ratio = anomaly.details.get("vol_ratio", 0)

    return f"""股票: {name}({code})
当前价: {price}元
异动信号: {reasons_str}
涨幅: {pct:+.2f}%
量能: {vol_ratio:.1f}倍平均量

请分析:
1. 该异动的可能原因（市场情绪、板块效应、资金流向等）
2. 短期（当日）趋势判断
3. 操作建议（买入/持有/卖出/观望）
4. 置信度评分（0-100）

以JSON格式输出。"""


# ============================================================
# 自测
# ============================================================

if __name__ == "__main__":
    print("=== 异动规则引擎自测 ===\n")

    # 测试案例 1: 神州数码（涨跌幅+成交量双异动）
    test1 = {
        "code": "000034",
        "name": "神州数码",
        "price": 42.91,
        "prev_price": 40.55,
        "volume": 674944,
        "avg_vol_5min": 400000,
        "ma5": 41.50,
        "prev_close": 40.02,
    }
    r1 = detect_from_dict(test1)
    print(f"[{test1['code']}] {test1['name']}:")
    print(f"  异动: {r1.is_anomaly}, 等级: {r1.severity}")
    print(f"  原因: {r1.reasons}")
    print(f"  详情: {r1.details}\n")

    # 测试案例 2: 横盘股票（无异动）
    test2 = {
        "code": "600519",
        "name": "贵州茅台",
        "price": 1680.0,
        "prev_price": 1680.0,
        "volume": 10000,
        "avg_vol_5min": 12000,
        "ma5": 1685.0,
        "prev_close": 1685.0,
    }
    r2 = detect_from_dict(test2)
    print(f"[{test2['code']}] {test2['name']}:")
    print(f"  异动: {r2.is_anomaly}, 等级: {r2.severity}")
    print(f"  原因: {r2.reasons}")
    print(f"  详情: {r2.details}\n")

    # 测试案例 3: 批量测试
    batch = batch_detect([test1, test2])
    print(f"批量: {len(batch)} 只异动 (应=1)")
    for b in batch:
        print(f"  {b['code']}: {b['reasons']} [{b['severity']}]")
