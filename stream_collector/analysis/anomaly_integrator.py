# -*- coding: utf-8 -*-
"""
异动集成器 — anomaly_integrator.py

将异动检测 + LLM分析 嵌入流式采集管线。
当拦截器捕获数据后，由 _on_data() 回调触发此模块。

流程:
  intercepted_data → anomaly_detector → 结果写入 daily_features
      ↓ 如果是异动
  LLM分析 → 结果写入 daily_features.llm_analysis
"""

import json
import os
import sys
import sqlite3
import logging
import requests
from typing import Dict, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)

# 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "stocks.db")

# LLM配置 (llama-server)
LLM_URL = "http://127.0.0.1:1235/v1/chat/completions"
LLM_MODEL = "qwen2.5-7b-instruct"

# 引入异动检测
sys.path.insert(0, os.path.join(BASE_DIR, "llm_factors"))
from anomaly_detector import detect_anomaly, format_llm_prompt


ANOMALY_LLM_PROMPT = """你是A股量化分析助手。分析给定的异动信号。

股票: {name}({code})
当前价: {price}元
异动信号: {reasons}
涨幅: {pct_change:+.2f}%
量能: 当前量 / 5分钟均量 = {vol_ratio:.1f}倍

请分析:
1. 异动原因（市场情绪、板块效应、资金流向等）
2. 短期趋势判断（当日）
3. 操作建议（买入/持有/卖出/观望）
4. 置信度（0-100）

以JSON格式输出，只输出JSON。"""


