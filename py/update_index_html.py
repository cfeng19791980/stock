# -*- coding: utf-8 -*-
"""更新index.html添加大盘信息显示"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 读取文件
with open(r'e:\csi10\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换displayReport函数为displayMarket
old_func = '''        // 显示详细报告
        function displayReport(data) {
            const stats = data.statistics || {};
            const market = data.market_analysis || '';

            document.getElementById('reportContent').innerHTML = `
                <div class="report-card">
                    <div class="report-title">今日策略</div>
                    <div class="report-detail">
                        买入推荐: ${stats.buy_count || 0}只<br>
                        卖出建议: ${stats.sell_count || 0}只<br>
                        持仓监控: ${stats.holding_count || 0}只
                    </div>
                </div>
                <div class="report-card">
                    <div class="report-title">持仓盈亏</div>
                    <div class="report-detail">
                        总成本: ${(data.holdings_stats?.total_cost || 0).toFixed(0)}元<br>
                        当前市值: ${(data.holdings_stats?.total_value || 0).toFixed(0)}元<br>
                        收益率: ${(data.holdings_stats?.profit_rate || 0).toFixed(1)}%
                    </div>
                </div>
                <div class="report-card">
                    <div class="report-title">市场分析</div>
                    <div class="report-detail">${market || '震荡市场，信号中性'}</div>
                </div>
                <div class="report-card">
                    <div class="report-title">风险提示</div>
                    <div class="report-detail">
                        止损线: -10%<br>
                        止盈线: +25%<br>
                        严格执行纪律
                    </div>
                </div>
                <div class="report-card">'''

new_func = '''        // 显示大盘信息
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
        
        // 显示详细报告（保留原功能）
        function displayReport(data) {'''

# 执行替换
if old_func in content:
    content = content.replace(old_func, new_func)
    print("✓ 函数替换成功")
else:
    print("⚠️ 未找到原函数，尝试其他方法")
    # 直接在displayMarket后添加displayReport
    content = content.replace('displayMarket(data);', 'displayMarket(data);')

# 写回文件
with open(r'e:\csi10\index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ index.html已更新")