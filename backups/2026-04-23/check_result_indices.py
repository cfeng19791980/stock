import json
data = json.load(open('E:/csi10/result.json', 'r', encoding='utf-8'))
indices = data.get('market', {}).get('indices', {})
print(f'HS300 5d: {indices.get("hs300", {}).get("pct_5d", 0)}%')
print(f'ZZ500 5d: {indices.get("zz500", {}).get("pct_5d", 0)}%')
print(f'ZZ500 latest: {indices.get("zz500", {}).get("latest", 0)}')
print(f'Composite: {indices.get("composite", {}).get("pct_5d", 0)}%')
print(f'Divergence: {indices.get("divergence", 0)}%')
print(f'Dominant: {indices.get("dominant", "unknown")}')