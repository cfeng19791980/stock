# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import buysell_predictor_v5

print("测试买点卖点预测器...")
predictor = buysell_predictor_v5.BuySellPredictor()
predictor.train_models()

# 测试预测
test_codes = ['688028.SH', '605196.SH', '002353.SZ']
for code in test_codes:
    try:
        buy, sell = predictor.predict(code)
        print(f"{code}: buy={buy}, sell={sell}")
    except Exception as e:
        print(f"{code}: 预测失败 - {e}")