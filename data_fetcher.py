# -*- coding: utf-8 -*-
"""
实时数据获取模块 v2.0
- 使用腾讯/新浪API获取实时行情
- 自动排除非交易日数据（数据为0）
- 自动更新数据库
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import sqlite3
import requests
import time
import random
from datetime import datetime, timedelta

DB_PATH = r'E:\csi10\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'

class RealtimeDataFetcher:
    """实时数据获取器"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        self.last_update = None
        
        # API配置
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://quote.eastmoney.com/'
        })
    
    def _code_to_tencent(self, code):
        """转换代码格式为腾讯格式 600183.SH -> sh600183"""
        parts = code.split('.')
        market = parts[1].lower()  # SH/SZ
        stock = parts[0]            # 600183
        return f"{market}{stock}"
    
    def _code_to_sina(self, code):
        """转换代码格式为新浪格式 600183.SH -> sh600183"""
        market = code.split('.')[1]
        stock = code.split('.')[0]
        return f"{market.lower()}{stock}"
    
    def fetch_from_tencent(self, codes):
        """从腾讯API获取实时数据（推荐，速度快）"""
        # 腾讯股票API格式
        # http://qt.gtimg.cn/q=sh600183,sz000001
        tc_codes = [self._code_to_tencent(c) for c in codes]
        url = f"http://qt.gtimg.cn/q={','.join(tc_codes)}"
        
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            
            # 解析数据
            data_lines = resp.text.strip().split('\n')
            results = {}
            
            for line in data_lines:
                if not line.startswith('v_'):
                    continue
                
                # v_sh600183="1~华通线缆~605196~47.44~..."
                parts = line.split('~')
                if len(parts) < 35:
                    continue
                
                # 解析字段
                code_raw = parts[2]  # 股票代码
                name = parts[1]      # 股票名称
                price = float(parts[3]) if parts[3] else 0  # 当前价格
                prev_close = float(parts[4]) if parts[4] else 0  # 昨收
                high = float(parts[33]) if len(parts) > 33 and parts[33] else price
                low = float(parts[34]) if len(parts) > 34 and parts[34] else price
                volume_hand = float(parts[36]) if len(parts) > 36 and parts[36] else 0  # 手
                volume = int(volume_hand * 100)  # 股
                amount = float(parts[37]) if len(parts) > 37 and parts[37] else 0
                
                # 计算涨跌幅
                pct_chg = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                
                # 提取原始代码格式
                # v_sh600183 -> 600183.SH
                line_start = line.split('=')[0]  # v_sh600183
                if 'sh' in line_start:
                    code = f"{code_raw}.SH"
                elif 'sz' in line_start:
                    code = f"{code_raw}.SZ"
                else:
                    code = code_raw
                
                results[code] = {
                    'code': code,
                    'name': name,
                    'price': price,
                    'prev_close': prev_close,
                    'pct_chg': round(pct_chg, 2),
                    'high': high,
                    'low': low,
                    'volume': volume,
                    'amount': amount,
                    'time': parts[30] if len(parts) > 30 else '',
                    'source': 'tencent'
                }
            
            # 排除非交易日数据
            valid_results = {}
            for code, data in results.items():
                if data['price'] == 0 or data['volume'] == 0:
                    print(f"  {code}: 非交易日或停牌，跳过")
                    continue
                valid_results[code] = data
            
            return valid_results
            
        except Exception as e:
            print(f"腾讯API错误: {e}")
            return None
    
    def fetch_from_sina(self, codes):
        """从新浪API获取实时数据（备用）"""
        sina_codes = [self._code_to_sina(c) for c in codes]
        url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
        
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            
            data_lines = resp.text.strip().split('\n')
            results = {}
            
            for line in data_lines:
                if not line.startswith('var hq_str_'):
                    continue
                
                # var hq_str_sh600183="华通线缆,47.44,47.00,..."
                parts = line.split('=')[1].strip('"').split(',')
                if len(parts) < 32:
                    continue
                
                code_raw = line.split('_')[-1].split('=')[0]
                market_code = line.split('str_')[1].split('=')[0]
                
                if 'sh' in market_code:
                    code = f"{code_raw.split('sh')[1] if 'sh' in code_raw else code_raw}.SH"
                elif 'sz' in market_code:
                    code = f"{code_raw.split('sz')[1] if 'sz' in code_raw else code_raw}.SZ"
                else:
                    code = code_raw
                
                name = parts[0]
                open_price = float(parts[1]) if parts[1] else 0
                prev_close = float(parts[2]) if parts[2] else 0
                price = float(parts[3]) if parts[3] else 0
                high = float(parts[4]) if parts[4] else 0
                low = float(parts[5]) if parts[5] else 0
                volume = int(float(parts[8]) if parts[8] else 0)
                
                # 排除非交易日
                if price == 0 or open_price == 0:
                    print(f"  {code}: 非交易日或停牌，跳过")
                    continue
                
                pct_chg = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                
                results[code] = {
                    'code': code,
                    'name': name,
                    'price': price,
                    'prev_close': prev_close,
                    'pct_chg': round(pct_chg, 2),
                    'high': high,
                    'low': low,
                    'volume': volume,
                    'amount': float(parts[9]) if parts[9] else 0,
                    'time': parts[31] if len(parts) > 31 else '',
                    'source': 'sina'
                }
            
            return results
            
        except Exception as e:
            print(f"新浪API错误: {e}")
            return None
    
    def update_database(self, data_dict):
        """更新数据库"""
        if not data_dict:
            return 0
        
        cursor = self.conn.cursor()
        updated = 0
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        for code, data in data_dict.items():
            try:
                # 检查是否已存在今日数据
                check_sql = "SELECT COUNT(*) FROM daily_price WHERE code=? AND date=?"
                cursor.execute(check_sql, (code, today))
                exists = cursor.fetchone()[0]
                
                if exists > 0:
                    # 更新现有数据
                    update_sql = '''
                        UPDATE daily_price SET 
                            close=?, high=?, low=?, volume=?, pct_chg=?, amount=?
                        WHERE code=? AND date=?
                    '''
                    cursor.execute(update_sql, (
                        data['price'], data['high'], data['low'],
                        data['volume'], data['pct_chg'], data['amount'],
                        code, today
                    ))
                else:
                    # 插入新数据
                    insert_sql = '''
                        INSERT INTO daily_price 
                        (code, date, open, close, high, low, volume, amount, pct_chg, prev_close)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    '''
                    cursor.execute(insert_sql, (
                        code, today, data['prev_close'],
                        data['price'], data['high'], data['low'],
                        data['volume'], data['amount'], data['pct_chg'],
                        data['prev_close']
                    ))
                
                updated += 1
                
            except Exception as e:
                print(f"  {code} 数据库更新错误: {e}")
        
        self.conn.commit()
        return updated
    
    def calculate_indicators(self, code):
        """计算技术指标（MA, RSI, MACD, KDJ等） - 全量计算"""
        sql = "SELECT * FROM daily_price WHERE code=? ORDER BY date ASC"
        df = pd.read_sql_query(sql, self.conn, params=(code,))
        
        if len(df) < 30:
            return
        
        # 均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma30'] = df['close'].rolling(30).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain6 = gain.ewm(alpha=1/6).mean()
        avg_loss6 = loss.ewm(alpha=1/6).mean()
        rs6 = avg_gain6 / avg_loss6
        df['rsi6'] = 100 - (100 / (1 + rs6))
        
        avg_gain12 = gain.ewm(alpha=1/12).mean()
        avg_loss12 = loss.ewm(alpha=1/12).mean()
        rs12 = avg_gain12 / avg_loss12
        df['rsi12'] = 100 - (100 / (1 + rs12))
        
        avg_gain24 = gain.ewm(alpha=1/24).mean()
        avg_loss24 = loss.ewm(alpha=1/24).mean()
        rs24 = avg_gain24 / avg_loss24
        df['rsi24'] = 100 - (100 / (1 + rs24))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # KDJ
        low_n = df['low'].rolling(9).min()
        high_n = df['high'].rolling(9).max()
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        df['k'] = rsv.ewm(alpha=1/3).mean()
        df['d'] = df['k'].ewm(alpha=1/3).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']
        
        # 布林带
        df['boll_mid'] = df['close'].rolling(20).mean()
        df['boll_upper'] = df['boll_mid'] + df['close'].rolling(20).std() * 2
        df['boll_lower'] = df['boll_mid'] - df['close'].rolling(20).std() * 2
        
        # 批量更新数据库
        cursor = self.conn.cursor()
        
        for i in range(20, len(df)):
            row = df.iloc[i]
            
            update_sql = '''
                UPDATE daily_price SET 
                    ma5=?, ma10=?, ma20=?, ma30=?,
                    rsi6=?, rsi12=?, rsi24=?,
                    macd=?, macd_signal=?, macd_hist=?,
                    k=?, d=?, j=?,
                    boll_upper=?, boll_mid=?, boll_lower=?
                WHERE code=? AND date=?
            '''
            
            cursor.execute(update_sql, (
                row['ma5'] if pd.notna(row['ma5']) else None,
                row['ma10'] if pd.notna(row['ma10']) else None,
                row['ma20'] if pd.notna(row['ma20']) else None,
                row['ma30'] if pd.notna(row['ma30']) else None,
                row['rsi6'] if pd.notna(row['rsi6']) else None,
                row['rsi12'] if pd.notna(row['rsi12']) else None,
                row['rsi24'] if pd.notna(row['rsi24']) else None,
                row['macd'] if pd.notna(row['macd']) else None,
                row['macd_signal'] if pd.notna(row['macd_signal']) else None,
                row['macd_hist'] if pd.notna(row['macd_hist']) else None,
                row['k'] if pd.notna(row['k']) else None,
                row['d'] if pd.notna(row['d']) else None,
                row['j'] if pd.notna(row['j']) else None,
                row['boll_upper'] if pd.notna(row['boll_upper']) else None,
                row['boll_mid'] if pd.notna(row['boll_mid']) else None,
                row['boll_lower'] if pd.notna(row['boll_lower']) else None,
                code, row['date']
            ))
        
        self.conn.commit()
    
    def refresh_all(self):
        """刷新所有股票数据"""
        print("=" * 60)
        print(f"刷新股票数据 ({len(self.stock_pool)}只)")
        print("=" * 60)
        
        # 先尝试腾讯API
        print("\n[尝试腾讯API...]")
        data = self.fetch_from_tencent(self.stock_pool)
        
        # 如果腾讯失败，尝试新浪API
        if not data or len(data) < len(self.stock_pool) * 0.8:
            print("[腾讯API失败或数据不全，尝试新浪API...]")
            data = self.fetch_from_sina(self.stock_pool)
        
        if not data:
            print("✗ 所有API获取失败")
            return {'status': 'error', 'updated': 0}
        
        print(f"\n[获取成功: {len(data)}只股票]")
        
        # 更新数据库
        print("\n[更新数据库...]")
        updated = self.update_database(data)
        print(f"  已更新: {updated}只")
        
        # 计算技术指标
        print("\n[计算技术指标...]")
        for code in data.keys():
            try:
                self.calculate_indicators(code)
            except Exception as e:
                print(f"  {code}: 指标计算错误 {e}")
        
        self.last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print("\n" + "=" * 60)
        print(f"✓ 刷新完成! 更新时间: {self.last_update}")
        print("=" * 60)
        
        return {
            'status': 'success',
            'updated': updated,
            'total': len(data),
            'time': self.last_update
        }
    
    def check_freshness(self):
        """检查数据新鲜度"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        sql = '''
            SELECT code, MAX(date) as latest_date
            FROM daily_price
            WHERE code IN ({})
            GROUP BY code
        '''.format(','.join(['?'] * len(self.stock_pool)))
        
        df = pd.read_sql_query(sql, self.conn, params=self.stock_pool)
        
        outdated = []
        for _, row in df.iterrows():
            if row['latest_date'] < today:
                outdated.append({
                    'code': row['code'],
                    'latest_date': row['latest_date'],
                    'delay': (datetime.now() - datetime.strptime(row['latest_date'], '%Y-%m-%d')).days
                })
        
        return {
            'today': today,
            'fresh_count': len(df) - len(outdated),
            'outdated_count': len(outdated),
            'outdated_stocks': outdated
        }
    
    def fetch_history_from_eastmoney(self, code, days=60):
        """从东方财富API获取历史K线数据"""
        # 转换代码格式
        if code.startswith('60') or code.startswith('68'):
            secid = '1.' + code.replace('.SH', '').replace('.SZ', '')
        else:
            secid = '0.' + code.replace('.SZ', '').replace('.SH', '')
        
        url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
            'klt': '101',  # 日K
            'fqt': '1',    # 前复权
            'end': '20500101',
            'lmt': str(days),  # 天数
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            if not data.get('data') or not data['data'].get('klines'):
                return None
            
            klines = data['data']['klines']
            history = []
            
            for line in klines:
                parts = line.split(',')
                if len(parts) >= 6:
                    history.append({
                        'code': code,
                        'date': parts[0],
                        'open': float(parts[1]) if parts[1] else 0,
                        'close': float(parts[2]) if parts[2] else 0,
                        'high': float(parts[3]) if parts[3] else 0,
                        'low': float(parts[4]) if parts[4] else 0,
                        'volume': float(parts[5]) if parts[5] else 0,
                        'pct_chg': float(parts[6]) if len(parts) > 6 and parts[6] else 0
                    })
            
            return history if history else None
            
        except Exception as e:
            print(f"  {code} 历史数据获取失败: {e}")
            return None
    
    def fill_history_data(self, days=60):
        """填充股票池历史数据"""
        print(f"\n[获取{days}天历史数据]")
        
        cursor = self.conn.cursor()
        total_inserted = 0
        
        for code in self.stock_pool:
            history = self.fetch_history_from_eastmoney(code, days)
            
            if not history:
                print(f"  {code}: 无历史数据")
                continue
            
            # 插入历史数据
            for h in history:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO daily_price
                        (code, date, open, close, high, low, volume, pct_chg)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (h['code'], h['date'], h['open'], h['close'], h['high'], h['low'], h['volume'], h['pct_chg']))
                    total_inserted += 1
                except Exception as e:
                    pass
            
            print(f"  {code}: {len(history)}条历史数据")
            time.sleep(0.05)  # 避免请求过快
        
        self.conn.commit()
        print(f"\n✓ 共插入 {total_inserted} 条历史数据")
        
        # 计算技术指标
        print("\n[计算技术指标]")
        for code in self.stock_pool:
            self.calculate_indicators(code)
        
        return total_inserted
    
    def close(self):
        self.conn.close()


if __name__ == '__main__':
    fetcher = RealtimeDataFetcher()
    
    # 检查数据量
    cursor = fetcher.conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_price')
    total = cursor.fetchone()[0]
    
    if total < 1000:  # 数据量不足，先填充历史数据
        print(f"数据量不足({total}条)，开始填充历史数据...")
        fetcher.fill_history_data(60)
    
    # 刷新今日实时数据
    fetcher.refresh_all()
    
    fetcher.close()
    
    print("\n测试完成！")