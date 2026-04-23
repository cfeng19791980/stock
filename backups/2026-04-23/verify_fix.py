import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('E:/csi10/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查新增字段读取代码
checks = [
    ('sellThreshold', "getElementById('sellThreshold')"),
    ('stopProfit', "getElementById('stopProfit')"),
    ('stopLoss', "getElementById('stopLoss')"),
    ('suggestPosition', "getElementById('suggestPosition')"),
    ('hs300Pct', "getElementById('hs300Pct')"),
    ('zz500Pct', "getElementById('zz500Pct')"),
    ('divergence', "getElementById('divergence')"),
]

print('displayMarket function check:')
for name, code in checks:
    if code in content:
        print(f'Found: {name}')
    else:
        print(f'Missing: {name}')

print('\nFix completed successfully!') if all(code in content for _, code in checks) else print('\nFix incomplete!')