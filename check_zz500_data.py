# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'E:\csi10\stocks.db')
cursor = conn.cursor()

# Check table structure
print('=== Table Structure ===')
cursor.execute('PRAGMA table_info(index_daily)')
cols = cursor.fetchall()
for c in cols:
    print(f'{c[1]}: {c[2]}')

print()
print('=== ZZ500 Recent Data ===')
cursor.execute("SELECT date, close, pct_chg FROM index_daily WHERE code='sh.000905' ORDER BY date DESC LIMIT 10")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f'{r[0]}: close={r[1]}, pct_chg={r[2]}')
else:
    print('NO ZZ500 DATA FOUND!')

print()
print('=== HS300 Recent Data ===')
cursor.execute("SELECT date, close, pct_chg FROM index_daily WHERE code='sh.000300' ORDER BY date DESC LIMIT 5")
rows = cursor.fetchall()
for r in rows:
    print(f'{r[0]}: close={r[1]}, pct_chg={r[2]}')

print()
print('=== ZZ500 Total Count ===')
cursor.execute("SELECT COUNT(*) FROM index_daily WHERE code='sh.000905'")
count = cursor.fetchone()[0]
print(f'Total records: {count}')

print()
print('=== ZZ500 Last 5 Records ===')
cursor.execute("SELECT date, close FROM index_daily WHERE code='sh.000905' ORDER BY date DESC LIMIT 5")
rows = cursor.fetchall()
for r in rows:
    print(f'{r[0]}: close={r[1]}')

print()
print('=== Check pct_5d calculation ===')
if len(rows) >= 5:
    latest_close = rows[0][1]
    fifth_close = rows[4][1]
    pct_5d = (latest_close - fifth_close) / fifth_close * 100
    print(f'latest_close={latest_close}')
    print(f'fifth_close={fifth_close}')
    print(f'pct_5d={pct_5d:.2f}%')
else:
    print(f'Not enough data! Only {len(rows)} records')

print()
print('=== All Codes in index_daily ===')
cursor.execute("SELECT DISTINCT code FROM index_daily")
codes = cursor.fetchall()
for c in codes:
    print(f'Code: {c[0]}')

conn.close()