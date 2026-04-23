# -*- coding: utf-8 -*-
"""
执行修复：按照最佳实践
1. 备份原文件到py文件夹
2. 在原文件内修改
"""
import sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8')

base = r'e:\csi10'
py_dir = os.path.join(base, 'py')
analyzer_path = os.path.join(base, 'analyzer_v5_market.py')

# 步骤1: 备份原文件
backup_name = 'analyzer_v5_market_backup_20260420.py'
backup_path = os.path.join(py_dir, backup_name)

if not os.path.exists(backup_path):
    shutil.copy(analyzer_path, backup_path)
    print(f"✓ 备份: {backup_path}")
else:
    print(f"✓ 备份已存在: {backup_path}")

# 步骤2: 在原文件内修改
with open(analyzer_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找原函数
old_func = '''def generate_trade_advice(score, market_status, adjusted_score, threshold):
    """生成买卖建议（含大盘调整信息）"""
    if score >= 80:
        base = f"强烈推荐买入！原评分{score}分"
    elif score >= 70:
        base = f"推荐买入。原评分{score}分"
    elif score >= 60:
        base = f"可考虑买入。原评分{score}分"
    elif score >= 40:
        base = f"暂不买入。评分{score}分，未达买入阈值"
    elif score >= 15:
        base = f"观望。评分{score}分，中性区间"
    else:
        base = f"建议卖出！评分仅{score}分"
    
    # 大盘调整说明
    adjustment_info = f"\\n大盘调整: {score}→{adjusted_score} ({market_status}, 阈值{threshold})"
    
    if adjusted_score >= threshold:
        return base + adjustment_info + " → ✅建议买入"
    else:
        return base + adjustment_info + " → ❌暂不买入"'''

new_func = '''def generate_trade_advice(score, market_status, adjusted_score, threshold):
    """生成买卖建议（含大盘调整信息）"""
    
    # 大盘调整说明
    adjustment_info = f"\\n大盘调整: {score}→{adjusted_score} ({market_status}, 阈值{threshold}分)"
    
    # 根据调整后评分给出建议（逻辑清晰）
    if adjusted_score < 15:
        # 低评分：建议卖出
        return f"建议卖出！评分仅{adjusted_score}分，风险较高" + adjustment_info + " → ❌卖出"
    elif adjusted_score < threshold:
        # 中等评分：暂不买入
        if adjusted_score >= 40:
            return f"暂不买入。评分{adjusted_score}分，接近阈值{threshold}" + adjustment_info + " → ⚠️观望"
        else:
            return f"观望。评分{adjusted_score}分，中性区间" + adjustment_info + " → ⏸️观望"
    else:
        # 高评分：建议买入
        if adjusted_score >= 80:
            return f"强烈推荐买入！评分{adjusted_score}分" + adjustment_info + " → ✅买入"
        elif adjusted_score >= 70:
            return f"推荐买入。评分{adjusted_score}分" + adjustment_info + " → ✅买入"
        else:
            return f"可考虑买入。评分{adjusted_score}分，达标{threshold}" + adjustment_info + " → ✅买入"'''

if old_func in content:
    content = content.replace(old_func, new_func)
    print("✓ 函数已替换")
else:
    print("⚠️ 未找到原函数，尝试其他方式")
    # 查找并替换
    import re
    pattern = r'def generate_trade_advice\(score, market_status, adjusted_score, threshold\):.*?return base + adjustment_info + " → ❌暂不买入"'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        print(f"找到函数位置: {match.start()}-{match.end()}")
        content = content[:match.start()] + new_func + content[match.end():]
        print("✓ 函数已替换")

# 写回文件
with open(analyzer_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ analyzer_v5_market.py 已更新")

print("\n" + "=" * 60)
print("修复完成")
print("=" * 60)

print("""
修复内容:
  - 卖出建议逻辑清晰化
  - adjusted_score < 15 → ❌卖出
  - 15 ≤ adjusted_score < threshold → ⚠️观望
  - adjusted_score ≥ threshold → ✅买入

不再显示矛盾的"建议卖出 → 暂不买入"

下次使用:
  - 运行 analyzer_v5_market.py
  - 查看修复后的建议
""")