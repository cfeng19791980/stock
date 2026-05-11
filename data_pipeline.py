# -*- coding: utf-8 -*-
"""
数据管线 — data_pipeline.py

第一阶段数据层改造核心模块。
功能：
1. 资金流向采集（AkShare）→ 写入 fund_flow 表 + daily_price
2. 前复权处理 → 写入 daily_price.adjust_factor
3. 滚动标准化（60日窗口）→ 更新 daily_price 标准化字段
4. 一键更新全部数据

用法：
    from data_pipeline import DataPipeline
    dp = DataPipeline()
    dp.update_all()          # 一键更新所有数据
    dp.collect_fund_flow()   # 仅更新资金流向
    dp.calc_rolling_norm()   # 仅计算滚动标准化
"""

import os
import sys
import time
import json
import sqlite3
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 尝试导入 akshare
try:
    import akshare as ak
    AK_AVAILABLE = True
except ImportError:
    AK_AVAILABLE = False
    logger.warning("akshare 未安装。安装: pip install akshare")


BASE_DIR = r'E:\csi10'
DB_PATH = os.path.join(BASE_DIR, 'stocks.db')


class DataPipeline:
    """
    数据层核心管线。
    管理日线数据、资金流向、复权处理、滚动标准化。

    线程安全：否（每天跑一次即可，不并行）
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._code_to_market = {}  # 缓存代码→市场映射

    # ── 数据库连接 ──

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    # ── 股票池 ──

    def get_stock_pool(self) -> List[str]:
        """获取股票池列表（含.SH/.SZ后缀）"""
        import pandas as pd
        csv_path = os.path.join(BASE_DIR, '波段股票Top30.csv')
        try:
            df = pd.read_csv(csv_path)
            return df['股票代码'].tolist()
        except Exception as e:
            logger.error(f"读取股票池失败: {e}")
            return []

    def _to_ak_code(self, code: str) -> tuple:
        """将 '600183.SH' 转为 (market, symbol) 如 ('sh', '600183')"""
        parts = code.split('.')
        symbol = parts[0]
        market = 'sh' if len(parts) > 1 and parts[1].upper() == 'SH' else 'sz'
        return market, symbol

    # ════════════════════════════════════════
    # 1. 资金流向采集
    # ════════════════════════════════════════

    def collect_fund_flow(self, codes: List[str] = None, 
                          start_date: str = None,
                          end_date: str = None) -> Dict:
        """
        采集个股资金流向数据，写入 fund_flow 表和 daily_price 表。
        
        Args:
            codes: 股票代码列表，默认从股票池读取
            start_date: 起始日期 YYYYMMDD，默认30天前
            end_date: 截止日期，默认今天
        
        Returns:
            {'total': N, 'success': N, 'fail': N, 'errors': [...]}
        """
        if not AK_AVAILABLE:
            logger.error("akshare 不可用，无法采集资金流向")
            return {'total': 0, 'success': 0, 'fail': 0, 'errors': ['akshare not installed']}

        if codes is None:
            codes = self.get_stock_pool()

        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start = datetime.now() - timedelta(days=30)
            start_date = start.strftime('%Y%m%d')

        result = {'total': len(codes), 'success': 0, 'fail': 0, 'errors': []}
        conn = self._get_conn()

        for code in codes:
            try:
                market, symbol = self._to_ak_code(code)
                df = ak.stock_individual_fund_flow(stock=symbol, market=market)

                if df is None or df.empty:
                    result['fail'] += 1
                    continue

                # 筛选日期范围（AkShare 返回的日期是 datetime.date 类型）
                if start_date:
                    from datetime import date
                    sd = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
                    df = df[df['日期'] >= sd]
                if end_date:
                    from datetime import date
                    ed = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
                    df = df[df['日期'] <= ed]

                if df.empty:
                    result['fail'] += 1
                    continue

                # 写入 fund_flow 表
                rows = []
                for _, row in df.iterrows():
                    date_val = row['日期']
                    # AkShare 返回 datetime.date，转字符串
                    if hasattr(date_val, 'strftime'):
                        date = date_val.strftime('%Y-%m-%d')
                    else:
                        date = str(date_val)
                    close = self._safe_float(row.get('收盘价'))
                    pct_chg = self._safe_float(row.get('涨跌幅'))
                    main_net = self._safe_float(row.get('主力净流入-净额'))
                    main_pct = self._safe_float(row.get('主力净流入-净占比'))
                    super_net = self._safe_float(row.get('超大单净流入-净额'))
                    super_pct = self._safe_float(row.get('超大单净流入-净占比'))
                    big_net = self._safe_float(row.get('大单净流入-净额'))
                    big_pct = self._safe_float(row.get('大单净流入-净占比'))
                    med_net = self._safe_float(row.get('中单净流入-净额'))
                    med_pct = self._safe_float(row.get('中单净流入-净占比'))
                    small_net = self._safe_float(row.get('小单净流入-净额'))
                    small_pct = self._safe_float(row.get('小单净流入-净占比'))

                    rows.append((code, date, main_net, main_pct,
                                 super_net, super_pct, big_net, big_pct,
                                 med_net, med_pct, small_net, small_pct,
                                 None, close, pct_chg))

                conn.executemany("""
                    INSERT OR REPLACE INTO fund_flow
                    (code, date, main_net, main_pct,
                     super_large_net, super_large_pct,
                     big_net, big_pct,
                     medium_net, medium_pct,
                     small_net, small_pct,
                     north_net, close, pct_chg)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, rows)

                # 同步最近一期到 daily_price
                if rows:
                    latest = rows[-1]
                    conn.execute("""
                        UPDATE daily_price SET
                            main_net = ?,
                            main_net_pct = ?
                        WHERE code = ? AND date = ?
                    """, (latest[2], latest[3], code, latest[1]))

                conn.commit()
                result['success'] += 1
                logger.info(f"[{code}] 资金流向: {len(rows)}条")

            except Exception as e:
                conn.rollback()
                result['fail'] += 1
                result['errors'].append(f"{code}: {e}")
                logger.warning(f"[{code}] 资金流向采集失败: {e}")

        conn.close()
        logger.info(f"资金流向采集完成: 成功{result['success']}/{result['total']}")
        return result

    # ════════════════════════════════════════
    # 2. 前复权处理
    # ════════════════════════════════════════

    def calc_adjust_factor(self, codes: List[str] = None) -> Dict:
        """
        计算复权因子（前复权）。
        用 AkShare 的 qfq 参数获取复权数据，计算 adjust_factor。
        
        策略：用复权价/实际价的比例作为复权因子
        """
        if not AK_AVAILABLE:
            return {'total': 0, 'success': 0, 'errors': ['akshare not installed']}

        if codes is None:
            codes = self.get_stock_pool()

        result = {'total': len(codes), 'success': 0, 'fail': 0, 'errors': []}
        conn = self._get_conn()

        for code in codes:
            try:
                market, symbol = self._to_ak_code(code)
                
                # 获取前复权数据
                df_qfq = ak.stock_zh_a_hist(
                    symbol=symbol, period="daily",
                    start_date="20240101",
                    end_date=datetime.now().strftime("%Y%m%d"),
                    adjust="qfq"
                )
                if df_qfq is None or df_qfq.empty:
                    result['fail'] += 1
                    continue

                # 获取不复权数据
                df_raw = ak.stock_zh_a_hist(
                    symbol=symbol, period="daily",
                    start_date="20240101",
                    end_date=datetime.now().strftime("%Y%m%d"),
                    adjust=""
                )
                if df_raw is None or df_raw.empty:
                    result['fail'] += 1
                    continue

                # 合并，计算复权因子
                df_qfq['日期'] = pd.to_datetime(df_qfq['日期']).dt.strftime('%Y-%m-%d')
                df_raw['日期'] = pd.to_datetime(df_raw['日期']).dt.strftime('%Y-%m-%d')

                merged = pd.merge(
                    df_qfq[['日期', '收盘']].rename(columns={'收盘': 'close_qfq'}),
                    df_raw[['日期', '收盘']].rename(columns={'收盘': 'close_raw'}),
                    on='日期', how='inner'
                )

                for _, row in merged.iterrows():
                    date = row['日期']
                    if row['close_raw'] > 0:
                        factor = row['close_qfq'] / row['close_raw']
                        conn.execute("""
                            UPDATE daily_price SET adjust_factor = ?
                            WHERE code = ? AND date = ?
                        """, (round(factor, 6), code, date))

                conn.commit()
                result['success'] += 1
                logger.info(f"[{code}] 前复权处理: {len(merged)}条")

            except Exception as e:
                result['fail'] += 1
                result['errors'].append(f"{code}: {e}")
                logger.warning(f"[{code}] 前复权失败: {e}")

        conn.close()
        return result

    # ════════════════════════════════════════
    # 3. 滚动标准化
    # ════════════════════════════════════════

    def calc_rolling_norm(self, codes: List[str] = None, window: int = 60) -> Dict:
        """
        滚动标准化：用近 window 个交易日的均值、标准差对量价指标做归一化。
        
        标准化的字段：volume, amount, pct_chg, turnover, amplitude, main_net
        标准化后的新字段存储为：{field}_zscore
        
        用法：dp.calc_rolling_norm()  # 默认 60 日窗口
        """
        if codes is None:
            codes = self.get_stock_pool()

        result = {'total': len(codes), 'success': 0, 'errors': []}
        conn = self._get_conn()

        for code in codes:
            try:
                # 获取该股票所有日线数据（按日期排序）
                rows = conn.execute("""
                    SELECT date, volume, amount, pct_chg, turnover, amplitude, main_net
                    FROM daily_price
                    WHERE code = ? AND volume > 0
                    ORDER BY date ASC
                """, (code,)).fetchall()

                if len(rows) < window:
                    result['success'] += 1
                    continue

                # 转 DataFame 计算 Z-score
                dates = [r[0] for r in rows]
                fields = {
                    'volume': [r[1] or 0 for r in rows],
                    'amount': [r[2] or 0 for r in rows],
                    'pct_chg': [r[3] or 0 for r in rows],
                    'turnover': [r[4] or 0 for r in rows],
                    'amplitude': [r[5] or 0 for r in rows],
                    'main_net': [r[6] or 0 for r in rows],
                }

                df = pd.DataFrame(fields, index=dates)
                
                # 滚动标准化
                rolling_mean = df.rolling(window=window, min_periods=window).mean()
                rolling_std = df.rolling(window=window, min_periods=window).std().replace(0, np.nan)
                df_z = (df - rolling_mean) / rolling_std

                # 写入数据库
                for i, date in enumerate(dates):
                    updates = {}
                    for field in fields.keys():
                        val = df_z.iloc[i].get(field)
                        if pd.notna(val) and np.isfinite(val):
                            updates[f'{field}_zscore'] = round(val, 4)

                    if updates:
                        set_clause = ', '.join(f"{k}=?" for k in updates)
                        values = list(updates.values()) + [code, date]
                        conn.execute(
                            f"UPDATE daily_price SET {set_clause} WHERE code=? AND date=?",
                            values
                        )

                conn.commit()
                result['success'] += 1

            except Exception as e:
                result['errors'].append(f"{code}: {e}")
                logger.warning(f"[{code}] 滚动标准化失败: {e}")

        conn.close()
        logger.info(f"滚动标准化完成: {result['success']}/{result['total']}")
        return result

    # ════════════════════════════════════════
    # 4. 一键更新
    # ════════════════════════════════════════

    def update_all(self, codes: List[str] = None,
                   collect_fund_flow: bool = True,
                   calc_adjust: bool = True,
                   calc_norm: bool = True) -> Dict:
        """
        一键更新全部数据管线。
        
        Args:
            codes: 股票代码列表
            collect_fund_flow: 是否采集资金流向
            calc_adjust: 是否计算复权因子
            calc_norm: 是否计算滚动标准化
        
        Returns:
            {'fund_flow': {...}, 'adjust': {...}, 'norm': {...}}
        """
        report = {}
        t0 = time.time()

        if codes is None:
            codes = self.get_stock_pool()

        logger.info(f"=== 数据管线更新开始: {len(codes)}只股票 ===")

        if collect_fund_flow:
            logger.info("--- Step 1/3: 资金流向 ---")
            report['fund_flow'] = self.collect_fund_flow(codes)

        if calc_adjust:
            logger.info("--- Step 2/3: 前复权 ---")
            report['adjust'] = self.calc_adjust_factor(codes)

        if calc_norm:
            logger.info("--- Step 3/3: 滚动标准化 ---")
            report['norm'] = self.calc_rolling_norm(codes)

        elapsed = time.time() - t0
        logger.info(f"=== 数据管线更新完成 ({elapsed:.1f}s) ===")
        return report

    # ── 工具函数 ──

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        if val is None:
            return None
        try:
            v = float(val)
            return None if np.isnan(v) or np.isinf(v) else v
        except (ValueError, TypeError):
            return None


# ── 便捷入口 ──

def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description='CSI10 数据管线')
    parser.add_argument('--fund-flow', action='store_true', help='仅采集资金流向')
    parser.add_argument('--adjust', action='store_true', help='仅计算前复权')
    parser.add_argument('--norm', action='store_true', help='仅计算滚动标准化')
    parser.add_argument('--all', action='store_true', help='一键更新全部')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    dp = DataPipeline()
    codes = dp.get_stock_pool()
    
    if not codes:
        logger.error("股票池为空，请检查 波段股票Top30.csv")
        return

    if args.all or not any([args.fund_flow, args.adjust, args.norm]):
        report = dp.update_all(codes)
        print("\n=== 更新报告 ===")
        for k, v in report.items():
            success = v.get('success', 0) if isinstance(v, dict) else '?'
            total = v.get('total', 0) if isinstance(v, dict) else '?'
            print(f"  {k}: {success}/{total}")
    else:
        if args.fund_flow:
            dp.collect_fund_flow(codes)
        if args.adjust:
            dp.calc_adjust_factor(codes)
        if args.norm:
            dp.calc_rolling_norm(codes)

    print("Done!")


if __name__ == '__main__':
    main()
