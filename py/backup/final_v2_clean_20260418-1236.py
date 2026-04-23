# -*- coding: utf-8 -*-
"""
波段股票分析系统 v2.0 - 数据刷新版（含大盘因子优化）
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, jsonify, render_template_string
import pandas as pd
import sqlite3
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# 股票名称字典（30只波段股票池）
STOCK_NAMES = {
    # 核心波段股票
    '605196.SH': '华通线缆',
    '688028.SH': '沃尔德',
    '688195.SH': '拓荆科技',
    '688233.SH': '格林深瞳',
    '688519.SH': '南亚新材',
    '002353.SZ': '杰瑞股份',
    '002384.SZ': '东山精密',
    '600183.SH': '生益科技',
    '603876.SH': '鼎胜新材',
    '603986.SH': '兆易创新',
    '688416.SH': '恒烁股份',
    '688521.SH': '芯原股份',
    '688676.SH': '金盘科技',
    '300136.SZ': '信维通信',
    '603225.SH': '新凤鸣',
    '688308.SH': '博瑞医药',
    '688388.SH': '嘉元科技',
    '688556.SH': '高测股份',
    '600118.SH': '中国卫星',
    '601231.SH': '环旭电子',
    '688658.SH': '埃斯顿',
    '688668.SH': '鼎通股份',
    '688788.SH': '科思科技',
    '002202.SZ': '金风科技',
    '002916.SZ': '深信服',
    '300604.SZ': '长川科技',
    '603228.SH': '景旺电子',
    '688698.SH': '伟测科技',
    '002460.SZ': '赣锋锂业',
    '300476.SZ': '胜宏科技',
    # 常用大盘股
    '000001.SZ': '平安银行',
    '000002.SZ': '万科A',
    '000333.SZ': '美的集团',
    '000651.SZ': '格力电器',
    '000725.SZ': '京东方A',
    '000858.SZ': '五粮液',
    '002415.SZ': '海康威视',
    '002594.SZ': '比亚迪',
    '300750.SZ': '宁德时代',
    '600000.SH': '浦发银行',
    '600036.SH': '招商银行',
    '600519.SH': '贵州茅台',
    '600887.SH': '伊利股份',
    '601318.SH': '中国平安',
    '601398.SH': '工商银行',
    '601939.SH': '建设银行',
    '603259.SH': '药明康德',
    '688981.SH': '中芯国际',
    '688111.SH': '金山办公',
    '688012.SH': '中微公司',
    '688008.SH': '澜起科技',
    '688005.SH': '容百科技',
    '688006.SH': '奥特维',
    '688007.SH': '华峰测控',
    '688010.SH': '福光股份',
}

def get_stock_name(code):
    return STOCK_NAMES.get(code, code.split('.')[0])

app = Flask(__name__)

# 配置
DB_PATH = r'E:\股票\csi500_data\stocks.db'
CSV_PATH = r'e:\csi10\波段股票Top30.csv'
INDEX_CODE = 'sh.000300'  # 沪深300指数

# ========== 分析引擎（含大盘因子）==========
class AnalyzerV2:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.stock_pool = pd.read_csv(CSV_PATH)['股票代码'].tolist()
        self.models = {}
        self.analysis_results = []
        self.accuracy_report = {}
        self.last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.last_analysis_time = None
        
        # 加载大盘数据
        print("加载大盘数据...")
        self.index_data = self._load_index_data()
        
        print("训练模型（含大盘因子）...")
        self._train_models()
        print("分析股票...")
        self._analyze()
    
    def _load_index_data(self):
        """加载沪深300指数数据"""
        sql = '''
            SELECT date, close, pct_chg, ma5, ma10, ma20, macd, macd_hist, rsi6
            FROM index_daily 
            WHERE code = ?
            ORDER BY date DESC
            LIMIT 1000
        '''
        df = pd.read_sql_query(sql, self.conn, params=(INDEX_CODE,))
        
        if len(df) == 0:
            print("⚠️ 大盘数据为空")
            return None
        
        df = df.iloc[::-1].reset_index(drop=True)
        df['date'] = pd.to_datetime(df['date'])
        print(f"✓ 大盘数据: {len(df)}条 ({df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')})")
        return df
    
    def _train_models(self):
        """训练所有股票模型"""
        accuracies = []
        
        for code in self.stock_pool:
            try:
                sql = "SELECT * FROM daily_price WHERE code=? ORDER BY date DESC LIMIT 500"
                df = pd.read_sql_query(sql, self.conn, params=(code,))
                
                if len(df) < 100:
                    continue
                
                df = df.iloc[::-1].reset_index(drop=True)
                df['date'] = pd.to_datetime(df['date'])
                
                # 提取特征（含大盘因子）
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
                
                # 切分训练集/测试集
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                
                # 模型参数优化
                model = RandomForestClassifier(
                    n_estimators=100,     # 增加树数量
                    max_depth=6,          # 增加深度
                    min_samples_split=5,  # 最小分裂样本
                    min_samples_leaf=2,   # 最小叶子样本
                    random_state=42
                )
                model.fit(X_train, y_train)
                
                # 计算准确率
                y_pred = model.predict(X_test)
                acc = accuracy_score(y_test, y_pred)
                accuracies.append(acc)
                
                self.models[code] = {
                    'model': model,
                    'data': df,
                    'features': X.columns.tolist(),
                    'accuracy': acc
                }
                
            except Exception as e:
                print(f"{code}: {e}")
        
        # 计算平均准确率
        if accuracies:
            self.accuracy_report = {
                'avg': np.mean(accuracies),
                'min': np.min(accuracies),
                'max': np.max(accuracies),
                'count': len(accuracies)
            }
            print(f"✓ 平均准确率: {self.accuracy_report['avg']:.2%} (范围: {self.accuracy_report['min']:.2%} ~ {self.accuracy_report['max']:.2%})")
    
    def _extract_features(self, df, i):
        """提取特征 - 含大盘因子"""
        if i < 30 or i >= len(df) - 3:
            return None
        
        row = df.iloc[i]
        current_date = row['date']
        
        close = row['close'] if pd.notna(row['close']) else 0
        volume = row['volume'] if pd.notna(row['volume']) else 0
        pct_chg = row['pct_chg'] if pd.notna(row['pct_chg']) else 0
        ma5 = row['ma5'] if pd.notna(row['ma5']) else close
        ma10 = row['ma10'] if pd.notna(row['ma10']) else close
        ma20 = row['ma20'] if pd.notna(row['ma20']) else close
        rsi = row['rsi6'] if pd.notna(row['rsi6']) else 50
        macd = row['macd'] if pd.notna(row['macd']) else 0
        macd_hist = row.get('macd_hist', 0) if pd.notna(row.get('macd_hist', 0)) else 0
        
        feat = {}
        
        # === 个股技术指标（原版）===
        feat['ma5_ratio'] = close/ma5 if ma5 > 0 else 1
        feat['ma10_ratio'] = close/ma10 if ma10 > 0 else 1
        feat['ma20_ratio'] = close/ma20 if ma20 > 0 else 1
        feat['ma5_ma10_diff'] = (ma5 - ma10)/ma10 if ma10 > 0 else 0
        feat['rsi'] = rsi
        feat['macd'] = macd
        feat['macd_hist'] = macd_hist
        feat['macd_signal'] = 1 if macd > 0 and macd_hist > 0 else 0
        feat['pct_chg'] = pct_chg
        
        # 量价关系
        if i >= 20:
            vol_ma = df.iloc[i-20:i]['volume'].mean()
            feat['vol_ratio'] = volume/vol_ma if vol_ma > 0 else 1
        else:
            feat['vol_ratio'] = 1
        
        # 波动率
        if i >= 20:
            closes = df.iloc[i-20:i+1]['close'].values
            returns = np.diff(closes)/closes[:-1]
            feat['volatility'] = np.std(returns) * 100
        else:
            feat['volatility'] = 2
        
        # 价格位置
        if i >= 60:
            high_60 = df.iloc[i-60:i+1]['close'].max()
            low_60 = df.iloc[i-60:i+1]['close'].min()
            feat['price_position'] = (close - low_60)/(high_60 - low_60) if high_60 > low_60 else 0.5
        else:
            feat['price_position'] = 0.5
        
        # 近3日涨跌
        if i >= 3:
            pct_list = df.iloc[i-3:i]['pct_chg'].values
            feat['up_days'] = len([p for p in pct_list if p > 0])
            feat['down_days'] = len([p for p in pct_list if p < 0])
            feat['total_pct_3d'] = sum(pct_list)
        else:
            feat['up_days'] = 0
            feat['down_days'] = 0
            feat['total_pct_3d'] = 0
        
        # === 新增：大盘因子 ===
        if self.index_data is not None:
            idx_row = self.index_data[self.index_data['date'] == current_date]
            
            if len(idx_row) > 0:
                idx = idx_row.iloc[0]
                feat['index_pct_chg'] = idx['pct_chg'] if pd.notna(idx['pct_chg']) else 0
                feat['index_ma5_ratio'] = idx['close']/idx['ma5'] if pd.notna(idx['ma5']) and idx['ma5'] > 0 else 1
                feat['index_rsi6'] = idx['rsi6'] if pd.notna(idx['rsi6']) else 50
                feat['index_macd'] = idx['macd'] if pd.notna(idx['macd']) else 0
                feat['index_macd_hist'] = idx['macd_hist'] if pd.notna(idx['macd_hist']) else 0
                feat['stock_vs_index'] = pct_chg - feat['index_pct_chg']
            else:
                feat['index_pct_chg'] = 0
                feat['index_ma5_ratio'] = 1
                feat['index_rsi6'] = 50
                feat['index_macd'] = 0
                feat['index_macd_hist'] = 0
                feat['stock_vs_index'] = 0
        else:
            feat['index_pct_chg'] = 0
            feat['index_ma5_ratio'] = 1
            feat['index_rsi6'] = 50
            feat['index_macd'] = 0
            feat['index_macd_hist'] = 0
            feat['stock_vs_index'] = 0
        
        # 目标：3日涨幅≥3%
        close_3d = df.iloc[i+3]['close']
        rise_3d = (close_3d - close)/close if close > 0 else 0
        feat['target'] = 1 if rise_3d >= 0.03 else 0
        
        return feat
    
    def _analyze(self):
        """分析所有股票"""
        self.analysis_results = []
        for code in self.stock_pool:
            pred = self._predict(code)
            if pred:
                self.analysis_results.append(pred)
        self.analysis_results.sort(key=lambda x: x['score'], reverse=True)
        self.last_analysis_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _predict(self, code):
        """预测单只股票"""
        if code not in self.models:
            # 返回默认值
            sql = "SELECT * FROM daily_price WHERE code=? ORDER BY date DESC LIMIT 1"
            df = pd.read_sql_query(sql, self.conn, params=(code,))
            if len(df) == 0:
                return None
            row = df.iloc[0]
            
            rsi_val = row['rsi6'] if pd.notna(row['rsi6']) else 50
            macd_val = row['macd'] if pd.notna(row['macd']) else 0
            change_val = row['pct_chg'] if pd.notna(row['pct_chg']) else 0
            price_val = row['close'] if pd.notna(row['close']) else 0
            
            return {
                'code': code,
                'name': get_stock_name(code),
                'price': float(price_val),
                'change_pct': float(change_val),
                'rsi': float(rsi_val),
                'macd': float(macd_val),
                'probability': 0.5,
                'action': '持有',
                'confidence': '低',
                'score': 50,
                'accuracy': 0
            }
        
        m = self.models[code]
        model = m['model']
        df = m['data']
        features = m['features']
        
        # 提取最新特征
        latest_feat = self._extract_features(df, len(df) - 4)
        if latest_feat is None:
            return None
        
        X = pd.DataFrame([latest_feat])
        X = X[features]
        
        prob = model.predict_proba(X)[0, 1] if len(model.classes_) > 1 else 0.5
        
        action = '买入' if prob >= 0.6 else '卖出' if prob <= 0.3 else '持有'
        conf = '高' if prob >= 0.7 or prob <= 0.25 else '中' if prob >= 0.55 or prob <= 0.4 else '低'
        
        row = df.iloc[-1]
        rsi_val = row['rsi6'] if pd.notna(row['rsi6']) else 50
        macd_val = row['macd'] if pd.notna(row['macd']) else 0
        change_val = row['pct_chg'] if pd.notna(row['pct_chg']) else 0
        
        return {
            'code': code,
            'name': get_stock_name(code),
            'price': float(row['close']) if pd.notna(row['close']) else 0,
            'change_pct': float(change_val),
            'rsi': float(rsi_val),
            'macd': float(macd_val),
            'probability': float(prob),
            'action': action,
            'confidence': conf,
            'score': int(prob * 100),
            'accuracy': m['accuracy']
        }
    
    def refresh(self):
        """刷新数据"""
        self.last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.index_data = self._load_index_data()
        self._analyze()
        return {'status': 'success', 'time': self.last_analysis_time}
    
    def get_all(self): return self.analysis_results
    def get_buy(self, n=5): return [x for x in self.analysis_results if x['action']=='买入'][:n]
    def get_sell(self): return [x for x in self.analysis_results if x['action']=='卖出']
    def get_accuracy(self): return self.accuracy_report
    
    def get_report(self, code):
        """生成详细技术报告"""
        try:
            sql = "SELECT * FROM daily_price WHERE code=? ORDER BY date DESC LIMIT 120"
            df = pd.read_sql_query(sql, self.conn, params=(code,))
            
            if len(df) == 0:
                return {'error': '股票不存在', 'code': code}
            
            df = df.iloc[::-1]
            latest = df.iloc[-1]
            
            close = latest['close'] if pd.notna(latest['close']) else 0
            volume = latest['volume'] if pd.notna(latest['volume']) else 0
            pct_chg = latest['pct_chg'] if pd.notna(latest['pct_chg']) else 0
            ma5 = latest['ma5'] if pd.notna(latest['ma5']) else close
            ma10 = latest['ma10'] if pd.notna(latest['ma10']) else close
            ma20 = latest['ma20'] if pd.notna(latest['ma20']) else close
            rsi = latest['rsi6'] if pd.notna(latest['rsi6']) else 50
            macd = latest['macd'] if pd.notna(latest['macd']) else 0
            
            recent_20 = df.iloc[-20:] if len(df) >= 20 else df
            avg_vol_20 = recent_20['volume'].mean() if len(recent_20) > 0 else volume
            max_close_20 = recent_20['close'].max() if len(recent_20) > 0 else close
            min_close_20 = recent_20['close'].min() if len(recent_20) > 0 else close
            
            support = float(min_close_20)
            resistance = float(max_close_20)
            
            trend = '上升趋势' if close > ma5 and ma5 > ma10 and ma10 > ma20 else \
                    '下降趋势' if close < ma5 and ma5 < ma10 and ma10 < ma20 else '震荡趋势'
            
            rsi_signal = '超买' if rsi > 80 else '超卖' if rsi < 20 else '中性'
            macd_signal = '多头' if macd > 0 else '空头' if macd < 0 else '中性'
            
            closes = df['close'].dropna().values[-30:]
            if len(closes) > 1:
                returns = np.diff(closes) / closes[:-1]
                volatility_30 = float(np.std(returns) * 100)
            else:
                volatility_30 = 0.0
            
            # 大盘对比
            index_info = {}
            if self.index_data is not None and len(self.index_data) > 0:
                idx_latest = self.index_data.iloc[-1]
                index_info = {
                    'index_close': float(idx_latest['close']) if pd.notna(idx_latest['close']) else 0,
                    'index_pct_chg': float(idx_latest['pct_chg']) if pd.notna(idx_latest['pct_chg']) else 0,
                    'index_rsi': float(idx_latest['rsi6']) if pd.notna(idx_latest['rsi6']) else 50,
                    'stock_vs_index': float(pct_chg - idx_latest['pct_chg']) if pd.notna(idx_latest['pct_chg']) else 0
                }
            
            return {
                'code': code,
                'name': get_stock_name(code),
                'current_price': float(close),
                'change_today': float(pct_chg),
                'volume': int(volume),
                'avg_volume_20': float(avg_vol_20) if pd.notna(avg_vol_20) else float(volume),
                'vol_ratio': float(volume / avg_vol_20) if avg_vol_20 > 0 else 1.0,
                
                'ma5': float(ma5),
                'ma10': float(ma10),
                'ma20': float(ma20),
                'trend': trend,
                
                'support': support,
                'resistance': resistance,
                'distance_support': float((close - support) / support * 100) if support > 0 else 0,
                'distance_resistance': float((resistance - close) / close * 100) if close > 0 else 0,
                
                'rsi': float(rsi),
                'rsi_signal': rsi_signal,
                'macd': float(macd),
                'macd_signal': macd_signal,
                'volatility_30': volatility_30,
                
                'index_info': index_info,
                
                'data_days': len(df),
                'latest_date': str(latest['date']),
                
                'suggestion': self._generate_suggestion(trend, rsi_signal, macd_signal, close, support, resistance, index_info)
            }
        except Exception as e:
            return {'error': str(e), 'code': code}
    
    def _generate_suggestion(self, trend, rsi_signal, macd_signal, close, support, resistance, index_info):
        """生成操作建议（含大盘判断）"""
        try:
            close = float(close) if pd.notna(close) else 0
            support = float(support) if pd.notna(support) else 0
            resistance = float(resistance) if pd.notna(resistance) else 0
            
            # 大盘判断
            index_pct = index_info.get('index_pct_chg', 0)
            index_rsi = index_info.get('index_rsi', 50)
            
            # 大盘超买或大跌时谨慎
            if index_rsi > 80 or index_pct < -2:
                return f'大盘风险较高（RSI={index_rsi:.0f}, 跌{index_pct:.1f}%），建议观望'
            
            # 大盘正常时按个股信号操作
            if trend == '上升趋势' and rsi_signal != '超买':
                return '建议买入，趋势向上且未超买，大盘稳定'
            elif trend == '下降趋势' and rsi_signal != '超卖':
                return '建议卖出，趋势向下'
            elif support > 0 and close <= support * 1.02 and rsi_signal == '超卖':
                return '接近支撑位且超卖，可考虑低吸'
            elif resistance > 0 and close >= resistance * 0.98 and rsi_signal == '超买':
                return '接近压力位且超买，可考虑高抛'
            else:
                return '震荡行情，建议观望或轻仓操作'
        except:
            return '建议观望'

# 初始化
print("="*60)
print("波段股票分析系统 v2.0 (含大盘因子优化)")
print("="*60)
analyzer = AnalyzerV2()
print("="*60)

# ========== API路由 ==========

@app.route('/api/status')
def api_status():
    return jsonify({
        'update_time': analyzer.last_update,
        'analysis_time': analyzer.last_analysis_time,
        'stock_count': len(analyzer.analysis_results),
        'buy_count': len([x for x in analyzer.analysis_results if x['action']=='买入']),
        'sell_count': len([x for x in analyzer.analysis_results if x['action']=='卖出']),
        'avg_accuracy': analyzer.accuracy_report.get('avg', 0),
        'feature_count': 22,  # 16个股 + 6大盘
        'version': 'v2.0-optimized'
    })

@app.route('/api/accuracy')
def api_accuracy():
    return jsonify(analyzer.get_accuracy())

@app.route('/api/refresh')
def api_refresh():
    return jsonify(analyzer.refresh())

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
    return jsonify(analyzer.get_report(code))

# ========== HTML模板 ==========

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>波段股票分析 v2.0 (含大盘因子)</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei';background:#1a1a2e;color:#fff;padding:20px}
.header{text-align:center;margin-bottom:20px;padding:20px;background:rgba(255,255,255,0.1);border-radius:15px}
.accuracy-box{background:rgba(102,126,234,0.2);padding:15px;border-radius:10px;margin:10px 0;text-align:center}
.accuracy-value{font-size:28px;color:#764ba2;font-weight:bold}
.refresh-btn{padding:10px 25px;background:linear-gradient(135deg,#667eea,#764ba2);border:none;border-radius:20px;color:#fff;cursor:pointer;margin:5px}
.refresh-btn:hover{transform:scale(1.05)}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}
.panel{background:rgba(255,255,255,0.05);border-radius:15px;padding:20px}
.panel-header{display:flex;justify-content:space-between;margin-bottom:15px;border-bottom:2px solid rgba(255,255,255,0.1)}
.card{background:rgba(255,255,255,0.08);border-radius:10px;padding:15px;margin:10px 0}
.card.buy{background:rgba(16,185,129,0.2);border-left:4px solid #10b981}
.card.sell{background:rgba(239,68,68,0.2);border-left:4px solid #ef4444}
.badge{padding:5px 15px;border-radius:15px;font-weight:bold}
.badge.buy{background:#10b981}
.badge.sell{background:#ef4444}
.badge.hold{background:#3b82f6}
.score-bar{height:6px;background:rgba(255,255,255,0.1);border-radius:3px;margin-top:5px}
.score-fill{height:100%;background:linear-gradient(90deg,#667eea,#764ba2);border-radius:3px}
@media(max-width:1200px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="header">
<h1>📊 波段股票分析系统 v2.0 (含大盘因子)</h1>
<div id="time">数据: {{update}} | 分析: {{analysis}}</div>
<div class="accuracy-box">
<h2>模型准确率</h2>
<div class="accuracy-value" id="accuracy">-</div>
<div id="accuracy-range">-</div>
</div>
<button class="refresh-btn" onclick="refreshAll()">🔄 全局刷新</button>
</div>
<div class="grid">
<div class="panel">
<div class="panel-header"><span>📈 30只股票池</span><button class="refresh-btn" onclick="refreshPool()">刷新</button></div>
<div id="pool"></div>
</div>
<div class="panel">
<div class="panel-header"><span>🎯 买入推荐</span><button class="refresh-btn" onclick="refreshBuy()">刷新</button></div>
<div id="buy"></div>
</div>
<div class="panel">
<div class="panel-header"><span>⚠️ 卖出信号</span><button class="refresh-btn" onclick="refreshSell()">刷新</button></div>
<div id="sell"></div>
</div>
</div>
<script>
function refreshAll(){fetch('/api/refresh').then(r=>r.json()).then(d=>{if(d.status==='success')location.reload()})}
function refreshPool(){fetch('/api/all').then(r=>r.json()).then(renderPool)}
function refreshBuy(){fetch('/api/buy').then(r=>r.json()).then(renderBuy)}
function refreshSell(){fetch('/api/sell').then(r=>r.json()).then(renderSell)}
function renderPool(d){document.getElementById('pool').innerHTML=d.map(s=>`<div class="card ${s.action.toLowerCase()}"><span>${s.code} ${s.name}</span> ¥${s.price.toFixed(2)} <span class="badge ${s.action.toLowerCase()}">${s.action}</span><div>准确率:${(s.accuracy*100).toFixed(0)}% 评分:${s.score}</div><div class="score-bar"><div class="score-fill" style="width:${s.score}%"></div></div></div>`).join('')}
function renderBuy(d){document.getElementById('buy').innerHTML=d.map(s=>`<div class="card buy"><span>${s.code} ${s.name}</span> ¥${s.price.toFixed(2)} <span class="badge buy">买入</span><div>评分:${s.score} 置信度:${s.confidence} 准确率:${(s.accuracy*100).toFixed(0)}%</div></div>`).join('')||'<div style="padding:20px;color:#888">暂无信号</div>'}
function renderSell(d){document.getElementById('sell').innerHTML=d.map(s=>`<div class="card sell"><span>${s.code} ${s.name}</span> ¥${s.price.toFixed(2)} <span class="badge sell">卖出</span><div>置信度:${s.confidence}</div></div>`).join('')||'<div style="padding:20px;color:#888">暂无信号</div>'}
fetch('/api/all').then(r=>r.json()).then(renderPool)
fetch('/api/buy').then(r=>r.json()).then(renderBuy)
fetch('/api/sell').then(r=>r.json()).then(renderSell)
fetch('/api/status').then(r=>r.json()).then(d=>document.getElementById('time').textContent=`数据:${d.update_time}|分析:${d.analysis_time}`)
fetch('/api/accuracy').then(r=>r.json()).then(d=>{
  if(d.avg){
    document.getElementById('accuracy').textContent=(d.avg*100).toFixed(1)+'%'
    document.getElementById('accuracy-range').textContent=`范围: ${(d.min*100).toFixed(1)}% ~ ${(d.max*100).toFixed(1)}% (${d.count}只股票)`
  }
})
</script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML, 
        update=analyzer.last_update, 
        analysis=analyzer.last_analysis_time)

if __name__ == '__main__':
    print("访问: http://localhost:5000")
    app.run(debug=False, port=5000, threaded=True)