# -*- coding: utf-8 -*-
"""升级index.html前端界面 - 丰富大盘走势信息"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 读取index.html
with open(r'E:\csi10\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: 添加更多market-card（卖出阈值、止盈止损、建议仓位）
old_market_grid = '''            <div class="market-grid" id="marketGrid">
                <div class="market-card">
                    <div class="market-card-label">市场状态</div>
                    <div class="market-card-value" id="marketStatus">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">5日涨跌</div>
                    <div class="market-card-value" id="marketPct">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">调整因子</div>
                    <div class="market-card-value" id="marketFactor">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">买入阈值</div>
                    <div class="market-card-value" id="marketThreshold">--</div>
                </div>
            </div>'''

new_market_grid = '''            <div class="market-grid" id="marketGrid">
                <div class="market-card">
                    <div class="market-card-label">市场状态</div>
                    <div class="market-card-value" id="marketStatus">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">综合涨跌</div>
                    <div class="market-card-value" id="marketPct">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">调整因子</div>
                    <div class="market-card-value" id="marketFactor">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">买入阈值</div>
                    <div class="market-card-value" id="marketThreshold">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">卖出阈值</div>
                    <div class="market-card-value" id="sellThreshold">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">止盈线</div>
                    <div class="market-card-value" id="stopProfit">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">止损线</div>
                    <div class="market-card-value" id="stopLoss">--</div>
                </div>
                <div class="market-card">
                    <div class="market-card-label">建议仓位</div>
                    <div class="market-card-value" id="suggestPosition">--</div>
                </div>
            </div>
            
            <!-- 多指数对比面板 -->
            <div class="indices-panel">
                <div class="indices-title">📊 多指数对比</div>
                <div class="indices-grid" id="indicesGrid">
                    <div class="indices-card">
                        <div class="indices-label">沪深300</div>
                        <div class="indices-value" id="hs300Pct">--</div>
                        <div class="indices-detail" id="hs300Latest">--</div>
                    </div>
                    <div class="indices-card">
                        <div class="indices-label">中证500</div>
                        <div class="indices-value" id="zz500Pct">--</div>
                        <div class="indices-detail" id="zz500Latest">--</div>
                    </div>
                    <div class="indices-card">
                        <div class="indices-label">分歧度</div>
                        <div class="indices-value" id="divergence">--</div>
                        <div class="indices-detail" id="dominant">--</div>
                    </div>
                </div>
            </div>'''

content = content.replace(old_market_grid, new_market_grid)
print("✓ Market grid enhanced with 8 cards + indices panel")

# Step 2: 添加indices-panel CSS样式
old_style = '''        .market-chart {'''

new_style = '''        /* 多指数对比面板 */
        .indices-panel {
            background: linear-gradient(135deg, rgba(59,130,246,0.1) 0%, rgba(99,102,241,0.1) 100%);
            border: 1px solid rgba(59,130,246,0.3);
            border-radius: 12px;
            padding: 15px;
            margin-top: 15px;
        }
        .indices-title {
            font-size: 14px;
            color: #3b82f6;
            margin-bottom: 10px;
            font-weight: 600;
        }
        .indices-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }
        .indices-card {
            background: rgba(255,255,255,0.8);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        .indices-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        .indices-value {
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }
        .indices-value.positive { color: #10b981; }
        .indices-value.negative { color: #ef4444; }
        .indices-detail {
            font-size: 10px;
            color: #888;
            margin-top: 3px;
        }
        
        .market-chart {'''

content = content.replace(old_style, new_style)
print("✓ Indices panel CSS added")

# Step 3: 增强displayMarket函数
old_display_market = '''function displayMarket(data) {
            const market = data.market || {};

            // 显示市场状态
            const statusEl = document.getElementById('marketStatus');
            const pctEl = document.getElementById('marketPct');
            const factorEl = document.getElementById('marketFactor');
            const thresholdEl = document.getElementById('marketThreshold');

            if (statusEl) {
                const status = market.status || '震荡市场';
                statusEl.textContent = status;
                statusEl.className = 'market-card-value ' +
                    (status.includes('强') ? 'market-strong' : status.includes('弱') ? 'market-weak' : 'market-neutral');
            }

            if (pctEl) {
                const pct = market.pct_5d || 0;
                pctEl.textContent = pct.toFixed(2) + '%';
                pctEl.className = 'market-card-value ' +
                    (pct >= 1 ? 'market-strong' : pct <= -1 ? 'market-weak' : 'market-neutral');
            }

            if (factorEl) {
                const factor = market.factor || 1.0;
                factorEl.textContent = factor.toFixed(2);
                factorEl.className = 'market-card-value ' +
                    (factor > 1 ? 'market-strong' : factor < 1 ? 'market-weak' : 'market-neutral');
            }

            if (thresholdEl) {
                thresholdEl.textContent = (market.threshold || 60) + '分';
                thresholdEl.className = 'market-card-value market-neutral';
            }'''

new_display_market = '''function displayMarket(data) {
            const market = data.market || {};

            // 显示市场状态（8卡片）
            const statusEl = document.getElementById('marketStatus');
            const pctEl = document.getElementById('marketPct');
            const factorEl = document.getElementById('marketFactor');
            const thresholdEl = document.getElementById('marketThreshold');
            const sellEl = document.getElementById('sellThreshold');
            const profitEl = document.getElementById('stopProfit');
            const lossEl = document.getElementById('stopLoss');
            const positionEl = document.getElementById('suggestPosition');

            if (statusEl) {
                const status = market.status || '震荡市场';
                statusEl.textContent = status;
                statusEl.className = 'market-card-value ' +
                    (status.includes('强') ? 'market-strong' : status.includes('弱') ? 'market-weak' : 'market-neutral');
            }

            if (pctEl) {
                const pct = market.pct_5d || 0;
                pctEl.textContent = pct.toFixed(2) + '%';
                pctEl.className = 'market-card-value ' +
                    (pct >= 1 ? 'market-strong' : pct <= -1 ? 'market-weak' : 'market-neutral');
            }

            if (factorEl) {
                const factor = market.factor || 1.0;
                factorEl.textContent = factor.toFixed(2);
                factorEl.className = 'market-card-value ' +
                    (factor > 1 ? 'market-strong' : factor < 1 ? 'market-weak' : 'market-neutral');
            }

            if (thresholdEl) {
                thresholdEl.textContent = (market.buy_threshold || 60) + '分';
                thresholdEl.className = 'market-card-value market-neutral';
            }
            
            // 新增4卡片
            if (sellEl) sellEl.textContent = (market.sell_threshold || 15) + '分';
            if (profitEl) profitEl.textContent = '+' + (market.stop_profit || 25) + '%';
            if (lossEl) lossEl.textContent = (market.stop_loss || -10) + '%';
            if (positionEl) positionEl.textContent = (market.suggest_position || 15) + '%';
            
            // 多指数对比
            const indices = market.indices || {};
            const hs300PctEl = document.getElementById('hs300Pct');
            const zz500PctEl = document.getElementById('zz500Pct');
            const divergenceEl = document.getElementById('divergence');
            const hs300LatestEl = document.getElementById('hs300Latest');
            const zz500LatestEl = document.getElementById('zz500Latest');
            const dominantEl = document.getElementById('dominant');
            
            if (hs300PctEl && indices.hs300) {
                const hs300_pct = indices.hs300.pct_5d || 0;
                hs300PctEl.textContent = hs300_pct.toFixed(2) + '%';
                hs300PctEl.className = 'indices-value ' + (hs300_pct >= 0 ? 'positive' : 'negative');
                if (hs300LatestEl) hs300LatestEl.textContent = '最新: ' + (indices.hs300.latest || 0).toFixed(2);
            }
            
            if (zz500PctEl && indices.zz500) {
                const zz500_pct = indices.zz500.pct_5d || 0;
                zz500PctEl.textContent = zz500_pct.toFixed(2) + '%';
                zz500PctEl.className = 'indices-value ' + (zz500_pct >= 0 ? 'positive' : 'negative');
                if (zz500LatestEl) zz500LatestEl.textContent = '最新: ' + (indices.zz500.latest || 0).toFixed(2);
            }
            
            if (divergenceEl && indices.divergence !== undefined) {
                divergenceEl.textContent = indices.divergence.toFixed(2) + '%';
                divergenceEl.className = 'indices-value ' + (indices.divergence >= 1 ? 'negative' : 'positive');
            }
            
            if (dominantEl && indices.dominant) {
                dominantEl.textContent = indices.dominant + '主导';
            }'''

content = content.replace(old_display_market, new_display_market)
print("✓ displayMarket function enhanced")

# 写回文件
with open(r'E:\csi10\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ index.html upgraded successfully!")
print("Next: Test frontend to verify changes")