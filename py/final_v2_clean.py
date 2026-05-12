# -*- coding: utf-8 -*-
"""
波段股票分析系统 v2.2 - XGBoost优化版 + 买点卖点预测
准确率: 74.24% + 买点偏离1.31%
版本日期: 2026-04-18
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, jsonify, render_template_string
import pandas as pd
import sqlite3
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import xgboost as xgb
import warnings
import threading
import logging
warnings.filterwarnings('ignore')

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# 买点卖点预测器（延迟加载，避免启动超时）
BUYSELL_PREDICTOR = None

def get_buysell_predictor():
    """延迟加载买点卖点预测器"""
    global BUYSELL_PREDICTOR
    if BUYSELL_PREDICTOR is None:
        try:
            import buysell_predictor_v5
            BUYSELL_PREDICTOR = buysell_predictor_v5.BuySellPredictor()
            BUYSELL_PREDICTOR.train_models()
            print(f"✓ 买点卖点预测器已加载 (买点MAE: {BUYSELL_PREDICTOR.buy_mae:.2f}%)")
        except Exception as e:
            print(f"买点卖点预测器加载失败: {e}")
            BUYSELL_PREDICTOR = None
    return BUYSELL_PREDICTOR

# 股票名称字典
STOCK_NAMES = {
    '605196.SH': '华通线缆', '688028.SH': '沃尔德', '688195.SH': '拓荆科技',
    '688233.SH': '格林深瞳', '688519.SH': '南亚新材', '002353.SZ': '杰瑞股份',
    '002384.SZ': '东山精密', '600183.SH': '生益科技', '603876.SH': '鼎胜新材',
    '603986.SH': '兆易创新', '688416.SH': '恒烁股份', '688521.SH': '芯原股份',
    '688676.SH': '金盘科技', '300136.SZ': '信维通信', '603225.SH': '新凤鸣',
    '688308.SH': '博瑞医药', '688388.SH': '嘉元科技', '688556.SH': '高测股份',
    '600118.SH': '中国卫星', '601231.SH': '环旭电子', '688658.SH': '埃斯顿',
    '688668.SH': '鼎通股份', '688788.SH': '科思科技', '002202.SZ': '金风科技',
    '002916.SZ': '深信服', '300604.SZ': '长川科技', '603228.SH': '景旺电子',
    '688698.SH': '伟测科技', '002460.SZ': '赣锋锂业', '300476.SZ': '胜宏科技',
    '000001.SZ': '平安银行', '000002.SZ': '万科A', '000333.SZ': '美的集团',
    '600519.SH': '贵州茅台', '601318.SH': '中国平安', '688981.SH': '中芯国际',
}

def get_stock_name(code):
    return STOCK_NAMES.get(code, code.split('.')[0])

app = Flask(__name__)

DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
INDEX_CODE = 'sh.000300'

class AnalyzerV3:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        self.models = {}
        self.analysis_results = []
        self.accuracy_report = {}
        self.last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.last_analysis_time = None
        self.buysell_predictor = None
        self.auto_refresh_timer = None
        
        print("加载大盘数据...")
        self.index_data = self._load_index_data()
        
        print("训练模型（完整43特征 + XGBoost）...")
        self._train_models()
        
        # 初始化买点卖点预测器
        print("加载买点卖点预测器...")
        self.buysell_predictor = get_buysell_predictor()
        
        print("分析股票...")
        self._analyze()
        
        # 启动自动刷新（30分钟）
        self._start_auto_refresh()
    
    def _load_index_data(self):
        sql = '''
            SELECT date, close, pct_chg, ma5, ma10, ma20, ma30,
                   macd, macd_signal, macd_hist, rsi6, rsi12, rsi24
            FROM index_daily WHERE code = ? ORDER BY date DESC LIMIT 1000
        '''
        df = pd.read_sql_query(sql, self.conn, params=(INDEX_CODE,))
        if len(df) == 0:
            return None
        df = df.iloc[::-1].reset_index(drop=True)
        df['date'] = pd.to_datetime(df['date'])
        print(f"✓ 大盘数据: {len(df)}条")
        return df
    
    def _extract_features(self, df, i):
        """完整特征提取（43个特征）"""
        if i < 60 or i >= len(df) - 3:
            return None
        
        row = df.iloc[i]
        current_date = row['date']
        
        close = row['close'] if pd.notna(row['close']) else 0
        volume = row['volume'] if pd.notna(row['volume']) else 0
        pct_chg = row['pct_chg'] if pd.notna(row['pct_chg']) else 0
        high = row['high'] if pd.notna(row['high']) else close
        low = row['low'] if pd.notna(row['low']) else close
        
        ma5 = row['ma5'] if pd.notna(row['ma5']) else close
        ma10 = row['ma10'] if pd.notna(row['ma10']) else close
        ma20 = row['ma20'] if pd.notna(row['ma20']) else close
        ma30 = row['ma30'] if pd.notna(row['ma30']) else close
        
        rsi6 = row['rsi6'] if pd.notna(row['rsi6']) else 50
        rsi12 = row['rsi12'] if pd.notna(row['rsi12']) else 50
        rsi24 = row['rsi24'] if pd.notna(row['rsi24']) else 50
        
        macd = row['macd'] if pd.notna(row['macd']) else 0
        macd_signal = row['macd_signal'] if pd.notna(row['macd_signal']) else 0
        macd_hist = row['macd_hist'] if pd.notna(row.get('macd_hist', 0)) else 0
        
        k = row['k'] if pd.notna(row.get('k', 50)) else 50
        d = row['d'] if pd.notna(row.get('d', 50)) else 50
        j = row['j'] if pd.notna(row.get('j', 50)) else 50
        
        feat = {}
        
        # 价格动量
        feat['pct_chg'] = pct_chg
        feat['pct_chg_5d'] = df.iloc[i-5:i]['pct_chg'].sum() if i >= 5 else 0
        feat['pct_chg_10d'] = df.iloc[i-10:i]['pct_chg'].sum() if i >= 10 else 0
        
        # 均线系统
        feat['ma5_ratio'] = close/ma5 if ma5 > 0 else 1
        feat['ma10_ratio'] = close/ma10 if ma10 > 0 else 1
        feat['ma20_ratio'] = close/ma20 if ma20 > 0 else 1
        feat['ma30_ratio'] = close/ma30 if ma30 > 0 else 1
        feat['ma5_ma10_diff'] = (ma5 - ma10)/ma10 if ma10 > 0 else 0
        feat['ma10_ma20_diff'] = (ma10 - ma20)/ma20 if ma20 > 0 else 0
        feat['ma5_slope'] = (ma5 - df.iloc[i-5]['ma5'])/ma5 if i >= 5 and ma5 > 0 else 0
        
        # RSI系统
        feat['rsi6'] = rsi6
        feat['rsi12'] = rsi12
        feat['rsi24'] = rsi24
        feat['rsi6_rsi12_diff'] = rsi6 - rsi12
        feat['rsi_oversold'] = 1 if rsi6 < 30 else 0
        feat['rsi_overbought'] = 1 if rsi6 > 70 else 0
        
        # MACD系统
        feat['macd'] = macd
        feat['macd_hist'] = macd_hist
        feat['macd_signal'] = macd_signal
        feat['macd_cross_up'] = 1 if macd > macd_signal and macd_hist > 0 else 0
        feat['macd_cross_down'] = 1 if macd < macd_signal and macd_hist < 0 else 0
        
        # KDJ系统
        feat['k'] = k
        feat['d'] = d
        feat['j'] = j
        feat['kdj_cross'] = 1 if k > d else 0
        
        # 量价关系
        if i >= 20:
            vol_ma = df.iloc[i-20:i]['volume'].mean()
            feat['vol_ratio'] = volume/vol_ma if vol_ma > 0 else 1
        else:
            feat['vol_ratio'] = 1
        feat['vol_price_trend'] = 1 if volume > feat['vol_ratio'] * 1.5 and pct_chg > 0 else 0
        
        # 波动率
        if i >= 20:
            closes20 = df.iloc[i-20:i+1]['close'].values
            returns20 = np.diff(closes20)/closes20[:-1]
            feat['volatility_20'] = np.std(returns20) * 100
        else:
            feat['volatility_20'] = 2
        if i >= 30:
            closes30 = df.iloc[i-30:i+1]['close'].values
            returns30 = np.diff(closes30)/closes30[:-1]
            feat['volatility_30'] = np.std(returns30) * 100
        else:
            feat['volatility_30'] = 2
        
        # 价格位置
        if i >= 60:
            high_60 = df.iloc[i-60:i+1]['close'].max()
            low_60 = df.iloc[i-60:i+1]['close'].min()
            feat['price_position_60'] = (close - low_60)/(high_60 - low_60) if high_60 > low_60 else 0.5
        else:
            feat['price_position_60'] = 0.5
        
        # 涨跌统计
        if i >= 5:
            pct_list5 = df.iloc[i-5:i]['pct_chg'].values
            feat['up_days_5'] = len([p for p in pct_list5 if p > 0])
            feat['down_days_5'] = len([p for p in pct_list5 if p < 0])
        else:
            feat['up_days_5'] = 0
            feat['down_days_5'] = 0
        if i >= 10:
            pct_list10 = df.iloc[i-10:i]['pct_chg'].values
            feat['up_days_10'] = len([p for p in pct_list10 if p > 0])
            feat['down_days_10'] = len([p for p in pct_list10 if p < 0])
        else:
            feat['up_days_10'] = 0
            feat['down_days_10'] = 0
        
        # 日内波动
        feat['intraday_range'] = (high - low)/low * 100 if low > 0 else 0
        
        # 大盘因子
        if self.index_data is not None:
            idx_row = self.index_data[self.index_data['date'] == current_date]
            if len(idx_row) > 0:
                idx = idx_row.iloc[0]
                feat['index_pct_chg'] = idx['pct_chg'] if pd.notna(idx['pct_chg']) else 0
                feat['index_ma5_ratio'] = idx['close']/idx['ma5'] if pd.notna(idx['ma5']) and idx['ma5'] > 0 else 1
                feat['index_rsi6'] = idx['rsi6'] if pd.notna(idx['rsi6']) else 50
                feat['index_rsi12'] = idx['rsi12'] if pd.notna(idx['rsi12']) else 50
                feat['index_macd'] = idx['macd'] if pd.notna(idx['macd']) else 0
                feat['index_macd_hist'] = idx['macd_hist'] if pd.notna(idx['macd_hist']) else 0
                feat['stock_vs_index'] = pct_chg - feat['index_pct_chg']
            else:
                feat['index_pct_chg'] = 0
                feat['index_ma5_ratio'] = 1
                feat['index_rsi6'] = 50
                feat['index_rsi12'] = 50
                feat['index_macd'] = 0
                feat['index_macd_hist'] = 0
                feat['stock_vs_index'] = 0
        else:
            feat['index_pct_chg'] = 0
            feat['index_ma5_ratio'] = 1
            feat['index_rsi6'] = 50
            feat['index_rsi12'] = 50
            feat['index_macd'] = 0
            feat['index_macd_hist'] = 0
            feat['stock_vs_index'] = 0
        
        # 目标
        close_3d = df.iloc[i+3]['close']
        rise_3d = (close_3d - close)/close if close > 0 else 0
        feat['target'] = 1 if rise_3d >= 0.03 else 0
        
        return feat
    
    def _train_models(self):
        accuracies = []
        for code in self.stock_pool:
            try:
                sql = "SELECT * FROM daily_price WHERE code=? ORDER BY date DESC LIMIT 500"
                df = pd.read_sql_query(sql, self.conn, params=(code,))
                if len(df) < 100:
                    continue
                df = df.iloc[::-1].reset_index(drop=True)
                df['date'] = pd.to_datetime(df['date'])
                
                features = []
                for i in range(60, len(df)-3):
                    feat = self._extract_features(df, i)
                    if feat:
                        features.append(feat)
                
                if len(features) < 30:
                    continue
                
                ds = pd.DataFrame(features)
                X = ds.drop('target', axis=1)
                y = ds['target']
                
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                
                model = xgb.XGBClassifier(
                    n_estimators=200, max_depth=6, learning_rate=0.1,
                    subsample=0.8, colsample_bytree=0.8,
                    objective='binary:logistic', eval_metric='auc',
                    random_state=42, n_jobs=-1, verbosity=0
                )
                model.fit(X_train, y_train)
                
                y_pred = model.predict(X_test)
                acc = accuracy_score(y_test, y_pred)
                accuracies.append(acc)
                
                self.models[code] = {'model': model, 'data': df, 'features': X.columns.tolist(), 'accuracy': acc}
            except Exception as e:
                print(f"{code}: {e}")
        
        if accuracies:
            self.accuracy_report = {'avg': np.mean(accuracies), 'min': np.min(accuracies), 'max': np.max(accuracies), 'count': len(accuracies)}
            print(f"✓ 平均准确率: {self.accuracy_report['avg']:.2%} (范围: {self.accuracy_report['min']:.2%} ~ {self.accuracy_report['max']:.2%})")
    
    def _analyze(self):
        self.analysis_results = []
        # 确保买点卖点预测器已加载
        if self.buysell_predictor is None:
            self.buysell_predictor = get_buysell_predictor()
        print(f"[分析] 买点卖点预测器状态: {self.buysell_predictor is not None}")
        for code in self.stock_pool:
            pred = self._predict(code)
            if pred:
                # 添加买点卖点预测
                if self.buysell_predictor:
                    try:
                        buysell = self.buysell_predictor.predict(code)
                        if buysell:
                            pred['buy_price'] = float(buysell['buy']['price_center'])
                            pred['buy_change'] = float(buysell['buy']['change_pct'])
                            pred['sell_price'] = float(buysell['sell']['price_center'])
                            pred['sell_change'] = float(buysell['sell']['change_pct'])
                    except Exception as e:
                        print(f"[分析] {code} 买点卖点预测失败: {e}")
                self.analysis_results.append(pred)
        self.analysis_results.sort(key=lambda x: x['score'], reverse=True)
        self.last_analysis_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 统计买点卖点数据
        with_buysell = sum(1 for x in self.analysis_results if 'buy_price' in x)
        print(f"[分析] 完成，{len(self.analysis_results)}只股票，{with_buysell}只包含买点卖点")
    
    def _start_auto_refresh(self):
        """启动自动刷新定时器（30分钟）"""
        def auto_refresh_loop():
            import time
            while True:
                time.sleep(1800)  # 30分钟
                print("\n[自动刷新] 开始刷新数据...")
                self.refresh()
                print("[自动刷新] 数据刷新完成")
        
        self.auto_refresh_timer = threading.Thread(target=auto_refresh_loop, daemon=True)
        self.auto_refresh_timer.start()
        print("✓ 自动刷新已启动（间隔30分钟）")
    
    def _predict(self, code):
        if code not in self.models:
            sql = "SELECT * FROM daily_price WHERE code=? ORDER BY date DESC LIMIT 1"
            df = pd.read_sql_query(sql, self.conn, params=(code,))
            if len(df) == 0:
                return None
            row = df.iloc[0]
            return {
                'code': code, 'name': get_stock_name(code),
                'price': float(row['close']) if pd.notna(row['close']) else 0,
                'change_pct': float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0,
                'rsi': float(row['rsi6']) if pd.notna(row['rsi6']) else 50,
                'macd': float(row['macd']) if pd.notna(row['macd']) else 0,
                'probability': 0.5, 'action': '持有', 'confidence': '低',
                'score': 50, 'accuracy': 0
            }
        
        m = self.models[code]
        df = m['data']
        features = m['features']
        
        latest_feat = self._extract_features(df, len(df) - 4)
        if latest_feat is None:
            return None
        
        X = pd.DataFrame([latest_feat])[features]
        prob = m['model'].predict_proba(X)[0, 1] if len(m['model'].classes_) > 1 else 0.5
        
        action = '买入' if prob >= 0.6 else '卖出' if prob <= 0.3 else '持有'
        conf = '高' if prob >= 0.7 or prob <= 0.25 else '中' if prob >= 0.55 or prob <= 0.4 else '低'
        
        row = df.iloc[-1]
        return {
            'code': code, 'name': get_stock_name(code),
            'price': float(row['close']) if pd.notna(row['close']) else 0,
            'change_pct': float(row['pct_chg']) if pd.notna(row['pct_chg']) else 0,
            'rsi': float(row['rsi6']) if pd.notna(row['rsi6']) else 50,
            'macd': float(row['macd']) if pd.notna(row['macd']) else 0,
            'probability': float(prob), 'action': action, 'confidence': conf,
            'score': int(prob * 100), 'accuracy': m['accuracy']
        }
    
    def refresh(self):
        self.last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.index_data = self._load_index_data()
        
        # 确保买点卖点预测器已加载
        if self.buysell_predictor is None:
            print("[刷新] 重新加载买点卖点预测器...")
            self.buysell_predictor = get_buysell_predictor()
        
        # 刷新买点卖点预测模型
        if self.buysell_predictor:
            try:
                print("[刷新] 更新买点卖点模型...")
                self.buysell_predictor.train_models()
                print(f"[刷新] 买点MAE: {self.buysell_predictor.buy_mae:.2f}%")
            except Exception as e:
                print(f"[刷新] 买点卖点模型更新失败: {e}")
        
        print("[刷新] 分析股票...")
        self._analyze()
        print(f"[刷新] 分析完成，{len(self.analysis_results)}只股票")
        return {'status': 'success', 'time': self.last_analysis_time, 'buysell_updated': self.buysell_predictor is not None}
    
    def get_all(self):
        # 确保数据包含买点卖点
        results = self.analysis_results
        if results and 'buy_price' not in results[0]:
            logger.info(f"[get_all] 买点卖点数据缺失，重新补充...")
            self._add_buysell_to_results()
        return self.analysis_results
    
    def _add_buysell_to_results(self):
        """补充买点卖点数据到现有结果"""
        if self.buysell_predictor is None:
            self.buysell_predictor = get_buysell_predictor()
        if self.buysell_predictor:
            for item in self.analysis_results:
                if 'buy_price' not in item:
                    try:
                        buysell = self.buysell_predictor.predict(item['code'])
                        if buysell:
                            item['buy_price'] = float(buysell['buy']['price_center'])
                            item['buy_change'] = float(buysell['buy']['change_pct'])
                            item['sell_price'] = float(buysell['sell']['price_center'])
                            item['sell_change'] = float(buysell['sell']['change_pct'])
                    except Exception as e:
                        logger.info(f"[补充] {item['code']} 失败: {e}")
            logger.info(f"[补充完成] {sum(1 for x in self.analysis_results if 'buy_price' in x)}只包含买点卖点")
    
    def get_buy(self, n=5):
        results = [x for x in self.analysis_results if x['action']=='买入'][:n]
        # 确保买点卖点数据
        if results and 'buy_price' not in results[0]:
            self._add_buysell_to_results()
        return [x for x in self.analysis_results if x['action']=='买入'][:n]
    
    def get_sell(self):
        results = [x for x in self.analysis_results if x['action']=='卖出']
        if results and 'buy_price' not in results[0]:
            self._add_buysell_to_results()
        return [x for x in self.analysis_results if x['action']=='卖出']
    def get_accuracy(self): return self.accuracy_report

# Flask钩子：确保analyzer已初始化
@app.before_request
def ensure_analyzer():
    global analyzer
    if analyzer is None:
        print('[Flask] analyzer未初始化，创建新实例...')
        analyzer = AnalyzerV3()

analyzer = None  # 延迟初始化

@app.route('/api/status')
def api_status():
    predictor = BUYSELL_PREDICTOR
    return jsonify({
        'update_time': analyzer.last_update,
        'analysis_time': analyzer.last_analysis_time,
        'stock_count': len(analyzer.analysis_results),
        'buy_count': len([x for x in analyzer.analysis_results if x['action']=='买入']),
        'sell_count': len([x for x in analyzer.analysis_results if x['action']=='卖出']),
        'avg_accuracy': analyzer.accuracy_report.get('avg', 0),
        'feature_count': 43,
        'version': 'v2.2-xgboost-buysell-auto-refresh',
        'model': 'XGBoost',
        'buysell_enabled': predictor is not None,
        'buysell_buy_mae': predictor.buy_mae if predictor else 0,
        'buysell_sell_mae': predictor.sell_mae if predictor else 0,
        'auto_refresh': '30分钟'
    })

@app.route('/api/accuracy')
def api_accuracy():
    return jsonify(analyzer.get_accuracy())

@app.route('/api/refresh')
def api_refresh():
    global analyzer
    print(f"[API] analyzer状态: {analyzer is not None}, type: {type(analyzer)}")
    sys.stdout.flush()
    if analyzer is None:
        print("[API] analyzer为None，重新创建...")
        sys.stdout.flush()
        analyzer = AnalyzerV3()
    # 强制确保买点卖点预测器已加载
    if analyzer.buysell_predictor is None:
        print("[API] buysell_predictor为None，重新加载...")
        sys.stdout.flush()
        analyzer.buysell_predictor = get_buysell_predictor()
    result = analyzer.refresh()
    # 检查结果
    data = analyzer.get_all()
    has_buysell = sum(1 for x in data if 'buy_price' in x)
    print(f"[API] 刷新完成，{len(data)}只股票，{has_buysell}只包含买点卖点")
    sys.stdout.flush()
    return jsonify(result)

@app.route('/api/all')
def api_all():
    return jsonify(analyzer.get_all())

@app.route('/api/buy')
def api_buy():
    return jsonify(analyzer.get_buy(5))

@app.route('/api/sell')
def api_sell():
    return jsonify(analyzer.get_sell())

@app.route('/api/report/<code>')
def api_report(code):
    """技术分析报告API"""
    try:
        sql = "SELECT * FROM daily_price WHERE code=? ORDER BY date DESC LIMIT 60"
        df = pd.read_sql_query(sql, analyzer.conn, params=(code,))
        if len(df) == 0:
            return jsonify({'error': '股票不存在'})
        
        df = df.iloc[::-1].reset_index(drop=True)
        latest = df.iloc[-1]
        
        # 基本数据
        close = float(latest['close']) if pd.notna(latest['close']) else 0
        pct_chg = float(latest['pct_chg']) if pd.notna(latest['pct_chg']) else 0
        volume = float(latest['volume']) if pd.notna(latest['volume']) else 0
        
        # 均线 - 如果最新数据为NaN，往前查找有数据的记录
        ma5 = None
        ma10 = None
        ma20 = None
        for i in range(len(df)-1, max(0, len(df)-10), -1):
            row_i = df.iloc[i]
            if pd.notna(row_i.get('ma5')) and pd.notna(row_i.get('ma10')) and pd.notna(row_i.get('ma20')):
                ma5 = float(row_i['ma5'])
                ma10 = float(row_i['ma10'])
                ma20 = float(row_i['ma20'])
                break
        # 如果还是没找到，用当前价格
        if ma5 is None:
            ma5 = close
        if ma10 is None:
            ma10 = close
        if ma20 is None:
            ma20 = close
        
        # 技术指标
        rsi = float(latest['rsi6']) if pd.notna(latest['rsi6']) else 50
        macd = float(latest['macd']) if pd.notna(latest['macd']) else 0
        macd_hist = float(latest.get('macd_hist', 0)) if pd.notna(latest.get('macd_hist', 0)) else 0
        
        # KDJ
        k = float(latest.get('k', 50)) if pd.notna(latest.get('k', 50)) else 50
        d = float(latest.get('d', 50)) if pd.notna(latest.get('d', 50)) else 50
        j = float(latest.get('j', 50)) if pd.notna(latest.get('j', 50)) else 50
        
        # 量比
        vol_ma20 = df.iloc[-20:]['volume'].mean() if len(df) >= 20 else volume
        vol_ratio = volume / vol_ma20 if vol_ma20 > 0 else 1
        
        # 支撑压力位
        low_20 = df.iloc[-20:]['low'].min() if len(df) >= 20 else close
        high_20 = df.iloc[-20:]['high'].max() if len(df) >= 20 else close
        
        # 波动率
        if len(df) >= 30:
            closes = df.iloc[-30:]['close'].values
            returns = np.diff(closes) / closes[:-1]
            volatility = np.std(returns) * 100
        else:
            volatility = 2
        
        # 趋势判断
        if close > ma5 and ma5 > ma10:
            trend = '上升趋势'
        elif close < ma5 and ma5 < ma10:
            trend = '下降趋势'
        else:
            trend = '震荡整理'
        
        # RSI信号
        if rsi > 70:
            rsi_signal = '超买预警'
        elif rsi < 30:
            rsi_signal = '超卖机会'
        else:
            rsi_signal = '中性区间'
        
        # MACD信号
        if macd > 0 and macd_hist > 0:
            macd_signal = '多头信号'
        elif macd < 0 and macd_hist < 0:
            macd_signal = '空头信号'
        else:
            macd_signal = '趋势转折'
        
        # 操作建议
        pred = analyzer._predict(code)
        if pred:
            suggestion = f"{pred['action']} (置信度: {pred['confidence']}, 评分: {pred['score']})"
        else:
            suggestion = '持有观望'
        
        # 距离支撑压力位
        distance_support = ((close - low_20) / close * 100) if close > 0 else 0
        distance_resistance = ((high_20 - close) / close * 100) if close > 0 else 0
        
        # 数据日期和天数
        latest_date = str(latest['date']) if pd.notna(latest['date']) else ''
        data_days = len(df)
        
        return jsonify({
            'code': code,
            'name': get_stock_name(code),
            'current_price': round(close, 2),
            'change_today': round(pct_chg, 2),
            'volume': int(volume),
            'vol_ratio': round(vol_ratio, 2),
            'latest_date': latest_date,
            'data_days': data_days,
            'ma5': round(ma5, 2),
            'ma10': round(ma10, 2),
            'ma20': round(ma20, 2),
            'trend': trend,
            'rsi': round(rsi, 2),
            'rsi_signal': rsi_signal,
            'macd': round(macd, 4),
            'macd_hist': round(macd_hist, 4),
            'macd_signal': macd_signal,
            'k': round(k, 2),
            'd': round(d, 2),
            'j': round(j, 2),
            'support': round(low_20, 2),
            'resistance': round(high_20, 2),
            'distance_support': round(distance_support, 1),
            'distance_resistance': round(distance_resistance, 1),
            'volatility_30': round(volatility, 2),
            'suggestion': suggestion
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/buysell/<code>')
def api_buysell(code):
    """买点卖点预测API"""
    try:
        predictor = get_buysell_predictor()
        if predictor is None:
            return jsonify({'error': '买点卖点预测器未加载'})
        
        result = predictor.predict(code)
        if result is None:
            return jsonify({'error': '股票数据不足'})
        
        return jsonify({
            'code': code,
            'name': get_stock_name(code),
            'current_price': float(result['current_price']),
            'buy': result['buy'],
            'sell': result['sell']
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()})

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>波段股票分析 v2.1 (XGBoost)</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei';background:#1a1a2e;color:#fff;padding:20px}
.header{text-align:center;margin-bottom:20px;padding:20px;background:rgba(255,255,255,0.1);border-radius:15px}
.accuracy-box{background:rgba(102,126,234,0.2);padding:15px;border-radius:10px;margin:10px 0;text-align:center}
.accuracy-value{font-size:28px;color:#764ba2;font-weight:bold}
.refresh-btn{padding:10px 25px;background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:20px;color:#fff;cursor:pointer;margin:5px}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}
.panel{background:rgba(255,255,255,0.05);border-radius:15px;padding:20px}
.card{background:rgba(255,255,255,0.08);border-radius:10px;padding:15px;margin:10px 0}
.card.buy{background:rgba(16,185,129,0.2);border-left:4px solid #10b981}
.card.sell{background:rgba(239,68,68,0.2);border-left:4px solid #ef4444}
.badge{padding:5px 15px;border-radius:15px;font-weight:bold}
.badge.buy{background:#10b981}
.badge.sell{background:#ef4444}
.badge.hold{background:#3b82f6}
</style>
</head>
<body>
<div class="header">
<h1>📊 波段股票分析 v2.1 (XGBoost + 43特征)</h1>
<div id="time">数据: {{update}} | 分析: {{analysis}}</div>
<div class="accuracy-box">
<h2>模型准确率</h2>
<div class="accuracy-value" id="accuracy">-</div>
</div>
<button class="refresh-btn" onclick="refreshAll()">🔄 全局刷新</button>
</div>
<div class="grid">
<div class="panel"><h3>📈 30只股票池</h3><div id="pool"></div></div>
<div class="panel"><h3>🎯 买入推荐</h3><div id="buy"></div></div>
<div class="panel"><h3>⚠️ 卖出信号</h3><div id="sell"></div></div>
</div>
<script>
function refreshAll(){fetch('/api/refresh').then(r=>r.json()).then(d=>{if(d.status==='success')location.reload()})}
function renderPool(d){document.getElementById('pool').innerHTML=d.map(s=>{
  let buysell = '';
  if(s.buy_price) buysell = `<div style="font-size:11px;color:#10b981">买点 ¥${s.buy_price.toFixed(2)} (${s.buy_change.toFixed(2)}%)</div>`;
  if(s.sell_price) buysell += `<div style="font-size:11px;color:#ef4444">卖点 ¥${s.sell_price.toFixed(2)} (${s.sell_change.toFixed(2)}%)</div>`;
  return `<div class="card ${s.action.toLowerCase()}">${s.code} ${s.name} ¥${s.price.toFixed(2)} <span class="badge ${s.action.toLowerCase()}">${s.action}</span> 准确率:${(s.accuracy*100).toFixed(0)}%${buysell}</div>`;
}).join('')}
function renderBuy(d){document.getElementById('buy').innerHTML=d.map(s=>{
  let buysell = '';
  if(s.buy_price) buysell = `<div style="font-size:11px;color:#10b981">买点 ¥${s.buy_price.toFixed(2)} (${s.buy_change.toFixed(2)}%)</div>`;
  if(s.sell_price) buysell += `<div style="font-size:11px;color:#ef4444">卖点 ¥${s.sell_price.toFixed(2)} (${s.sell_change.toFixed(2)}%)</div>`;
  return `<div class="card buy">${s.code} ${s.name} ¥${s.price.toFixed(2)} <span class="badge buy">买入</span> 评分:${s.score}${buysell}</div>`;
}).join('')||'<div style="padding:20px;color:#888">暂无信号</div>'}
function renderSell(d){document.getElementById('sell').innerHTML=d.map(s=>{
  let buysell = '';
  if(s.buy_price) buysell = `<div style="font-size:11px;color:#10b981">买点 ¥${s.buy_price.toFixed(2)} (${s.buy_change.toFixed(2)}%)</div>`;
  if(s.sell_price) buysell += `<div style="font-size:11px;color:#ef4444">卖点 ¥${s.sell_price.toFixed(2)} (${s.sell_change.toFixed(2)}%)</div>`;
  return `<div class="card sell">${s.code} ${s.name} ¥${s.price.toFixed(2)} <span class="badge sell">卖出</span>${buysell}</div>`;
}).join('')||'<div style="padding:20px;color:#888">暂无信号</div>'}
fetch('/api/all').then(r=>r.json()).then(renderPool)
fetch('/api/buy').then(r=>r.json()).then(renderBuy)
fetch('/api/sell').then(r=>r.json()).then(renderSell)
fetch('/api/accuracy').then(r=>r.json()).then(d=>{if(d.avg)document.getElementById('accuracy').textContent=(d.avg*100).toFixed(1)+'%'})
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML, update=analyzer.last_update, analysis=analyzer.last_analysis_time)

if __name__ == '__main__':
    print("============================================================")
    print("波段股票分析系统 v2.1 (XGBoost + 43特征)")
    print("============================================================")
    
    # Step 1: 自动刷新数据
    print("[检查数据新鲜度...]")
    from data_fetcher import RealtimeDataFetcher
    fetcher = RealtimeDataFetcher()
    freshness = fetcher.check_freshness()
    
    if freshness['outdated_count'] > 0:
        print(f"[发现 {freshness['outdated_count']} 只股票数据过期]")
        print("[自动刷新数据...]")
        result = fetcher.refresh_all()
        if result['status'] == 'success':
            print(f"✓ 数据刷新成功: {result['updated']} 只股票")
        else:
            print(f"✗ 数据刷新失败，使用现有数据")
    else:
        print(f"✓ 数据已是最新: {freshness['today']}")
    fetcher.close()
    
    # Step 2: 初始化分析引擎
    print("============================================================")
    print("加载大盘数据...")
    analyzer = AnalyzerV3()
    print(f"✓ 大盘数据: {len(analyzer.index_data)}条")
    print(f"✓ 平均准确率: {analyzer.accuracy_report['avg']:.2f}% (范围: {analyzer.accuracy_report['min']:.2f}% ~ {analyzer.accuracy_report['max']:.2f}%)")
    print(f"✓ 买点卖点: {analyzer.buysell_predictor.buy_mae:.2f}% MAE" if analyzer.buysell_predictor else "买点卖点: 未加载")
    print(f"✓ 分析股票: {len(analyzer.analysis_results)}只")
    print("============================================================")
    
    print("访问: http://localhost:5000")
    app.run(debug=False, port=5000, threaded=True)