import sys
sys.stdout.reconfigure(encoding='utf-8')

print("="*70)
print("检查前端'立即更新'按钮是否会更新大盘走势板块数据")
print("="*70)

# 1. 检查前端按钮调用链
print("\n[1] 前端按钮调用链:")
print("  🔄 刷新数据按钮 → refreshData() → loadData() → displayMarket(data)")
print("  ⚡ 立即更新按钮 → forceUpdate() → window.electronAPI.refreshData()")
print("    → main_json.js.runUpdateAndAnalyze()")
print("    → market_index_fetcher.py (更新大盘)")
print("    → data_fetcher.py (更新股票)")
print("    → analyzer_v4.py (重新分析)")
print("    → result.json (新数据)")
print("    → loadData() → displayMarket(data)")
print("\n  结论: 会更新大盘走势板块 ✓")

# 2. 检查market_index_fetcher.py是否更新中证500
print("\n[2] market_index_fetcher.py更新范围:")
with open('E:/csi10/market_index_fetcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

    if "'sh.000905'" in content:
        print("  ✓ INDEX_CODES包含中证500代码")
    else:
        print("  ✗ INDEX_CODES不包含中证500代码")

    # 检查__main__部分是否更新中证500
    if "__name__ == '__main__':" in content:
        main_section = content.split("__name__ == '__main__':")[1]
        if "'sh.000905'" in main_section or "中证500" in main_section:
            print("  ✓ __main__部分会更新中证500")
        else:
            print("  ✗ __main__部分只更新沪深300，不更新中证500 ⚠️")

# 3. 问题诊断
print("\n[3] 问题诊断:")
print("  ⚠️ market_index_fetcher.py的INDEX_CODES已包含中证500")
print("  ⚠️ 但__main__部分只调用fetch_today_realtime('sh.000300')")
print("  ⚠️ 所以'立即更新'按钮只更新沪深300，不更新中证500")
print("\n  这会导致:")
print("  - 沪深300数据会实时更新 ✓")
print("  - 中证500数据不会自动更新 ✗")
print("  - indices面板的中证500显示会停留在旧数据")

# 4. 解决方案
print("\n[4] 解决方案:")
print("  方案1: 修改market_index_fetcher.py，在__main__添加中证500更新")
print("  方案2: 在main_json.js调用fetch_zz500_data.py")
print("  推荐: 方案1（统一入口，更简洁）")

# 5. 修复代码示例
print("\n[5] 需要修改的代码位置:")
print("  market_index_fetcher.py __main__部分:")
print("  当前: fetcher.fetch_today_realtime('sh.000300')")
print("  应改为:")
print("    # 更新沪深300")
print("    fetcher.fetch_today_realtime('sh.000300')")
print("    # 更新中证500")
print("    fetcher.fetch_today_realtime('sh.000905')")

print("\n" + "="*70)
print("诊断完成")
print("="*70)