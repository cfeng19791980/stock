# -*- coding: utf-8 -*-
"""
消息面抓取器 — news_fetcher.py
每小时抓取一次，LLM 分析情感，结果写入 stocks.db

使用:
    1. 东方财富公告API获取新闻
    2. 本地 LLM (llama-server:1235) 分析情感
    3. 写入 factor_signals 表

调度: start.py 中每小时调用一次
"""

import json
import os
import sys
import time
import sqlite3
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "stocks.db")
CSV_PATH = os.path.join(BASE_DIR, "波段股票Top30.csv")

# LLM 配置 (llama-server)
LLM_URL = "http://127.0.0.1:1235/v1/chat/completions"
LLM_MODEL = "qwen2.5-7b-instruct"

# API 配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}


# ============================================================
# 新闻抓取
# ============================================================

def fetch_news(code: str, name: str = "") -> List[Dict]:
    """
    从东方财富公告API获取股票新闻。
    
    返回: [{'title': '...', 'content': '...', 'date': '...'}, ...]
    """
    # 清理代码格式 (600183.SH -> 000034)
    code_pure = code.split(".")[0]

    try:
        resp = requests.get(
            "https://np-anotice-stock.eastmoney.com/api/security/ann",
            params={
                "sr": -1,
                "page_size": 5,
                "page_index": 1,
                "ann_type": "A",
                "stock_list": code_pure,
                "f_node": 0,
                "s_node": 0,
            },
            headers=HEADERS,
            timeout=10,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        items = data.get("data", {}).get("list", [])
        news = []

        for item in items[:5]:
            news.append({
                "title": item.get("title", ""),
                "date": item.get("notice_date", item.get("date", "")),
                "content": item.get("abstract", item.get("content", "")),
            })

        return news

    except Exception as e:
        logger.debug(f"[{code}] 新闻抓取失败: {e}")
        return []


def fetch_all_news(stock_pool: List[Dict]) -> Dict[str, List[Dict]]:
    """批量抓取所有股票新闻"""
    results = {}
    for stock in stock_pool:
        code = stock.get("code", "")
        name = stock.get("name", code)
        if not code:
            continue
        news = fetch_news(code, name)
        if news:
            results[code] = news
        time.sleep(0.3)  # 控制请求频率
    return results


# ============================================================
# LLM 情感分析
# ============================================================

SYSTEM_PROMPT = """你是A股量化分析师。分析给定股票的新闻公告，输出结构化情感评分。

评分规则:
- sentiment: -1.0 到 1.0 (负面到正面)
- confidence: 0-100 (置信度)
- reason: 一句话分析理由

只输出JSON，不要多余文字。"""


def analyze_news(code: str, name: str, news_list: List[Dict]) -> Optional[Dict]:
    """
    用 LLM 分析新闻情感。
    
    返回: {'sentiment': 0.5, 'confidence': 80, 'reason': '...'}
          或 None (LLM失败时)
    """
    if not news_list:
        return None

    news_text = ""
    for n in news_list:
        title = n.get("title", "")
        content = n.get("content", "")[:100]
        news_text += f"- {title}\n  {content}\n"

    user_prompt = f"""股票: {name}({code})

最新公告:
{news_text}

请分析这些公告对该股票的短期影响，输出JSON评分。"""

    try:
        resp = requests.post(
            LLM_URL,
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.05,
                "max_tokens": 256,
            },
            timeout=30,
        )

        if resp.status_code != 200:
            logger.warning(f"[{code}] LLM返回 {resp.status_code}")
            return None

        content = resp.json()["choices"][0]["message"]["content"]

        # 提取JSON
        import re
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return {
                "sentiment": float(result.get("sentiment", 0)),
                "confidence": int(result.get("confidence", 50)),
                "reason": result.get("reason", ""),
                "raw": content[:200],
            }

        return None

    except Exception as e:
        logger.warning(f"[{code}] LLM分析失败: {e}")
        return None


# ============================================================
# 写入数据库
# ============================================================

def ensure_factor_signals_table(conn: sqlite3.Connection):
    """确保 factor_signals 表存在"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factor_signals (
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            session TEXT DEFAULT 'afternoon',
            news_score REAL DEFAULT 0,
            news_sentiment TEXT,
            fin_score REAL DEFAULT 50,
            fund_score REAL DEFAULT 50,
            llm_confidence REAL DEFAULT 0,
            llm_insight TEXT,
            PRIMARY KEY (code, date, session)
        )
    """)
    conn.commit()


def save_to_db(conn: sqlite3.Connection, code: str, analysis: Dict, today: str, session: str = "afternoon"):
    """将 LLM 分析结果写入 factor_signals 表"""
    sentiment = analysis.get("sentiment", 0)
    confidence = analysis.get("confidence", 50)

    # 情感转分数 (0-100)
    news_score = (sentiment + 1) * 50 if sentiment else 50
    news_score = max(0, min(100, news_score))

    # 构建 insights JSON
    insights = json.dumps({
        "sentiment": sentiment,
        "confidence": confidence,
        "reason": analysis.get("reason", ""),
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }, ensure_ascii=False)

    conn.execute("""
        INSERT OR REPLACE INTO factor_signals
        (code, date, session, news_score, news_sentiment, llm_confidence, llm_insight)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (code, today, session, news_score, insights, confidence, insights))

    conn.commit()


# ============================================================
# 主流程
# ============================================================

def run_news_analysis(stock_pool: List[Dict] = None) -> int:
    """
    主入口: 抓取所有股票新闻 → LLM分析 → 写入DB
    
    返回: 成功分析的股票数
    """
    if stock_pool is None:
        # 从 CSV 加载股票池
        import pandas as pd
        try:
            df = pd.read_csv(CSV_PATH)
            stock_pool = df.to_dict("records")
        except Exception as e:
            logger.error(f"加载股票池失败: {e}")
            # 使用默认测试池
            stock_pool = [
                {"code": "603986.SH", "name": "兆易创新"},
                {"code": "002353.SZ", "name": "杰瑞股份"},
                {"code": "300136.SZ", "name": "信维通信"},
            ]

    today = datetime.now().strftime("%Y-%m-%d")
    session = "afternoon"  # 或 "morning"

    conn = sqlite3.connect(DB_PATH)
    ensure_factor_signals_table(conn)

    # 1. 抓取新闻
    logger.info(f"=== 消息面抓取开始 ({today}) ===")
    all_news = fetch_all_news(stock_pool)
    logger.info(f"获取到 {len(all_news)} 只有新闻的股票")

    # 2. LLM 分析
    success_count = 0
    for code, news_list in all_news.items():
        name = next((s.get("name", code) for s in stock_pool if s.get("code") == code), code)

        logger.info(f"  [{code}] {name}: {len(news_list)}条新闻，LLM分析中...")
        result = analyze_news(code, name, news_list)

        if result:
            save_to_db(conn, code, result, today, session)
            success_count += 1
            logger.info(f"    → 情感:{result['sentiment']:+.2f} 置信度:{result['confidence']}")
        else:
            logger.info(f"    → LLM分析跳过")

        time.sleep(0.5)  # LLM 调用间隔

    conn.close()
    logger.info(f"=== 消息面分析完成: {success_count}/{len(all_news)} ===")
    return success_count


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    count = run_news_analysis()
    print(f"\n✓ 消息面分析完成: {count} 只股票")
