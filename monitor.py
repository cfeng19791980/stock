# -*- coding: utf-8 -*-
"""
后台监控面板 — monitor.py
终端运行，实时查看系统状态、采集进度、V5评分结果。

核心监控指标：
1. 进程状态（Python/Electron/Chrome）
2. 采集状态（拦截成功/失败/心跳）
3. 数据库概览（数据量/最新时间）
4. V5 评分（推荐买入/卖出）
5. 异常告警（中断/超时）

使用方法：
  python monitor.py
  按 Ctrl+C 退出
"""

import os
import sys
import time
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Optional

BASE_DIR = r'E:\csi10'
DB_PATH = os.path.join(BASE_DIR, 'stocks.db')
RS_V5 = os.path.join(BASE_DIR, 'result_v5.json')
COLLECTOR_LOG = os.path.join(BASE_DIR, 'stream_collector.log')
START_LOG = os.path.join(BASE_DIR, 'start.log')


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def get_process_stats() -> Dict:
    """检查各进程是否在运行"""
    try:
        out = subprocess.run(
            ['tasklist', '/fo', 'csv', '/nh'],
            capture_output=True, text=True, timeout=3
        ).stdout.lower()

        return {
            'python': 'python.exe' in out,
            'electron': 'electron.exe' in out,
            'chrome': 'chrome.exe' in out,
        }
    except Exception:
        return {'error': '?'}


# ── 采集状态监控 ──

_HEARTBEAT_CACHE = {}  # code -> {'time': str, 'source': str}


