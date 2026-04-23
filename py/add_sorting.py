# -*- coding: utf-8 -*-
"""
修改index.html添加排序功能
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

filepath = r'e:\csi10\index.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 修改renderStockPool函数（添加排序）
old_renderStockPool = '''        function renderStockPool(stocks) {
            const container = document.getElementById('stock-pool');
            document.getElementById('pool-count').textContent = `${stocks.length}只`;
            
            if (!stocks || stocks.length === 0) {
                container.innerHTML = '<div class="empty-state">暂无数据</div>';
                return;
            }
            
            container.innerHTML = stocks.map(s => {'''

new_renderStockPool = '''        function renderStockPool(stocks) {
            const container = document.getElementById('stock-pool');
            document.getElementById('pool-count').textContent = `${stocks.length}只`;
            
            if (!stocks || stocks.length === 0) {
                container.innerHTML = '<div class="empty-state">暂无数据</div>';
                return;
            }
            
            // 排序：买入信号优先，然后按评分降序
            const sorted = stocks.sort((a, b) => {
                if (a.action === '买入' && b.action !== '买入') return -1;
                if (a.action !== '买入' && b.action === '买入') return 1;
                if (a.action === '卖出' && b.action === '持有') return -1;
                if (a.action === '持有' && b.action === '卖出') return 1;
                return b.score - a.score;
            });
            
            container.innerHTML = sorted.map(s => {'''

content = content.replace(old_renderStockPool, new_renderStockPool)

# 修改renderBuyList函数（添加排序）
old_renderBuyList = '''        function renderBuyList(stocks) {
            const container = document.getElementById('buy-list');
            document.getElementById('buy-count').textContent = `TOP ${stocks.length}`;
            
            if (!stocks || stocks.length === 0) {
                container.innerHTML = '<div class="empty-state">今日暂无买入信号</div>';
                return;
            }
            
            container.innerHTML = stocks.map((s, i) =>'''

new_renderBuyList = '''        function renderBuyList(stocks) {
            const container = document.getElementById('buy-list');
            document.getElementById('buy-count').textContent = `TOP ${stocks.length}`;
            
            if (!stocks || stocks.length === 0) {
                container.innerHTML = '<div class="empty-state">今日暂无买入信号</div>';
                return;
            }
            
            // 排序：按评分降序
            const sorted = stocks.sort((a, b) => b.score - a.score);
            
            container.innerHTML = sorted.map((s, i) =>'''

content = content.replace(old_renderBuyList, new_renderBuyList)

# 修改renderSellList函数（添加排序）
old_renderSellList = '''        function renderSellList(stocks) {
            const container = document.getElementById('sell-list');
            document.getElementById('sell-count').textContent = `${stocks.length}只`;
            
            if (!stocks || stocks.length === 0) {
                container.innerHTML = '<div class="empty-state">今日暂无卖出信号</div>';
                return;
            }
            
            container.innerHTML = stocks.map(s =>'''

new_renderSellList = '''        function renderSellList(stocks) {
            const container = document.getElementById('sell-list');
            document.getElementById('sell-count').textContent = `${stocks.length}只`;
            
            if (!stocks || stocks.length === 0) {
                container.innerHTML = '<div class="empty-state">今日暂无卖出信号</div>';
                return;
            }
            
            // 排序：按评分降序（跌幅置信度高的排前面）
            const sorted = stocks.sort((a, b) => b.score - a.score);
            
            container.innerHTML = sorted.map((s, i) =>'''

content = content.replace(old_renderSellList, new_renderSellList)

# 保存修改后的文件
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 排序功能已添加！")
print("\n排序规则：")
print("  1. 股票池：买入信号优先 → 卖出信号 → 持有信号 → 按评分降序")
print("  2. 买入推荐：按评分降序（评分越高，买入置信度越高）")
print("  3. 卖出推荐：按评分降序（评分越高，跌幅置信度越高）")
print("\n文件已保存: e:\\csi10\\index.html")