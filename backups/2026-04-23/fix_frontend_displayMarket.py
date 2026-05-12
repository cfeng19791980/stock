# -*- coding: utf-8 -*-
"""修复index.html displayMarket函数 - 显示8卡片+indices面板"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 读取index.html
with open(r'E:\csi10\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到displayMarket函数并完整替换
old_displayMarket_start = 'function displayMarket(data) {'
old_displayMarket_end = '        } // 显示详细报告'

# 新的完整displayMarket函数
new_displayMarket = '''function displayMarket(data) {
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
            if (profitEl) profitEl.textContent = '+' + (market.stop_profit || 20) + '%';
            if (lossEl) lossEl.textContent = (market.stop_loss || -10) + '%';
            if (positionEl) positionEl.textContent = (market.suggest_position || 15) + '%';
            
            // 多指数对比面板
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
            
            if (divergenceEl) {
                const divergence = indices.divergence || 0;
                divergenceEl.textContent = divergence.toFixed(2) + '%';
                divergenceEl.className = 'indices-value ' + (divergence >= 1 ? 'negative' : 'positive');
            }
            
            if (dominantEl) {
                dominantEl.textContent = (indices.dominant || '大盘股') + '主导';
            }

            // 显示最近5日走势
            const chartEl = document.getElementById('marketChartContent');
            if (chartEl && market.recent_5d) {
                chartEl.innerHTML = market.recent_5d.map(r => {
                    const pctClass = r.pct_chg >= 0 ? 'market-strong' : 'market-weak';
                    return `<div class="market-chart-row">
                        <span class="market-chart-date">${r.date}</span>
                        <span class="market-chart-close">${r.close.toFixed(2)}</span>
                        <span class="market-chart-pct ${pctClass}">${r.pct_chg.toFixed(2)}%</span>
                    </div>`;
                }).join('');
            }

            // 显示调整示例
            const adjustEl = document.getElementById('adjustExamples');
            if (adjustEl && data.stocks) {
                const samples = data.stocks.slice(0, 5);
                adjustEl.innerHTML = samples.map(s => {
                    const adjScore = s.adjusted_score || s.score;
                    const change = adjScore - s.score;
                    const changeClass = change > 0 ? 'market-strong' : change < 0 ? 'market-weak' : 'market-neutral';
                    return `<div class="market-adjust-row">
                        ${s.name}: 原评分${s.score} → 调整后<span class="${changeClass}">${adjScore}</span> (${change >= 0 ? '+' : ''}${change})
                    </div>`;
                }).join('');
            }
        }'''

# 使用正则找到函数
import re
pattern = r'function displayMarket\(data\) \{.*?\} // 显示详细报告'
match = re.search(pattern, content, re.DOTALL)

if match:
    content = content[:match.start()] + new_displayMarket + '\n' + content[match.end():]
    print("✓ displayMarket function replaced")
else:
    print("✗ Pattern not found, trying manual replacement")
    # 手动查找并替换
    start_idx = content.find(old_displayMarket_start)
    if start_idx > 0:
        # 找到函数结束位置
        end_idx = content.find(old_displayMarket_end, start_idx)
        if end_idx > 0:
            content = content[:start_idx] + new_displayMarket + '\n' + content[end_idx:]
            print("✓ displayMarket replaced manually")

# 写回文件
with open(r'E:\csi10\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ index.html fixed!")
print("Next: Verify displayMarket function in browser")