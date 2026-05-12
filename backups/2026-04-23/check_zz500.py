import sqlite3
conn = sqlite3.connect('E:/csi10/stocks.db')
rows = conn.execute('SELECT code, date, close, pct_chg FROM index_daily WHERE code="sh.000905" ORDER BY date DESC LIMIT 5').fetchall()
for row in rows:
    print(f'{row[1]}: close={row[2]:.2f}, pct_chg={row[3]:.2f}%')
conn.close()