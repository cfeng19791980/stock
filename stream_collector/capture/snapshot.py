# -*- coding: utf-8 -*-
"""
截图采集模块 - capture/snapshot.py

定时器驱动:按队列顺序,每5秒处理一只股票。
30只股票 × 5秒 = 150秒,每轮约180秒(3分钟)。
排队策略:固定速率,避免给LM Studio造成并发压力。
"""

import time
import logging
from typing import Dict, List, Callable
from datetime import datetime

from stream_collector.browser.manager import BrowserManager

# 截流回退方案:用 data_fetcher.py HTTP 直连腾讯API(比截图+VL更可靠)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

# 全局 DataFetcher 实例(懒加载)
_FETCHER = None
def _get_fetcher():
    global _FETCHER
    if _FETCHER is None:
        _FETCHER = DataFetcher()
    return _FETCHER


class CaptureScheduler:
    """
    数据采集调度器

    核心逻辑:
    - 腾讯股票页面每3秒自动刷新行情,拦截器自动捕获
    - 维护一个股票队列(FIFO),每1-2秒轮询一只股票的拦截buffer
    - 拦截器有数据 → 直接取;无数据 → HTTP请求data_fetcher回退
    - 无需手动刷新页面,无需截图+VL

    优点:
    - 拦截器 Zero-cost:页面自刷新,拦截器静默收集
    - 低延迟:拦截器 buffer 中是最新行情,直接取用
    - 高可靠性:data_fetcher 做安全回退
    """

    def __init__(self,
                 browser: BrowserManager,
                 recognizer=None,
                 interval_seconds: int = 5,   # 每只股票轮询间隔（页面自刷新3秒，5秒轮询足够）
                 max_retry: int = 1,           # 拦截失败直接回退HTTP,不重试
                 on_data: Callable = None):
        """
        Args:
            browser: 浏览器管理器
            recognizer: VL识别器
            interval_seconds: 队列中每只股票的处理间隔(默认5秒)
            max_retry: 失败最大重试次数
            clip_area: 裁剪区域 {"x","y","width","height"}
            on_data: 数据回调函数 on_data(code, data_dict)
        """
        self.browser = browser
        self.recognizer = recognizer
        self.interval_seconds = interval_seconds
        self.max_retry = max_retry
        self.on_data = on_data

        self._is_running = False
        self._queue: List[str] = []         # 股票队列(FIFO)
        self._last_process_time = 0.0       # 上次处理时间
        self._stats = {
            "cycles": 0,
            "captures": 0,
            "recognitions": 0,
            "errors": 0,
            "start_time": None
        }

    def start(self):
        """启动循环调度"""
        self._is_running = True
        self._stats["start_time"] = datetime.now().isoformat()

        # 初始化队列
        self._queue = list(self.browser.stock_codes)

        logger.info(
            "截图调度器启动: %d只股票, 每只间隔%ds, "
            "一轮约%d秒" % (
                len(self._queue),
                self.interval_seconds,
                len(self._queue) * self.interval_seconds
            )
        )

        while self._is_running:
            if not self._queue:
                logger.warning("股票队列为空")
                time.sleep(5)
                continue

            # 控制执行速度:每 interval_seconds 秒处理一只
            now = time.time()
            since_last = now - self._last_process_time
            if since_last < self.interval_seconds:
                wait = self.interval_seconds - since_last
                self._wait_with_cancel(wait)
                if not self._is_running:
                    break

            # 从队首取一只股票
            code = self._queue.pop(0)

            # 处理
            self._process_one(code)

            # 放回队尾
            self._queue.append(code)

            self._last_process_time = time.time()

            # 统计:当队列完整轮完一圈时计为一轮
            self._stats["cycles"] += 1

    def stop(self):
        """停止调度"""
        self._is_running = False
        logger.info("截图调度器已停止")

    def _process_one(self, code: str):
        """处理一只股票：拦截器优先，data_fetcher HTTP回退"""
        logger.debug("处理 [%s]" % code)
        
        try:
            if not self._is_running:
                return
            
            # — 方案A：从拦截器 buffer 直接获取（页面自动刷新，拦截器静默缓存） —
            intercepted = self.browser.fetch_intercepted_data(code)
            
            if intercepted and intercepted.get("status") == "ok" and intercepted.get("data"):
                raw = intercepted["data"]
                
                data = {
                    "_code": code,
                    "_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "_source": "intercept",
                    "name": raw.get("name", ""),
                    "code": code,
                    "price": raw.get("price"),
                    "pct_change": raw.get("pct_change"),
                    "change": raw.get("price_change"),
                    "high": raw.get("high"),
                    "low": raw.get("low"),
                    "open": raw.get("open"),
                    "volume": str(raw.get("volume_hand", "")),
                    "amount": "",
                    "intercept_raw_count": len(intercepted.get("raw_requests", [])),
                }
                
                # 计算涨跌幅（如果没有直接提供）
                if data["pct_change"] is None and data["price"] and raw.get("prev_close"):
                    if raw["prev_close"] > 0:
                        data["pct_change"] = round(
                            (data["price"] - raw["prev_close"]) / raw["prev_close"] * 100, 2
                        )
                
                self._stats["captures"] += 1
                self._stats["recognitions"] += 1
                
                if self.on_data:
                    try:
                        self.on_data(code, data)
                    except Exception as e:
                        logger.error("[%s] 数据回调异常: %s" % (code, e))
                
                logger.info("[%s] 拦截成功 现价=%s %s" % (
                    code, data.get("price", "?"), data.get("pct_change", "")
                ))
                return True
            
            # — 方案B：拦截器没捕获到数据，用 data_fetcher HTTP 直接请求腾讯API —
            logger.debug("[%s] 拦截无数据，回退到HTTP请求" % code)
            try:
                fetcher = _get_fetcher()
                result = fetcher.fetch_from_tencent([code])
                if result and code in result:
                    r = result[code]
                    data = {
                        "_code": code,
                        "_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "_source": "http_fallback",
                        "name": r.get("name", ""),
                        "code": code,
                        "price": r.get("price", 0),
                        "pct_change": r.get("pct_chg", 0),
                        "high": r.get("high", 0),
                        "low": r.get("low", 0),
                        "volume": str(r.get("volume", 0)),
                        "amount": str(r.get("amount", 0)),
                        "intercept_raw_count": 0,
                    }
                    
                    self._stats["captures"] += 1
                    self._stats["recognitions"] += 1
                    
                    if self.on_data:
                        try:
                            self.on_data(code, data)
                        except Exception as e:
                            logger.error("[%s] 数据回调异常: %s" % (code, e))
                    
                    logger.info("[%s] HTTP回退成功 现价=%s %s" % (
                        code, data.get("price", "?"), data.get("pct_change", "")
                    ))
                    return True
                else:
                    logger.warning("[%s] HTTP回退无数据" % code)
            except Exception as e:
                logger.warning("[%s] HTTP回退失败: %s" % (code, e))
            
            # 全部失败
            self._stats["errors"] += 1
            logger.error("[%s] 采集失败（拦截+HTTP回退均无数据）" % code)
            return False
                
        except Exception as e:
            logger.error("[%s] 处理异常: %s" % (code, e))
            self._stats["errors"] += 1
            return False

    def _wait_with_cancel(self, seconds: float):
        """可中断的等待"""
        step = 0.2
        while seconds > 0 and self._is_running:
            time.sleep(min(step, seconds))
            seconds -= step

    def update_queue(self, codes: List[str]):
        """更新股票队列"""
        self._queue = list(codes)
        logger.info("队列更新: %d只股票" % len(codes))

    def get_stats(self) -> Dict:
        s = self._stats
        elapsed = datetime.now() - datetime.fromisoformat(s["start_time"]) if s["start_time"] else 0
        return {
            **s,
            "queue_length": len(self._queue),
            "is_running": self._is_running,
            "interval_seconds": self.interval_seconds,
            "cycle_minutes": round(len(self._queue) * self.interval_seconds / 60, 1)
        }