def get_collector_heartbeat() -> Dict:
    """
    采集心跳监控：读 minute_flow_data 最新记录。
    返回:
      - alive: 是否存活（5分钟内新数据）
      - last_time: 最新数据时间
      - page_age_sec: 距现在多少秒
      - stocks: {code: {time, source}} 各股票最后采集时间
      - count_today: 今日采集总数
      - sources: {source_type: count} 各来源分布
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')

        # 今日拦截总数
        row = conn.execute(
            "SELECT COUNT(*) FROM minute_flow_data WHERE timestamp LIKE ?",
            (today + '%',)
        ).fetchone()
        count_today = row[0] if row else 0

        # 各来源分布（今日）
        sources = {}
        rows = conn.execute(
            "SELECT _source, COUNT(*) as cnt FROM minute_flow_data "
            "WHERE timestamp LIKE ? GROUP BY _source",
            (today + '%',)
        ).fetchall()
        for r in rows:
            sources[r[0]] = r[1]

        # 最新一条记录
        row = conn.execute(
            "SELECT timestamp, _source FROM minute_flow_data ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        last_time = row[0] if row else None
        last_source = row[1] if row else None

        # 各股票最后采集时间（今日）
        stocks = {}
        rows = conn.execute(
            "SELECT code, MAX(timestamp) as last_t, MAX(_source) as src "
            "FROM minute_flow_data WHERE timestamp LIKE ? "
            "GROUP BY code ORDER BY last_t DESC",
            (today + '%',)
        ).fetchall()
        for r in rows:
            stocks[r[0]] = {'time': r[1], 'source': r[2]}

        # 更新心跳缓存
        _HEARTBEAT_CACHE.clear()
        for code, info in stocks.items():
            _HEARTBEAT_CACHE[code] = info

        # 计算距现在秒数
        page_age_sec = -1
        if last_time:
            try:
                last_dt = datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')
                page_age_sec = (now - last_dt).total_seconds()
            except ValueError:
                pass

        alive = page_age_sec >= 0 and page_age_sec < 600  # 10分钟无数据算失联

        conn.close()
        return {
            'alive': alive,
            'last_time': last_time or '无数据',
            'age_sec': page_age_sec,
            'count_today': count_today,
            'sources': sources,
            'stocks': stocks,
        }

    except Exception as e:
        return {'alive': False, 'error': str(e)}


def get_db_stats() -> Dict:
    """数据库核心数据概览"""
    try:
        conn = sqlite3.connect(DB_PATH)
        stats = {}
        today = datetime.now().strftime('%Y-%m-%d')

        # 表行数
        for tbl in ['daily_price', 'daily_features', 'minute_flow_data', 'factor_signals']:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
                stats[tbl] = row[0]
            except Exception:
                stats[tbl] = '?'

        # 最新日线日期
        try:
            row = conn.execute("SELECT MAX(date) FROM daily_price").fetchone()
            stats['last_date'] = row[0]
        except Exception:
            stats['last_date'] = '?'

        # 今日异动数
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM daily_features WHERE trade_date=? AND anomaly_flag=1",
                (today,)
            ).fetchone()
            stats['anomaly_today'] = row[0] if row else 0
        except Exception:
            stats['anomaly_today'] = '?'

        conn.close()
        return stats
    except Exception as e:
        return {'error': str(e)}


def get_v5_result() -> Optional[Dict]:
    """V5 评分摘要 — 基于 advice 字段精准分类"""
    try:
        with open(RS_V5, 'r', encoding='utf-8') as f:
            data = json.load(f)

        stats = data.get('statistics', {})
        stocks = data.get('stocks', [])
        market = data.get('market', {})

        buy_stocks = []
        sell_stocks = []
        watch_stocks = []

        for s in stocks:
            adv = s.get('advice', '')
            name = s.get('name', '?')
            score = s.get('score', 0)
            if '强烈推荐买入' in adv or '推荐买入' in adv or '可考虑买入' in adv:
                buy_stocks.append({'name': name, 'score': score})
            elif '卖出' in adv:
                sell_stocks.append({'name': name, 'score': score})
            elif '观望' in adv:
                watch_stocks.append({'name': name, 'score': score})

        buy_stocks.sort(key=lambda x: -x['score'])
        sell_stocks.sort(key=lambda x: x['score'])

        return {
            'version': data.get('version', '?'),
            'update_time': data.get('update_time', '?'),
            'total': stats.get('total', 0),
            'buy': len(buy_stocks),
            'sell': len(sell_stocks),
            'watch': len(watch_stocks),
            'avg_score': stats.get('avg_score', 0),
            'market_status': market.get('status', '?'),
            'top_buy': buy_stocks[:5],
            'top_sell': sell_stocks[:3],
        }
    except Exception:
        return None


def get_collector_log_last(max_lines: int = 8) -> Optional[list]:
    """读取采集器日志最新行"""
    for logfile in [COLLECTOR_LOG, START_LOG]:
        try:
            if not os.path.exists(logfile):
                continue
            with open(logfile, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            valid = [l for l in lines if any(tag in l for tag in ['[INFO]', '[ERROR]', '[WARNING]'])]
            if valid:
                return valid[-max_lines:]
        except Exception:
            continue
    return None


# ── 面板渲染 ──

def _color(text, color_code):
    """ANSI 颜色"""
    return f"\033[{color_code}m{text}\033[0m"


def print_panel():
    """打印完整监控面板"""
    clear_screen()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print('=' * 58)
    print(f'  股票分析系统 V5   [{now}]')
    print('=' * 58)

    # ── ① 进程状态 ──
    proc = get_process_stats()
    print('\n⚙️  进程状态:')
    if 'error' not in proc:
        print(f'  采集器进程:  {"🟢 Python" if proc["python"] else "⚪ 未启动"}')
        print(f'  界面进程:    {"🟢 Electron" if proc["electron"] else "⚪ 未启动"}')
        print(f'  浏览器进程:  {"🟢 Chrome" if proc["chrome"] else "⚪ 未启动"}')

    # ── ② 采集状态（核心） ──
    hb = get_collector_heartbeat()
    print('\n📡 采集状态:')
    if hb.get('alive'):
        print(f'  状态:        {"🟢 正常采集" if hb["age_sec"] < 300 else "🟡 数据延迟"}')
        age_str = f'{hb["age_sec"]:.0f}s前' if hb['age_sec'] >= 0 else '?'
        print(f'  最新数据:    {hb["last_time"]} ({age_str})')
    else:
        if hb.get('age_sec', -1) >= 0:
            age_min = int(hb['age_sec'] / 60)
            print(f'  状态:        {"🔴 无新数据("+str(age_min)+"min)" if age_min > 10 else "🟡 数据延迟"}')
            print(f'  最新数据:    {hb["last_time"]} ({age_min}分钟前)')
        else:
            print(f'  状态:        ⚪ 未开始采集')

    print(f'  今日采集:    {hb.get("count_today", 0)} 条')

    # 采集来源分布
    sources = hb.get('sources', {})
    if sources:
        parts = []
        for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
            label = {'intercept': '拦截器', 'http_fallback': 'HTTP回退', 'vl_ocr': 'VL识别'}.get(src, src)
            parts.append(f'{label}={cnt}')
        print(f'  来源分布:    {", ".join(parts)}')

    # 各股票最后采集时间
    stocks = hb.get('stocks', {})
    if stocks:
        stale_stocks = []
        now = datetime.now()
        for code, info in stocks.items():
            try:
                t = datetime.strptime(info['time'], '%Y-%m-%d %H:%M:%S')
                age = (now - t).total_seconds()
                if age > 600:  # 10分钟无数据
                    stale_stocks.append(f'{code}({int(age//60)}min)')
            except ValueError:
                stale_stocks.append(code)
        if stale_stocks:
            print(f'  ⚠️  数据延迟: {", ".join(stale_stocks)}')

    # ── ③ 数据库概览 ──
    db = get_db_stats()
    if 'error' not in db:
        print(f'\n🗄️  数据概览:')
        print(f'  日线: {db.get("daily_price", "?")}条 | '
              f'流式: {db.get("minute_flow_data", "?")}条 | '
              f'异动: {db.get("anomaly_today", "?")}只')
        print(f'  最新日期: {db.get("last_date", "?")}')

    # ── ④ V5 评分 ──
    v5 = get_v5_result()
    if v5:
        print(f'\n📈 V5 评分 (v{v5["version"]}):')
        print(f'  更新: {v5["update_time"]}  |  大盘: {v5["market_status"]}')
        print(f'  统计: 共{v5["total"]}只  🟢买入{v5["buy"]}  🔴卖出{v5["sell"]}  ⚪观望{v5["watch"]}')

        if v5['top_buy']:
            print(f'  🟢 推荐买入:')
            for s in v5['top_buy']:
                print(f'    {s["name"]:12s}  评分 {s["score"]}')
        if v5['top_sell']:
            print(f'  🔴 建议卖出:')
            for s in v5['top_sell']:
                print(f'    {s["name"]:12s}  评分 {s["score"]}')

    # ── ⑤ 最近日志 ──
    logs = get_collector_log_last(6)
    if logs:
        print(f'\n📋 最近日志:')
        for line in logs:
            line = line.strip()
            if '[ERROR]' in line:
                icon = '❌'
            elif '[WARNING]' in line:
                icon = '⚠️'
            else:
                icon = ''
            print(f'  {icon} {line[:90]}')

    print(f'\n{"-" * 50}')
    print('3秒自动刷新 | Ctrl+C 退出')


def main():
    try:
        while True:
            print_panel()
            time.sleep(3)
    except KeyboardInterrupt:
        clear_screen()
        print('\n监控已退出。')
        print('再次查看: python monitor.py')


if __name__ == '__main__':
    main()
