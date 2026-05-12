# -*- coding: utf-8 -*-
"""
live_runner.py — 实时开盘链路启动器（带日志系统）
整合腾讯实时数据 + Qwen多空分析，每5分钟一轮

日志:
  logs/live_runner_YYYY-MM-DD.log  — 详细运行日志（自动轮转）
  logs/live_predictions.log        — 精简预测记录
  
用法:
  python live_runner.py            # 连续运行（每5分钟一轮）
  python live_runner.py --once     # 只跑一轮
  python live_runner.py --interval 10  # 每10分钟一轮
  python live_runner.py --rounds 6     # 跑6轮后自动退出
  python live_runner.py --daemon       # 后台静默运行（无打印）
"""

import sys, os, time, json, logging, gc, subprocess
from datetime import datetime
from logging.handlers import RotatingFileHandler

# ��e psutil��1%( PowerShell
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from datetime import datetime
from logging.handlers import RotatingFileHandler

# ��e psutil��1%( PowerShell
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from datetime import datetime
from logging.handlers import RotatingFileHandler

sys.path.insert(0, r'E:\csi10')
from realtime_fetcher import build_realtime_snapshot_v2, fetch_realtime
from llm_factors.factor_fusion import get_qwen_bull_bear

BASE_DIR = r'E:\csi10'
LOG_DIR = os.path.join(BASE_DIR, 'logs')
HISTORY_PATH = os.path.join(BASE_DIR, 'live_predictions.json')

# ====== 日志系统 ======

def setup_logging(daemon_mode=False):
    """初始化日志系统"""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 主日志文件（每天滚动，保留7天）
    log_file = os.path.join(LOG_DIR, f'live_runner.log')
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=7, encoding='utf-8')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-5s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    # 根日志器
    logger = logging.getLogger('live_runner')
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加handler
    if not logger.handlers:
        logger.addHandler(handler)
        
        # 控制台输出（daemon模式不打印）
        if not daemon_mode:
            console = logging.StreamHandler()
            console.setFormatter(logging.Formatter('%(message)s'))
            console.setLevel(logging.INFO)
            logger.addHandler(console)
    
    return logger

def get_logger():
    return logging.getLogger('live_runner')

# ====== 核心逻辑 ======

def run_round(round_num, logger=None):
    """执行一轮实时���析"""
    if logger is None:
        logger = get_logger()
    
    t0 = time.time()
    
    # 1. 采集实时数据
    data, scored, indices = build_realtime_snapshot_v2()
    
    if not data or len(data) < 5:
        logger.warning(f"[{round_num}] 数据不足 ({len(data) if data else 0}只)，跳过")
        return None
    
    # 2. 大盘状态
    index_line = ' | '.join([
        f"{v['name'].replace('=','').replace('\"','').split()[-1] if ' ' in str(v['name']) else v['name']} {v['pct']:+.2f}%"
        for v in indices.values()
    ])
    
    top5 = scored[:5]
    bottom3 = scored[-3:]
    
    # 3. 记录第一轮摘要
    if round_num <= 1:
        logger.info(f"{'='*60}")
        logger.info(f"  CSI10 实时链路启动 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}")
    
    logger.info(f"[{round_num:3d}] {index_line}")
    
    # 4. Qwen多空分析（只看最强和最弱各1只）
    qwen_results = []
    
    for label, s in [('强势', top5[0]), ('弱势', bottom3[0])]:
        row_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'close': s['price'],
            'pct_chg': s['pct_change'],
            'ma5': s['price'],
            'ma10': s['price'],
            'ma20': s['price'],
            'rsi6': 50,
            'macd_hist': s['pct_change'] / 10,
            'volume_ratio': 1.0,
            'main_net': 0,
            'k': 50,
            'j': 50,
        }
        
        result = get_qwen_bull_bear(s['code'], s['name'], row_data)
        score = result.get('score', 0)
        bull = result.get('bull', '')[:25]
        bear = result.get('bear', '')[:25]
        
        icon = "🟢" if score > 0 else "🔴"
        logger.info(f"[{round_num:3d}] {icon} {label} {s['name']:<8} {s['price']:>8.2f} {s['pct_change']:>+6.2f}% | 多空{score:>+4d} | ↑{bull} | ↓{bear}")
        
        result['code'] = s['code']
        result['name'] = s['name']
        result['price'] = s['price']
        result['pct_change'] = s['pct_change']
        result['label'] = label
        qwen_results.append(result)
    
    # 5. 打包保存
    elapsed = round(time.time() - t0, 1)
    
    round_result = {
        'round': round_num,
        'time': datetime.now().isoformat(),
        'indices': {k: {'name': v['name'], 'price': v['price'], 'pct': v['pct']} for k, v in indices.items()},
        'top3': [{'code': s['code'], 'name': s['name'], 'price': s['price'], 'pct': s['pct_change'], 'score': s['score']} for s in top5[:3]],
        'bottom3': [{'code': s['code'], 'name': s['name'], 'price': s['price'], 'pct': s['pct_change'], 'score': s['score']} for s in bottom3[:3]],
        'qwen_picks': qwen_results,
        'elapsed': elapsed,
    }
    
    _save_round(round_result)
    
    # 精简日志
    avg_score = sum(s['score'] for s in scored) / len(scored)
    logger.info(f"[{round_num:3d}] ✅ {elapsed:.0f}s | 平均分{avg_score:.0f} | 强势{top5[0]['name']}({top5[0]['pct_change']:+.1f}%) 弱势{bottom3[0]['name']}({bottom3[0]['pct_change']:+.1f}%)")
    
    return round_result


