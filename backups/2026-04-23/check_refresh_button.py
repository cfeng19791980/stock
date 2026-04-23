import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('E:/csi10/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 查找立即更新按钮和相关函数
print("Searching for refresh/update buttons and functions...")

for i, line in enumerate(lines):
    # 查找按钮
    if 'refresh' in line.lower() or 'update' in line.lower() or 'reload' in line.lower():
        if '<button' in line or 'onclick' in line or 'function' in line:
            print(f'Line {i+1}: {line.rstrip()}')

# 查找fetchData函数
print("\nSearching for fetchData function...")
for i, line in enumerate(lines):
    if 'function fetchData' in line or 'fetchData(' in line:
        print(f'Line {i+1}: {line.rstrip()}')
        # 显示接下来的30行
        for j in range(i+1, min(i+30, len(lines))):
            print(f'Line {j+1}: {lines[j].rstrip()}')
        break