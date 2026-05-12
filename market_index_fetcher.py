# -*- coding: utf-8 -*-
"""
大盘指数数据获取模块
功能: 从AKShare获取沪深300指数数据，更新index_daily表
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import sqlite3
import re
from datetime import datetime, timedelta
import time

DB_PATH = r'E:\csi10\stocks.db'

class MarketIndexFetcher:
    """大盘指数数据获取器 - 双保险API"""
    
    # 大盘指数代码映射（扩展版）
    INDEX_CODES = {
        'sh.000001': {'name': '上证指数', 'secid': '1.000001', 'tencent': 'sh000001'},
        'sz.399001': {'name': '深证成指', 'secid': '0.399001', 'tencent': 'sz399001'},
        'sh.000300': {'name': '沪深300', 'secid': '1.000300', 'tencent': 'sh000300'},
        'sh.000905': {'name': '中证500', 'secid': '1.000905', 'tencent': 'sh000905'},  # 新增中证500
    }
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.today = datetime.now().strftime('%Y-%m-%d')
        
    def fetch_realtime_from_eastmoney(self, code='sh.000300'):
        """从东方财富获取今日实时数据"""
        import requests
        
        index_info = self.INDEX_CODES.get(code)
        if not index_info:
            return None
        
        try:
            url = "http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': index_info['secid'],
                'fields': 'f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f169,f170,f171',
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            }
            
            headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://quote.eastmoney.com/'}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data'):
                d = data['data']
                # 东方财富字段: f43=今开, f44=昨收, f45=最高, f46=最低, f47=现价, f48=涨跌, f49=涨幅
                return {
                    'code': code,
                    'name': index_info['name'],
                    'date': self.today,
                    'open': d.get('f43', 0) / 100 if d.get('f43') else 0,
                    'close': d.get('f47', 0) / 100 if d.get('f47') else 0,
                    'high': d.get('f45', 0) / 100 if d.get('f45') else 0,
                    'low': d.get('f46', 0) / 100 if d.get('f46') else 0,
                    'prev_close': d.get('f44', 0) / 100 if d.get('f44') else 0,
                    'pct_chg': d.get('f49', 0) / 100 if d.get('f49') else 0,
                    'volume': d.get('f50', 0) if d.get('f50') else 0,
                    'amount': d.get('f51', 0) if d.get('f51') else 0,
                    'source': 'eastmoney_realtime'
                }
        except Exception as e:
            print(f"东方财富实时API失败: {e}")
        return None
    
    def fetch_realtime_from_tencent(self, code='sh.000300'):
        """从腾讯获取今日实时数据"""
        import requests
        
        index_info = self.INDEX_CODES.get(code)
        if not index_info:
            return None
        
        try:
            url = f"http://qt.gtimg.cn/q={index_info['tencent']}"
            headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://quote.eastmoney.com/'}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'gbk'
            
            # 解析: v_sh000300="1~沪深300~000300~4770.27~..."
            match = re.search(r'"([^"]+)"', resp.text)
            if match:
                parts = match.group(1).split('~')
                # 腾讯字段映射:
                # parts[1] = 名称, parts[2] = 代码, parts[3] = 现价, parts[4] = 昨收
                # parts[30] = 时间, parts[31] = 涨跌额, parts[32] = 涨跌幅
                if len(parts) >= 35:
                    price = float(parts[3]) if parts[3] else 0
                    prev_close = float(parts[4]) if parts[4] else 0
                    pct_chg = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0
                    
                    return {
                        'code': code,
                        'name': parts[1],
                        'date': self.today,
                        'open': float(parts[5]) if parts[5] else price,
                        'close': price,
                        'high': float(parts[33]) if len(parts) > 33 and parts[33] else price,
                        'low': float(parts[34]) if len(parts) > 34 and parts[34] else price,
                        'prev_close': prev_close,
                        'pct_chg': round(pct_chg, 2),
                        'volume': float(parts[36]) * 100 if len(parts) > 36 and parts[36] else 0,
                        'amount': float(parts[37]) * 10000 if len(parts) > 37 and parts[37] else 0,
                        'source': 'tencent_realtime'
                    }
        except Exception as e:
            print(f"腾讯实时API失败: {e}")
        return None
    
    def fetch_today_realtime(self, code='sh.000300'):
        """双保险获取今日实时数据 - 腾讯优先（数据更准确），东方财富备用"""
        # 尝试腾讯（数据更准确）
        data = self.fetch_realtime_from_tencent(code)
        if data and data['close'] > 0:
            print(f"✓ 腾讯获取 {data['name']} 今日数据: {data['close']} ({data['pct_chg']:.2f}%)")
            return data
        
        # 尝试东方财富
        data = self.fetch_realtime_from_eastmoney(code)
        if data and data['close'] > 0:
            print(f"✓ 东方财富获取 {data['name']} 今日数据: {data['close']} ({data['pct_chg']:.2f}%)")
            return data
        
        print(f"✗ {code} 双保险API均失败")
        return None
    
    def fetch_zz500_from_akshare(self):
        """从AKShare获取中证500指数历史数据"""
        try:
            import akshare as ak
            
            print("获取中证500指数数据...")
            df = ak.stock_zh_index_daily(symbol="sh000905")
            
            if df is None or len(df) == 0:
                print("AKShare ZZ500 return empty data")
                return None
            
            print(f"ZZ500 data columns: {df.columns.tolist()}")
            print(f"ZZ500 first 5 rows: {df.head()}")
            
            # Format conversion
            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
            })
            
            # Ensure date column is string format
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # Add pct_chg calculation
            df['pct_chg'] = df['close'].pct_change() * 100
            
            # Add code column
            df['code'] = 'sh.000905'
            
            print(f"Got {len(df)} ZZ500 records")
            return df
            
        except ImportError:
            print("AKShare not installed, try Tencent backup...")
            return self.fetch_zz500_from_eastmoney()
        except Exception as e:
            print(f"AKShare ZZ500 failed: {e}")
            return self.fetch_zz500_from_eastmoney()
    
    def fetch_zz500_from_eastmoney(self):
        """从东方财富API获取中证500历史数据"""
        try:
            import requests
            
            print("Try Eastmoney API for ZZ500...")
            url = "http://push2.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'secid': '1.000905',  # ZZ500 code
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
                'klt': '101',  # Daily K
                'fqt': '1',
                'end': '20500101',
                'lmt': '365',  # Last 365 days
            }
            
            headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://quote.eastmoney.com/'}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                rows = []
                for line in klines:
                    parts = line.split(',')
                    rows.append({
                        'code': 'sh.000905',
                        'date': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': float(parts[5]),
                        'pct_chg': float(parts[6]) if len(parts) > 6 else 0,
                    })
                
                df = pd.DataFrame(rows)
                print(f"Eastmoney got {len(df)} ZZ500 records")
                return df
            
        except Exception as e:
            print(f"Eastmoney ZZ500 API failed: {e}")
        
        return None
    
    def save_zz500_to_db(self, df):
        """Save ZZ500 data to database (22 columns)"""
        if df is None or len(df) == 0:
            return 0
        
        cursor = self.conn.cursor()
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Delete old ZZ500 data
        cursor.execute("DELETE FROM index_daily WHERE code='sh.000905'")
        
        # Insert new data (22 columns)
        inserted = 0
        for _, row in df.iterrows():
            try:
                values = (
                    str(row['code']), str(row['date']),
                    float(row['open']) if pd.notna(row.get('open')) else 0,
                    float(row['high']) if pd.notna(row.get('high')) else 0,
                    float(row['low']) if pd.notna(row.get('low')) else 0,
                    float(row['close']) if pd.notna(row.get('close')) else 0,
                    float(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0,
                    float(row.get('pct_chg', 0)) if pd.notna(row.get('pct_chg')) else 0,
                    float(row['ma5']) if pd.notna(row.get('ma5')) else None,
                    float(row['ma10']) if pd.notna(row.get('ma10')) else None,
                    float(row['ma20']) if pd.notna(row.get('ma20')) else None,
                    float(row['ma30']) if pd.notna(row.get('ma30')) else None,
                    float(row['ema12']) if pd.notna(row.get('ema12')) else None,
                    float(row['ema26']) if pd.notna(row.get('ema26')) else None,
                    float(row['macd']) if pd.notna(row.get('macd')) else None,
                    float(row['macd_signal']) if pd.notna(row.get('macd_signal')) else None,
                    float(row['macd_hist']) if pd.notna(row.get('macd_hist')) else None,
                    float(row['rsi6']) if pd.notna(row.get('rsi6')) else None,
                    0,  # amount
                    0,  # turnover
                    0,  # prev_close
                    'ZZ500'  # name
                )
                cursor.execute('''INSERT INTO index_daily VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )''', values)
                inserted += 1
            except Exception as e:
                if inserted < 5:
                    print(f"Insert error: {e}")
                continue
        
        self.conn.commit()
        print(f"Updated ZZ500 database: {inserted} records")
        return inserted
    
    def check_zz500_freshness(self):
        """Check ZZ500 data freshness"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='index_daily'")
        if not cursor.fetchone():
            return {'count': 0, 'is_enough': False}
        
        cursor.execute("SELECT COUNT(*) FROM index_daily WHERE code='sh.000905'")
        count = cursor.fetchone()[0]
        
        return {
            'count': count,
            'is_enough': count >= 5,  # Need at least 5 days
            'latest_date': None  # Could add more details
        }
    
    def fetch_hs300_from_akshare(self):
        """从AKShare获取沪深300指数数据"""
        try:
            import akshare as ak
            
            # 获取沪深300指数历史数据
            print("获取沪深300指数数据...")
            df = ak.stock_zh_index_daily(symbol="sh000300")
            
            if df is None or len(df) == 0:
                print("❌ AKShare返回空数据")
                return None
            
            print(f"数据列: {df.columns.tolist()}")
            print(f"前5行: {df.head()}")
            
            # 格式转换
            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
            })
            
            # 确保date列是字符串格式
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # 添加涨跌幅计算
            df['pct_chg'] = df['close'].pct_change() * 100
            
            # 添加代码列
            df['code'] = 'sh.000300'
            
            print(f"✓ 获取到 {len(df)} 条数据")
            return df
            
        except ImportError:
            print("❌ AKShare未安装，尝试备用方案...")
            return self.fetch_from_eastmoney()
        except Exception as e:
            print(f"❌ AKShare获取失败: {e}")
            return self.fetch_from_eastmoney()
    
    def fetch_from_eastmoney(self):
        """从东方财富备用API获取"""
        try:
            import requests
            
            print("尝试东方财富API...")
            url = "http://push2.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'secid': '1.000300',  # 沪深300
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
                'klt': '101',  # 日K
                'fqt': '1',
                'end': '20500101',
                'lmt': '365',  # 最近365天
            }
            
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                rows = []
                for line in klines:
                    parts = line.split(',')
                    rows.append({
                        'code': 'sh.000300',
                        'date': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': float(parts[5]),
                        'pct_chg': float(parts[6]) if len(parts) > 6 else 0,
                    })
                
                df = pd.DataFrame(rows)
                print(f"✓ 东方财富获取到 {len(df)} 条数据")
                return df
            
        except Exception as e:
            print(f"❌ 东方财富API失败: {e}")
        
        return None
    
    def calculate_indicators(self, df):
        """计算技术指标"""
        # MA均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma30'] = df['close'].rolling(30).mean()
        
        # EMA
        df['ema12'] = df['close'].ewm(span=12).mean()
        df['ema26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema12'] - df['ema26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(6).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(6).mean()
        rs = gain / loss
        df['rsi6'] = 100 - (100 / (1 + rs))
        
        return df
    
    def save_to_db(self, df):
        """保存到数据库"""
        if df is None or len(df) == 0:
            return 0
        
        cursor = self.conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='index_daily'")
        if not cursor.fetchone():
            # 创建表
            cursor.execute('''CREATE TABLE index_daily (
                code TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                pct_chg REAL,
                ma5 REAL,
                ma10 REAL,
                ma20 REAL,
                ma30 REAL,
                ema12 REAL,
                ema26 REAL,
                macd REAL,
                macd_signal REAL,
                macd_hist REAL,
                rsi6 REAL
            )''')
            print("✓ 创建index_daily表")
        
        # 计算技术指标
        df = self.calculate_indicators(df)
        
        # 删除旧数据
        cursor.execute("DELETE FROM index_daily WHERE code='sh.000300'")
        
        # 插入新数据
        inserted = 0
        for _, row in df.iterrows():
            try:
                values = (
                    str(row['code']), str(row['date']), float(row['open']), float(row['high']), float(row['low']),
                    float(row['close']), float(row.get('volume', 0)), float(row.get('pct_chg', 0) if pd.notna(row.get('pct_chg')) else 0),
                    float(row['ma5']) if pd.notna(row.get('ma5')) else None,
                    float(row['ma10']) if pd.notna(row.get('ma10')) else None,
                    float(row['ma20']) if pd.notna(row.get('ma20')) else None,
                    float(row['ma30']) if pd.notna(row.get('ma30')) else None,
                    float(row['ema12']) if pd.notna(row.get('ema12')) else None,
                    float(row['ema26']) if pd.notna(row.get('ema26')) else None,
                    float(row['macd']) if pd.notna(row.get('macd')) else None,
                    float(row['macd_signal']) if pd.notna(row.get('macd_signal')) else None,
                    float(row['macd_hist']) if pd.notna(row.get('macd_hist')) else None,
                    float(row['rsi6']) if pd.notna(row.get('rsi6')) else None
                )
                cursor.execute('''INSERT INTO index_daily VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )''', values)
                inserted += 1
            except Exception as e:
                if inserted < 10:  # 只显示前几个错误
                    print(f"插入错误: {e}, row: {row.get('date')}")
                continue
        
        self.conn.commit()
        print(f"✓ 更新数据库: {inserted}条记录")
        return inserted
    
    def check_freshness(self):
        """检查数据新鲜度"""
        cursor = self.conn.cursor()
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='index_daily'")
        if not cursor.fetchone():
            return {'latest_date': None, 'delay_days': 999, 'is_fresh': False}
        
        cursor.execute("SELECT MAX(date) FROM index_daily WHERE code='sh.000300'")
        latest = cursor.fetchone()[0]
        
        if latest:
            latest_date = datetime.strptime(latest, '%Y-%m-%d')
            days_delay = (datetime.now() - latest_date).days
            return {
                'latest_date': latest,
                'delay_days': days_delay,
                'is_fresh': days_delay <= 1
            }
        return {'latest_date': None, 'delay_days': 999, 'is_fresh': False}
    
    def save_realtime_to_db(self, realtime_data):
        """保存今日实时数据到数据库"""
        if not realtime_data:
            return False
        
        cursor = self.conn.cursor()
        code = realtime_data['code']
        today = realtime_data['date']
        
        # 确保表结构完整
        cursor.execute("PRAGMA table_info(index_daily)")
        cols = [c[1] for c in cursor.fetchall()]
        
        if 'amount' not in cols:
            cursor.execute("ALTER TABLE index_daily ADD COLUMN amount REAL")
        if 'prev_close' not in cols:
            cursor.execute("ALTER TABLE index_daily ADD COLUMN prev_close REAL")
        
        # 检查今日是否已有数据
        cursor.execute('SELECT COUNT(*) FROM index_daily WHERE code=? AND date=?', (code, today))
        exists = cursor.fetchone()[0]
        
        if exists > 0:
            # 更新今日数据
            cursor.execute('''
                UPDATE index_daily SET 
                    open=?, close=?, high=?, low=?, volume=?, amount=?, pct_chg=?, prev_close=?
                WHERE code=? AND date=?
            ''', (
                realtime_data['open'], realtime_data['close'],
                realtime_data['high'], realtime_data['low'],
                realtime_data.get('volume', 0), realtime_data.get('amount', 0),
                realtime_data['pct_chg'], realtime_data.get('prev_close', 0),
                code, today
            ))
            print(f"✓ 更新 {realtime_data['name']} 今日数据")
        else:
            # 插入今日数据
            cursor.execute('''
                INSERT INTO index_daily (code, date, open, close, high, low, volume, amount, pct_chg, prev_close)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                code, today, realtime_data['open'], realtime_data['close'],
                realtime_data['high'], realtime_data['low'],
                realtime_data.get('volume', 0), realtime_data.get('amount', 0),
                realtime_data['pct_chg'], realtime_data.get('prev_close', 0)
            ))
            print(f"✓ 新增 {realtime_data['name']} 今日数据")
        
        self.conn.commit()
        return True
    
    def close(self):
        self.conn.close()


if __name__ == '__main__':
    import re
    print("=" * 60)
    print("大盘指数数据更新 - 双保险API")
    print("=" * 60)
    
    fetcher = MarketIndexFetcher()
    
    # Step 1: 获取今日实时数据（双保险）
    print("\n[Step 1] 获取今日实时数据")
    
    # 更新沪深300
    realtime_data = fetcher.fetch_today_realtime('sh.000300')
    if realtime_data:
        fetcher.save_realtime_to_db(realtime_data)
    
    # 更新中证500
    print("\n更新中证500...")
    realtime_zz500 = fetcher.fetch_today_realtime('sh.000905')
    if realtime_zz500:
        fetcher.save_realtime_to_db(realtime_zz500)
    
    # Step 2: 获取历史数据补充
    print("\n[Step 2] 检查历史数据完整性")
    freshness = fetcher.check_freshness()
    print(f"HS300 status: {freshness['latest_date']} (delay {freshness['delay_days']} days)")
    
    if freshness['delay_days'] > 3:
        # Get HS300 history
        df = fetcher.fetch_hs300_from_akshare()
        if df is not None and len(df) > 0:
            fetcher.save_to_db(df)
            print("HS300 history data updated")
    
    # Step 2.5: Check and get ZZ500 history
    print("\n[Step 2.5] Check ZZ500 history data")
    zz500_freshness = fetcher.check_zz500_freshness()
    print(f"ZZ500 records: {zz500_freshness['count']} (need >= 5)")
    
    if not zz500_freshness['is_enough']:
        print("ZZ500 data insufficient, fetching history...")
        df_zz500 = fetcher.fetch_zz500_from_akshare()
        if df_zz500 is not None and len(df_zz500) > 0:
            fetcher.save_zz500_to_db(df_zz500)
            print("ZZ500 history data updated")
    
    # Step 3: Verify final data
    print("\n[Step 3] Verify data completeness")
    cursor = fetcher.conn.cursor()
    
    # Check HS300
    cursor.execute('SELECT date, close, pct_chg FROM index_daily WHERE code="sh.000300" ORDER BY date DESC LIMIT 5')
    recent_hs300 = cursor.fetchall()
    print("HS300 last 5 days:")
    for r in recent_hs300:
        print(f"  {r[0]}: close={r[1]:.2f}, pct={r[2]:.2f}%")
    
    # Check ZZ500
    cursor.execute('SELECT date, close, pct_chg FROM index_daily WHERE code="sh.000905" ORDER BY date DESC LIMIT 5')
    recent_zz500 = cursor.fetchall()
    print("\nZZ500 last 5 days:")
    if recent_zz500:
        for r in recent_zz500:
            print(f"  {r[0]}: close={r[1]:.2f}, pct={r[2]:.2f}%")
        
        # Calculate 5-day pct
        if len(recent_zz500) >= 5:
            latest = recent_zz500[0][1]
            fifth = recent_zz500[4][1]
            pct_5d = (latest - fifth) / fifth * 100
            print(f"\nZZ500 5-day change: {pct_5d:.2f}%")
    else:
        print("  No ZZ500 data!")
    
    fetcher.close()
    print("\n" + "=" * 60)
    print("Market data update completed")
    print("=" * 60)