class AnomalyIntegrator:
    """异动集成器 — 挂在 _on_data() 回调后面运行"""

    def __init__(self, db_path: str = DB_PATH, enable_llm: bool = True):
        self.db_path = db_path
        self.enable_llm = enable_llm
        self._cache: Dict[str, Dict] = {}  # code -> last_data
        self._analysis_count = 0
        self._llm_count = 0

    # ---- 数据库操作 ----

    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_avg_volume_5min(self, code: str) -> float:
        """获取该股5分钟平均成交量"""
        conn = self._get_conn()
        try:
            # 从 minute_flow_data 取最近5条
            rows = conn.execute(
                "SELECT volume, pct_change, price FROM minute_flow_data "
                "WHERE code=? ORDER BY timestamp DESC LIMIT 5",
                (code,)
            ).fetchall()

            if not rows:
                return 0

            volumes = []
            for r in rows:
                try:
                    v = int(r['volume']) if r['volume'] else 0
                    volumes.append(v)
                except (ValueError, TypeError):
                    continue

            if not volumes:
                return 0
            return sum(volumes) / len(volumes)

        except Exception as e:
            logger.debug(f"[{code}] 获取5分钟均量失败: {e}")
            return 0
        finally:
            conn.close()

    def _get_ma5(self, code: str) -> float:
        """获取5日均线"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT ma5 FROM daily_price WHERE code=? AND ma5 IS NOT NULL ORDER BY date DESC LIMIT 1",
                (code,)
            ).fetchone()
            return row['ma5'] if row and row['ma5'] else 0
        except Exception:
            return 0
        finally:
            conn.close()

    def _update_daily_features(self, code: str, anomaly_result: Dict, llm_result: Dict = None, data: Dict = None):
        """
        更新 daily_features 表的 anomaly 和 llm_analysis 字段。
        如果有 trade_date 则 UPDATE，否则 INSERT 一条新记录。
        """
        conn = self._get_conn()
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            # 检查是否有当天记录
            existing = conn.execute(
                "SELECT id FROM daily_features WHERE code=? AND trade_date=?",
                (code, today)
            ).fetchone()

            anomaly_flag = 1 if anomaly_result else 0
            anomaly_reasons = json.dumps(anomaly_result.get('reasons', []), ensure_ascii=False) if anomaly_result else None
            anomaly_severity = anomaly_result.get('severity', 'none') if anomaly_result else None
            llm_analysis = json.dumps(llm_result, ensure_ascii=False) if llm_result else None

            if existing:
                conn.execute("""
                    UPDATE daily_features SET
                        anomaly_flag=?,
                        anomaly_reasons=?,
                        anomaly_severity=?,
                        llm_analysis=?
                    WHERE code=? AND trade_date=?
                """, (anomaly_flag, anomaly_reasons, anomaly_severity, llm_analysis, code, today))
            else:
                # 插入新行
                conn.execute("""
                    INSERT INTO daily_features
                    (code, trade_date, name, price_close, pct_change,
                     anomaly_flag, anomaly_reasons, anomaly_severity, llm_analysis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    code, today,
                    data.get('name', '') if data else '',
                    data.get('price', 0) if data else 0,
                    data.get('pct_change', 0) if data else 0,
                    anomaly_flag, anomaly_reasons, anomaly_severity, llm_analysis
                ))

            conn.commit()
            logger.info(f"[{code}] daily_features 已更新 (anomaly={anomaly_flag})")

        except Exception as e:
            logger.error(f"[{code}] 更新daily_features失败: {e}")
        finally:
            conn.close()

    # ---- LLM 分析 ----

    def _call_llm(self, prompt: str) -> Optional[Dict]:
        """调用本地LLM"""
        try:
            resp = requests.post(
                LLM_URL,
                json={
                    "model": LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": "你是有经验的量化分析助手。分析结果用JSON格式输出。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.05,
                    "max_tokens": 512,
                },
                timeout=30,
            )

            if resp.status_code != 200:
                return None

            content = resp.json()["choices"][0]["message"]["content"]

            # 提取JSON
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group())

            return None

        except Exception as e:
            logger.warning(f"LLM调用失败: {e}")
            return None

    def _analyze_anomaly(self, code: str, name: str, data: Dict, anomaly: Dict) -> Optional[Dict]:
        """对异动股票进行LLM分析"""
        if not self.enable_llm:
            return None

        prompt = ANOMALY_LLM_PROMPT.format(
            name=name,
            code=code,
            price=data.get('price', 0),
            reasons="; ".join(anomaly.get('reasons', [])),
            pct_change=anomaly.get('details', {}).get('pct_change', 0),
            vol_ratio=anomaly.get('details', {}).get('vol_ratio', 0),
        )

        result = self._call_llm(prompt)
        if result:
            result['analyzed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result['code'] = code
            result['anomaly_reasons'] = anomaly.get('reasons', [])
            self._llm_count += 1

        return result

    # ---- 主入口 ----

    def process(self, code: str, data: Dict) -> Dict:
        """
        处理一次拦截数据：异动检测 + 可选LLM分析

        返回分析结果，可被 _on_data 回调使用
        """
        name = data.get('name', code)

        # 尝试获取名字
        if not name or name == '':
            name = code

        price = data.get('price', 0)
        prev_price = data.get('prev_price', 0)

        # 如果没有 prev_price，从缓存取
        if prev_price == 0 and code in self._cache:
            prev_price = self._cache[code].get('price', 0)

        # 更新缓存
        self._cache[code] = data

        # 获取5分钟平均量
        avg_vol = self._get_avg_volume_5min(code)

        # 获取5日均线
        ma5 = self._get_ma5(code)

        # 获取昨收
        prev_close = data.get('prev_close', 0)

        # 成交量
        volume = 0
        try:
            volume = int(data.get('volume', 0))
        except (ValueError, TypeError):
            volume = 0

        # 执行异动检测
        anomaly = detect_anomaly(
            current_price=price,
            prev_price=prev_price,
            current_volume=volume,
            avg_volume_5min=avg_vol,
            ma5=ma5,
            prev_close=prev_close,
            code=code,
        )

        result = {
            'is_anomaly': anomaly.is_anomaly,
            'reasons': anomaly.reasons,
            'severity': anomaly.severity,
            'details': anomaly.details,
        }

        # LLM分析（仅在异动时）
        llm_result = None
        if anomaly.is_anomaly and self.enable_llm:
            llm_result = self._analyze_anomaly(code, name, data, result)

        # 写入 daily_features
        self._update_daily_features(code, result, llm_result, data)

        if anomaly.is_anomaly:
            self._analysis_count += 1
            logger.info(f"[{code}] 异动检测: {anomaly.severity} - {'; '.join(anomaly.reasons)}")

        return {
            'anomaly': result,
            'llm': llm_result,
        }

    def get_stats(self) -> Dict:
        return {
            'analysis_count': self._analysis_count,
            'llm_count': self._llm_count,
        }

    def close(self):
        """清理"""
        self._cache.clear()


# 便捷函数
def create_integrator(db_path: str = DB_PATH, enable_llm: bool = True) -> AnomalyIntegrator:
    return AnomalyIntegrator(db_path=db_path, enable_llm=enable_llm)
