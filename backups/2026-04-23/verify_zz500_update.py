import sqlite3
conn = sqlite3.connect('E:/csi10/stocks.db')

rows = conn.execute('SELECT date, close, pct_chg FROM index_daily WHERE code="sh.000905" ORDER BY date DESC LIMIT 3').fetchall()

if rows:
    for r in rows:
        print(f'{r[0]}: close={r[1]:.2f}, pct_chg={r[2]:.2f}%')
else:
    print('No ZZ500 data found')

conn.close()