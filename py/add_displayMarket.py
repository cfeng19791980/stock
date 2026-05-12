# -*- coding: utf-8 -*-
"""添加displayMarket函数"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

displayMarket_func = '''
        // 显示大盘信息
        function displayMarket(data) {
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
            
            // 显示评分调整示例
            const adjustEl = document.getElementById('adjustExamples');
            if (adjustEl && data.stocks) {
                const samples = data.stocks.slice(0, 5);
                adjustEl.innerHTML = samples.map(s => {
                    const change = s.adjusted_score - s.score;
                    const changeClass = change > 0 ? 'market-strong' : change < 0 ? 'market-weak' : 'market-neutral';
                    return `<div class="market-adjust-row">
                        ${s.name}: 原评分${s.score} → 调整后<span class="${changeClass}">${s.adjusted_score}</span> (${change >= 0 ? '+' : ''}${change})
                    </div>`;
                }).join('');
            }
        }
'''

# 读取文件
with open(r'e:\csi10\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 在displayReport之前插入
if 'function displayMarket' not in content:
    # 找到displayReport位置
    pos = content.find('// 显示详细报告\n        function displayReport')
    if pos > 0:
        content = content[:pos] + displayMarket_func + '\n' + content[pos:]
        print("✓ displayMarket函数已添加")
    else:
        print("❌ 未找到插入位置")
else:
    print("✓ displayMarket函数已存在")

# 写回文件
with open(r'e:\csi10\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ index.html更新完成")

# 验证
with open(r'e:\csi10\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"\n验证: displayMarket函数存在 = {'function displayMarket' in content}")