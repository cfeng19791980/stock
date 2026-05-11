# -*- coding: utf-8 -*-
"""
采集器看门狗 - watchdog_cron.py

每5分钟由 cron 调用一次，监测流式数据采集器是否正常运行。
如果失联则自动重启；如果数据异常则 Windows 弹窗告警。

Cron 配置:
  频率: 每5分钟
  命令: cd E:/csi10 && python watchdog_cron.py

检查逻辑:
  1. 是否在交易时间 (9:30-15:00 工作日)
  2. start_collector.py 进程是否在运行
  3. minute_flow_data 表最近10分钟是否有新数据
  4. 连续三轮空数据 -> 异常告警

告警方式:
  - Windows toast 弹窗 (PowerShell popup)
  - 同时写入 watchdog.log
"""

import os
import sys
import json
import time
import sqlite3
import subprocess
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchdog.log"),
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

BASE_DIR = r"E:\csi10"
DB_PATH = os.path.join(BASE_DIR, "stocks.db")

# ============================================================
# 状态文件（用于跨轮次检测连续异常）
# ============================================================
STATE_FILE = os.path.join(BASE_DIR, ".watchdog_state.json")


def load_state():
    """读取看门狗持久化状态"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "consecutive_empty": 0,   # 连续空数据轮次
        "last_alert_time": "",    # 最后一次告警时间
        "last_restart_time": "",  # 最后一次重启时间
        "restart_count": 0,       # 当日重启次数
        "date": "",               # 记录日期
    }


def save_state(state):
    """保存看门狗持久化状态"""
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("date") != today:
        state["date"] = today
        state["restart_count"] = 0
        state["consecutive_empty"] = 0
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存状态失败: {e}")


# ============================================================
# 1. 交易时间判断
# ============================================================

def is_trading_time() -> bool:
    """是否在交易时间：9:30-12:00(上午) 13:00-15:00(下午)，工作日"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    hour = now.hour
    minute = now.minute
    # 9:30 - 12:00 上午交易
    if hour == 9 and minute >= 30:
        return True
    if 10 <= hour <= 11:
        return True
    # 12:00-13:00 午休
    # 13:00 - 15:00 下午交易
    if 13 <= hour <= 14:
        return True
    return False


# ============================================================
# 2. 进程检查
# ============================================================

def check_collector_process() -> dict:
    """
    检查 start_collector.py 和 Python 进程状态。
    
    Returns:
        {'running': bool, 'pids': [int], 'detail': str}
    """
    try:
        out = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            capture_output=True, text=True, timeout=5
        ).stdout.lower()

        # 找 python.exe 进程
        python_pids = []
        for line in out.splitlines():
            if "python.exe" in line:
                parts = line.split(",")
                if len(parts) > 1:
                    pid = parts[1].strip('"')
                    python_pids.append(pid)

        # 检查是否有 start_collector 或 stream_collector 在命令行参数中
        has_collector = False
        if python_pids:
            for pid in python_pids:
                try:
                    cmdline = subprocess.run(
                        ["tasklist", "/fi", f"PID eq {pid}", "/fo", "csv", "/nh"],
                        capture_output=True, text=True, timeout=2
                    ).stdout.lower()
                    if "start_collector" in cmdline or "stream_collector" in cmdline:
                        has_collector = True
                        break
                except Exception:
                    pass

        # 二次验证：用 wmic（更准确）
        if not has_collector:
            try:
                wmic_out = subprocess.run(
                    ["wmic", "process", "where", "name='python.exe'", "get", "commandline"],
                    capture_output=True, text=True, timeout=5
                ).stdout.lower()
                has_collector = "start_collector" in wmic_out or "stream_collector" in wmic_out
            except Exception:
                pass

        return {
            "running": has_collector,
            "pids": python_pids,
            "detail": "运行中" if has_collector else "未运行",
        }

    except Exception as e:
        return {"running": False, "pids": [], "detail": f"检查失败: {e}"}


# ============================================================
# 3. 数据库心跳检查
# ============================================================

