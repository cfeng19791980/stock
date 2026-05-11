# -*- coding: utf-8 -*-
"""
流式数据采集系统 — 主调度器

启动流程：
1. 启动浏览器管理器 → 打开所有个股页面
2. 启动截图调度器 → 循环截图→VL识别→入库
3. 支持优雅退出（Ctrl+C）
"""

import os
import sys
import json
import time
import logging
import signal
from typing import List, Dict
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from stream_collector.browser.manager import BrowserManager
from stream_collector.vision.parser import VLRecognizer
from stream_collector.capture.snapshot import CaptureScheduler
from stream_collector.storage.writer import DataWriter
from stream_collector.analysis.anomaly_integrator import AnomalyIntegrator

logger = logging.getLogger(__name__)


class StreamCollector:
    """流式数据采集系统主控制器"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self._is_running = False
        
        # 组件
        self.browser: BrowserManager = None
        self.recognizer: VLRecognizer = None
        self.scheduler: CaptureScheduler = None
        self.writer: DataWriter = None
        self.anomaly: AnomalyIntegrator = None
        self._enable_anomaly = True
        
        # 统计
        self._start_time = None
        self._stats = {
            "written": 0,
            "write_fail": 0
        }
    
    def _load_config(self, path: str = None) -> Dict:
        """加载配置"""
        if not path:
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "config", "config.json"
            )
        
        default = {
            "stock_pool": ["603986.SH", "002353.SZ", "300136.SZ", "300476.SZ"],
            "collector": {
                "interval_seconds": 6,
                "max_retry": 3
            },
            "browser": {
                "headless": False,
                "page_timeout": 30000
            },
            "vision": {
                "model": "qwen3-vl-4b-instruct",
                "temperature": 0.05
            },
            "storage": {
                "db_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stocks.db"),
                "table_name": "minute_flow_data",
                "keep_days": 30
            },
            "log": {
                "level": "INFO",
                "file": "stream_collector.log"
            }
        }
        
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # 合并（只覆盖已有键）
                self._deep_merge(default, loaded)
                logger.info(f"配置已加载: {path}")
        else:
            logger.warning(f"配置文件不存在，使用默认配置: {path}")
        
        return default
    
    def _deep_merge(self, base: Dict, override: Dict):
        """递归合并字典"""
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v
    
    def _is_trading_time(self) -> bool:
        """判断当前是否为交易时间（9:30-15:00，周一到周五）"""
        now = datetime.now()
        # 周末不交易
        if now.weekday() >= 5:
            return False
        # 交易时间 9:30 - 15:00
        hour = now.hour
        minute = now.minute
        if hour < 9 or hour >= 15:
            return False
        if hour == 9 and minute < 30:
            return False
        return True
    
    def start(self, headless: bool = False, use_intercept: bool = True):
        """启动系统"""
        if self._is_running:
            logger.warning("系统已在运行中")
            return
        
        # 检查交易时间
        if not self._is_trading_time():
            logger.info("当前非交易时间（需 9:30-15:00 周一至周五），系统等待中...")
            # 等到下一个交易日
            self._wait_for_trading_time()
        
        self._start_time = datetime.now()
        self._is_running = True
        
        cfg = self.config
        
        try:
            # 1. 初始化数据库
            logger.info("=== 初始化数据库 ===")
            self.writer = DataWriter(
                db_path=cfg["storage"]["db_path"],
                table_name=cfg["storage"]["table_name"],
                keep_days=cfg["storage"]["keep_days"]
            )
            
            # 2. 启动浏览器
            mode_str = "拦截模式" if use_intercept else "截图+VL模式"
            logger.info(f"=== 启动浏览器 ({mode_str}) ===")
            self.browser = BrowserManager(headless=headless).start()
            
            # 解析股票代码
            codes = []
            for item in cfg["stock_pool"]:
                code = item.split(".")[0]
                codes.append(code)
            
            # 打开所有股票标签页
            logger.info(f"=== 打开 {len(codes)} 只股票标签页 ===")
            for code in codes:
                exchange = "sh" if code.startswith("6") or code.startswith("9") else "sz"
                self.browser.add_stock(code, exchange)
            
            # 3. 初始化VL识别器
            if not use_intercept:
                logger.info("=== 初始化VL识别器 ===")
            else:
                logger.info("=== VL识别器已启用（作拦截回退方案） ===")
            self.recognizer = VLRecognizer(
                model=cfg["vision"]["model"]
            )
            
            # 4. 初始化异动集成器
            self.anomaly = AnomalyIntegrator(db_path=cfg["storage"]["db_path"]) if self._enable_anomaly else None
            if self.anomaly:
                logger.info("=== 异动检测已启用 ===")
            
            # 5. 启动调度器
            collector_cfg = cfg["collector"]
            self.scheduler = CaptureScheduler(
                browser=self.browser,
                recognizer=self.recognizer,
                interval_seconds=collector_cfg["interval_seconds"],
                max_retry=collector_cfg["max_retry"],
                on_data=self._on_data
            )
            # 注册信号处理
            self._register_signal_handlers()
            
            # 启动（阻塞）
            self.scheduler.start()
            
        except KeyboardInterrupt:
            logger.info("接收到中断信号")
        except Exception as e:
            logger.error(f"系统异常: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """停止系统"""
        logger.info("=== 停止系统 ===")
        
        if self.scheduler:
            try:
                self.scheduler.stop()
            except:
                pass
        
        if self.browser:
            try:
                self.browser.stop()
            except:
                pass
        
        if self.writer:
            try:
                self.writer.cleanup()
                self.writer.close()
            except:
                pass
        
        self._is_running = False
        
        # 打印统计
        elapsed = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
        logger.info(f"运行时长: {elapsed:.0f}s")
        logger.info(f"统计: {self._stats}")
        
        if self.recognizer:
            logger.info(f"VL识别统计: {self.recognizer.get_stats()}")
    
    def _on_data(self, code: str, data: Dict):
        """数据回调：写入数据库 + 异动检测"""
        row_id = self.writer.write(code, data)
        if row_id > 0:
            self._stats["written"] += 1
        else:
            self._stats["write_fail"] += 1
        
        # 异动检测
        if self.anomaly:
            try:
                result = self.anomaly.process(code, data)
            except Exception as e:
                logger.error(f"异动检测异常 [{code}]: {e}")
    
    def _wait_for_trading_time(self):
        """等到下一个交易时间的 9:30"""
        while self._is_running:
            if self._is_trading_time():
                logger.info("已到交易时间，启动采集...")
                return
            # 每 60 秒检查一次
            time.sleep(60)
    
    def _register_signal_handlers(self):
        """注册信号处理"""
        def handler(signum, frame):
            logger.info(f"收到信号 {signum}")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)


def main():
    """入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="流式数据采集系统")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--no-intercept", action="store_true", help="禁用拦截模式，回退到截图+VL识别")
    parser.add_argument("--log-level", default="INFO", help="日志级别")
    parser.add_argument("--log-file", default=None, help="日志文件路径")
    args = parser.parse_args()
    
    # 配置日志
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    
    if args.log_file:
        logging.basicConfig(
            level=log_level,
            format=log_format,
            filename=args.log_file,
            encoding="utf-8"
        )
    else:
        logging.basicConfig(
            level=log_level,
            format=log_format,
            encoding="utf-8"
        )
    
    # 启动
    collector = StreamCollector(config_path=args.config)
    collector.start(headless=args.headless, use_intercept=not args.no_intercept)


if __name__ == "__main__":
    main()