def _save_round(result):
    """追加保存"""
    existing = []
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            existing = []
    
    existing.append(result)
    if len(existing) > 100:
        existing = existing[-100:]
    
    with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def show_summary(logger=None):
    """显示累计统计"""
    if logger is None:
        logger = get_logger()
    
    if not os.path.exists(HISTORY_PATH):
        logger.info("暂无运行记录")
        return
    
    with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if not history:
        return
    
    latest = history[-1]
    
    logger.info(f"\n{'='*60}")
    logger.info(f"  运行统计: {len(history)} 轮 | {latest['time'][:19]}")
    logger.info(f"{'='*60}")
    
    # 统计大盘趋势
    first = history[0]
    for k in latest.get('indices', {}):
        if k in first.get('indices', {}):
            f_v = first['indices'][k]
            l_v = latest['indices'][k]
            change = l_v['pct'] - f_v['pct']
            icon = "↗" if change > 0.1 else "↘" if change < -0.1 else "→"
            name = str(l_v['name']).replace('=','').replace('"','').split()[-1] if ' ' in str(l_v['name']) else l_v['name']
            logger.info(f"  {icon} {name}: 首轮{f_v['pct']:+.2f}% → 最新{l_v['pct']:+.2f}% (变动{change:+.2f}%)")
    
    logger.info(f"  最近Qwen分析:")
    for r in latest.get('qwen_picks', []):
        score = r.get('score', 0)
        icon = "🟢" if score > 0 else "🔴" if score < 0 else "⚪"
        logger.info(f"  {icon} {r['name']}: 多空评分{score} | {r.get('bull','')[:30]}")


def run_continuous(interval_min=5, max_rounds=0, daemon=False):
    """连续运行"""
    logger = setup_logging(daemon_mode=daemon)
    
    logger.info(f"{'#'*60}")
    logger.info(f"  🔄 CSI10 实时链路启动")
    logger.info(f"  间隔: {interval_min}分钟 | 轮数: {'无限' if max_rounds==0 else str(max_rounds)}")
    logger.info(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  PID: {os.getpid()}")
    logger.info(f"{'#'*60}")
    
    round_num = 0
    while True:
        if max_rounds > 0 and round_num >= max_rounds:
            break
        
        try:
        try:
            result = run_round(round_num + 1, logger)
            if result:
                round_num += 1
                
                # :6�6�X
                gc.collect()
                
                # ѧ�X(ŵ
                try:
                    if HAS_PSUTIL:
                        memory_percent = psutil.virtual_memory().percent
                        logger.info(f"  �X(�: {memory_percent}%")
                    else:
                        # ( PowerShell �օX(�
                        mem_result = subprocess.run(
                            ['powershell', '-Command', '(Get-Counter "\Memory\Available MBytes" | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue) / (Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize * 100'],
                            capture_output=True, text=True, timeout=5
                        )
                        if mem_result.returncode == 0:
                            memory_percent = 100 - float(mem_result.stdout.strip())
                            logger.info(f"  �X(�: {memory_percent:.2f}%")
                except Exception as e:
                    logger.warning(f"  �Xѧ1%: {e}")

            logger.info("\n⏹️ 用户中断")
            show_summary(logger)
            break
        except Exception as e:
            logger.error(f"[{round_num+1}] ❌ 错误: {e}", exc_info=True)
        
        if max_rounds == 0 or round_num < max_rounds:
            next_time = datetime.fromtimestamp(time.time() + interval_min * 60).strftime('%H:%M')
            logger.info(f"  ⏳ 等待 {interval_min} 分钟 (下一轮 ≈ {next_time})")
            
            for i in range(interval_min * 60, 0, -1):
                time.sleep(1)
    
    show_summary(logger)
    logger.info("🛑 链路已停止")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='CSI10 实时开盘链路')
    parser.add_argument('--once', action='store_true', help='只跑一轮')
    parser.add_argument('--interval', type=int, default=5, help='间隔分钟数')
    parser.add_argument('--rounds', type=int, default=0, help='运行轮数 (0=无限)')
    parser.add_argument('--daemon', action='store_true', help='后台静默模式')
    args = parser.parse_args()
    
    if args.once:
        logger = setup_logging(daemon_mode=args.daemon)
        run_round(1, logger)
        show_summary(logger)
    else:
        run_continuous(args.interval, args.rounds, args.daemon)