def check_db_heartbeat() -> dict:
    """
    检查 minute_flow_data 表的数据心跳。
    
    Returns:
        {
            'has_data': bool,           # 过去10分钟是否有新数据
            'last_time': str,           # 最新数据时间
            'age_sec': int,             # 距现在秒数
            'count_10min': int,         # 过去10分钟数据条数
            'stocks_alive': [str],      # 活跃股票列表
            'error': str | None
        }
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        now = datetime.now()
        threshold = (now - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")

        # 过去10分钟的数据条数
        row = conn.execute(
            "SELECT COUNT(*) FROM minute_flow_data WHERE timestamp >= ?",
            (threshold,)
        ).fetchone()
        count_10min = row[0] if row else 0

        # 最新一条数据
        row = conn.execute(
            "SELECT MAX(timestamp) FROM minute_flow_data"
        ).fetchone()
        last_time = row[0] if row else None

        age_sec = -1
        if last_time:
            try:
                last_dt = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
                age_sec = (now - last_dt).total_seconds()
            except ValueError:
                pass

        # 过去10分钟有数据的股票
        stocks_alive = []
        if count_10min > 0:
            rows = conn.execute(
                "SELECT DISTINCT code FROM minute_flow_data WHERE timestamp >= ?",
                (threshold,)
            ).fetchall()
            stocks_alive = [r[0] for r in rows]

        conn.close()

        return {
            "has_data": count_10min > 0 and age_sec is not None and age_sec < 600,
            "last_time": last_time or "无数据",
            "age_sec": age_sec,
            "count_10min": count_10min,
            "stocks_alive": stocks_alive,
        }

    except Exception as e:
        return {
            "has_data": False,
            "last_time": "检查失败",
            "age_sec": -1,
            "count_10min": 0,
            "stocks_alive": [],
            "error": str(e),
        }


# ============================================================
# 4. 重启采集器
# ============================================================

def start_collector() -> bool:
    """
    启动采集器（start_collector.py）。
    使用 subprocess.Popen 新开窗口，不阻塞。
    
    Returns:
        True 表示启动成功（或已存在不重复启动）
    """
    try:
        # 先检查是否已经在运行
        proc_check = check_collector_process()
        if proc_check["running"]:
            logger.info("采集器已在运行，跳过启动")
            return True

        # 启动新的采集进程（新开窗口）
        script = os.path.join(BASE_DIR, "start_collector.py")
        subprocess.Popen(
            ["python", script],
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            shell=True,
        )
        logger.info("采集器已启动（新窗口）")
        return True

    except Exception as e:
        logger.error(f"启动采集器失败: {e}")
        return False


# ============================================================
# 5. Windows 弹窗告警
# ============================================================

def show_windows_alert(title: str, message: str):
    """
    Windows 原生弹窗告警。
    使用 PowerShell popup（无需第三方库）。
    """
    try:
        ps_script = f'''
        [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null
        [System.Windows.Forms.MessageBox]::Show("{message}", "{title}", 
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning)
        '''
        subprocess.Popen(
            ["powershell", "-Command", ps_script],
            shell=True,
        )
        logger.info(f"Windows 弹窗: {title} - {message}")
    except Exception as e:
        logger.warning(f"Windows 弹窗失败: {e}")


# ============================================================
# 主逻辑
# ============================================================

def main():
    logger.info("=== 看门狗检查开始 ===")

    if not is_trading_time():
        logger.info("非交易时间，跳过检查")
        return

    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("date") != today:
        state["date"] = today
        state["restart_count"] = 0
        state["consecutive_empty"] = 0

    # 1. 检查进程
    proc = check_collector_process()
    logger.info(f"进程状态: {proc['detail']}")

    # 2. 检查数据库心跳
    hb = check_db_heartbeat()
    logger.info(f"数据心跳: has_data={hb['has_data']}, "
                f"last={hb['last_time']}, "
                f"10min_count={hb['count_10min']}")

    # 决策逻辑
    alerts = []

    if not proc["running"]:
        # 采集器挂了 → 自动重启
        if state["restart_count"] < 3:  # 每天最多重启3次，防止死循环
            logger.warning("采集器未运行，准备重启...")
            ok = start_collector()
            if ok:
                state["last_restart_time"] = datetime.now().strftime("%H:%M:%S")
                state["restart_count"] += 1
                alerts.append(("🔄 采集器重启", f"采集器于{state['last_restart_time']}自动重启"))
            else:
                alerts.append(("❌ 重启失败", "采集器进程未运行且自动重启失败，请手动检查"))
        else:
            alerts.append(("❌ 重启超限", f"今日已重启{state['restart_count']}次，请手动检查"))

    elif not hb["has_data"]:
        # 进程在跑但没数据
        state["consecutive_empty"] += 1
        if state["consecutive_empty"] >= 3:
            # 连续三轮（15分钟）都没数据 → 严重告警
            alerts.append((
                "⚠️ 数据采集异常",
                f"采集器运行中但已{state['consecutive_empty']}轮无新数据"
                f"（最后数据: {hb.get('last_time', '无')}）\n"
                f"建议检查: 网络/浏览器/拦截器"
            ))
            state["consecutive_empty"] = 0  # 告警后重置
    else:
        # 正常运行
        state["consecutive_empty"] = 0

    # 发送告警
    now_str = datetime.now().strftime("%H:%M:%S")
    for title, msg in alerts:
        show_windows_alert(title, msg)
        logger.warning(f"告警: {title} - {msg}")
        state["last_alert_time"] = now_str

    # 保存状态
    save_state(state)

    logger.info(f"=== 看门狗检查结束 (alerts={len(alerts)}) ===")

    # 如果有告警，打印到 stdout 和哨兵可以捕获
    if alerts:
        print(json.dumps({
            "watchdog": "alert",
            "alerts": [{"title": a[0], "message": a[1]} for a in alerts],
            "time": now_str,
        }, ensure_ascii=False))
        return  # 非0退出码可被 cron 捕获为失败
    else:
        print(json.dumps({"watchdog": "ok", "time": now_str}))
        return


if __name__ == "__main__":
    main()
