# -*- coding: utf-8 -*-
"""
live_runner.py â å®æ¶å¼çé¾è·¯å¯å¨å¨ï¼å¸¦æ¥å¿ç³»ç»ï¼
æ´åè¾è®¯å®æ¶æ°æ® + Qwenå¤ç©ºåæï¼æ¯5åéä¸è½®

æ¥å¿:
  logs/live_runner_YYYY-MM-DD.log  â è¯¦ç»è¿è¡æ¥å¿ï¼èªå¨è½®è½¬ï¼
  logs/live_predictions.log        â ç²¾ç®é¢æµè®°å½
  
ç¨æ³:
  python live_runner.py            # è¿ç»­è¿è¡ï¼æ¯5åéä¸è½®ï¼
  python live_runner.py --once     # åªè·ä¸è½®
  python live_runner.py --interval 10  # æ¯10åéä¸è½®
  python live_runner.py --rounds 6     # è·6è½®åèªå¨éåº
  python live_runner.py --daemon       # åå°éé»è¿è¡ï¼æ æå°ï¼
"""

import sys, os, time, json, logging, gc, subprocess
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Õüe psutil1%( PowerShell
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Õüe psutil1%( PowerShell
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from datetime import datetime
from logging.handlers import RotatingFileHandler

sys.path.insert(0, r'E:\csi10')
from realtime_fetcher import build_realtime_snapshot_v2, fetch_realtime
from llm_factors.qwen_bull_bear import get_qwen_bull_bear

BASE_DIR = r'E:\csi10'
LOG_DIR = os.path.join(BASE_DIR, 'logs')
HISTORY_PATH = os.path.join(BASE_DIR, 'live_predictions.json')

# ====== æ¥å¿ç³»ç» ======

def setup_logging(daemon_mode=False):
    """åå§åæ¥å¿ç³»ç»"""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # ä¸»æ¥å¿æä»¶ï¼æ¯å¤©æ»å¨ï¼ä¿ç7å¤©ï¼
    log_file = os.path.join(LOG_DIR, f'live_runner.log')
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=7, encoding='utf-8')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-5s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    
    # æ ¹æ¥å¿å¨
    logger = logging.getLogger('live_runner')
    logger.setLevel(logging.DEBUG)
    
    # é¿åéå¤æ·»å handler
    if not logger.handlers:
        logger.addHandler(handler)
        
        # æ§å¶å°è¾åºï¼daemonæ¨¡å¼ä¸æå°ï¼
        if not daemon_mode:
            console = logging.StreamHandler()
            console.setFormatter(logging.Formatter('%(message)s'))
            console.setLevel(logging.INFO)
            logger.addHandler(console)
    
    return logger

def get_logger():
    return logging.getLogger('live_runner')

# ====== æ ¸å¿é»è¾ ======

def run_round(round_num, logger=None):
    """æ§è¡ä¸è½®å®æ¶ï¿½ï¿½ï¿½æ"""
    if logger is None:
        logger = get_logger()
    
    t0 = time.time()
    
    # 1. ééå®æ¶æ°æ®
    data, scored, indices = build_realtime_snapshot_v2()
    
    if not data or len(data) < 5:
        logger.warning(f"[{round_num}] æ°æ®ä¸è¶³ ({len(data) if data else 0}åª)ï¼è·³è¿")
        return None
    
    # 2. å¤§çç¶æ
    index_line = ' | '.join([
        f"{v['name'].replace('=','').replace('\"','').split()[-1] if ' ' in str(v['name']) else v['name']} {v['pct']:+.2f}%"
        for v in indices.values()
    ])
    
    top5 = scored[:5]
    bottom3 = scored[-3:]
    
    # 3. è®°å½ç¬¬ä¸è½®æè¦
    if round_num <= 1:
        logger.info(f"{'='*60}")
        logger.info(f"  CSI10 å®æ¶é¾è·¯å¯å¨ | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}")
    
    logger.info(f"[{round_num:3d}] {index_line}")
    
    # 4. Qwenå¤ç©ºåæï¼åªçæå¼ºåæå¼±å1åªï¼
    qwen_results = []
    
    for label, s in [('å¼ºå¿', top5[0]), ('å¼±å¿', bottom3[0])]:
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
        
        icon = "ð¢" if score > 0 else "ð´"
        logger.info(f"[{round_num:3d}] {icon} {label} {s['name']:<8} {s['price']:>8.2f} {s['pct_change']:>+6.2f}% | å¤ç©º{score:>+4d} | â{bull} | â{bear}")
        
        result['code'] = s['code']
        result['name'] = s['name']
        result['price'] = s['price']
        result['pct_change'] = s['pct_change']
        result['label'] = label
        qwen_results.append(result)
    
    # 5. æåä¿å­
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
    
    # ç²¾ç®æ¥å¿
    avg_score = sum(s['score'] for s in scored) / len(scored)
    logger.info(f"[{round_num:3d}] â {elapsed:.0f}s | å¹³åå{avg_score:.0f} | å¼ºå¿{top5[0]['name']}({top5[0]['pct_change']:+.1f}%) å¼±å¿{bottom3[0]['name']}({bottom3[0]['pct_change']:+.1f}%)")
    
    return round_result


def _save_round(result):
    """è¿½å ä¿å­"""
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
    """æ¾ç¤ºç´¯è®¡ç»è®¡"""
    if logger is None:
        logger = get_logger()
    
    if not os.path.exists(HISTORY_PATH):
        logger.info("ææ è¿è¡è®°å½")
        return
    
    with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if not history:
        return
    
    latest = history[-1]
    
    logger.info(f"\n{'='*60}")
    logger.info(f"  è¿è¡ç»è®¡: {len(history)} è½® | {latest['time'][:19]}")
    logger.info(f"{'='*60}")
    
    # ç»è®¡å¤§çè¶å¿
    first = history[0]
    for k in latest.get('indices', {}):
        if k in first.get('indices', {}):
            f_v = first['indices'][k]
            l_v = latest['indices'][k]
            change = l_v['pct'] - f_v['pct']
            icon = "â" if change > 0.1 else "â" if change < -0.1 else "â"
            name = str(l_v['name']).replace('=','').replace('"','').split()[-1] if ' ' in str(l_v['name']) else l_v['name']
            logger.info(f"  {icon} {name}: é¦è½®{f_v['pct']:+.2f}% â ææ°{l_v['pct']:+.2f}% (åå¨{change:+.2f}%)")
    
    logger.info(f"  æè¿Qwenåæ:")
    for r in latest.get('qwen_picks', []):
        score = r.get('score', 0)
        icon = "ð¢" if score > 0 else "ð´" if score < 0 else "âª"
        logger.info(f"  {icon} {r['name']}: å¤ç©ºè¯å{score} | {r.get('bull','')[:30]}")


def run_continuous(interval_min=5, max_rounds=0, daemon=False):
    """è¿ç»­è¿è¡"""
    logger = setup_logging(daemon_mode=daemon)
    
    logger.info(f"{'#'*60}")
    logger.info(f"  ð CSI10 å®æ¶é¾è·¯å¯å¨")
    logger.info(f"  é´é: {interval_min}åé | è½®æ°: {'æ é' if max_rounds==0 else str(max_rounds)}")
    logger.info(f"  æ¶é´: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  PID: {os.getpid()}")
    logger.info(f"{'#'*60}")
    
    round_num = 0
    while True:
        if max_rounds > 0 and round_num >= max_rounds:
            break
        
        try:
            result = run_round(round_num + 1, logger)
            if result:
                round_num += 1
                
                # X
                gc.collect()
                
                # XÑ§
                try:
                    if HAS_PSUTIL:
                        memory_percent = psutil.virtual_memory().percent
                        logger.info(f"X(: {memory_percent}%")
                    else:
                        # ( PowerShell åâX
                        mem_result = subprocess.run(
                            ['powershell', '-Command', '(Get-Counter "\Memory\Available MBytes" | Select-Object -ExpandProperty CounterSamples | Select-Object -ExpandProperty CookedValue) / (Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize * 100'],
                            capture_output=True, text=True, timeout=5
                        )
                        if mem_result.returncode == 0:
                            memory_percent = 100 - float(mem_result.stdout.strip())
                            logger.info(f"X(: {memory_percent:.2f}%")
                except Exception as e:
                    logger.warning(f"内存监控失败: {e}")
        
        except Exception as e:
            logger.error(f"[{round_num+1}] ❌ 错误: {e}", exc_info=True)
            next_time = datetime.fromtimestamp(time.time() + interval_min * 60).strftime('%H:%M')
            logger.info(f"  â³ ç­å¾ {interval_min} åé (ä¸ä¸è½® â {next_time})")
            
            for i in range(interval_min * 60, 0, -1):
                time.sleep(1)
    
    show_summary(logger)
    logger.info("ð é¾è·¯å·²åæ­¢")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='CSI10 å®æ¶å¼çé¾è·¯')
    parser.add_argument('--once', action='store_true', help='åªè·ä¸è½®')
    parser.add_argument('--interval', type=int, default=5, help='é´éåéæ°')
    parser.add_argument('--rounds', type=int, default=0, help='è¿è¡è½®æ° (0=æ é)')
    parser.add_argument('--daemon', action='store_true', help='åå°éé»æ¨¡å¼')
    args = parser.parse_args()
    
    if args.once:
        logger = setup_logging(daemon_mode=args.daemon)
        run_round(1, logger)
        show_summary(logger)
    else:
        run_continuous(args.interval, args.rounds, args.daemon)
