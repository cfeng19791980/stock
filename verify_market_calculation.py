# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r'E:\csi10\stocks.db')
cursor = conn.cursor()

# HS300 5 days
cursor.execute("SELECT date, close, pct_chg FROM index_daily WHERE code='sh.000300' ORDER BY date DESC LIMIT 5")
hs300 = cursor.fetchall()

# ZZ500 5 days
cursor.execute("SELECT date, close, pct_chg FROM index_daily WHERE code='sh.000905' ORDER BY date DESC LIMIT 5")
zz500 = cursor.fetchall()

print("=" * 60)
print("Market Status Calculation Analysis")
print("=" * 60)

print("\n--- HS300 Data (sorted by date DESC) ---")
for i, (date, close, pct) in enumerate(hs300):
    print(f"  [{i}] {date}: close={close:.2f}, daily_pct={pct:.2f}%")

# iloc[0] is latest (04-23), iloc[4] is 5th day (04-17)
hs300_latest = hs300[0][1]  # 04-23 close
hs300_fifth = hs300[4][1]   # 04-17 close
hs300_pct_5d = (hs300_latest - hs300_fifth) / hs300_fifth * 100

print(f"\nHS300 5-day pct calculation:")
print(f"  latest (iloc[0]) = {hs300_latest:.2f} ({hs300[0][0]})")
print(f"  fifth  (iloc[4]) = {hs300_fifth:.2f} ({hs300[4][0]})")
print(f"  pct_5d = ({hs300_latest:.2f} - {hs300_fifth:.2f}) / {hs300_fifth:.2f} * 100")
print(f"  pct_5d = {hs300_pct_5d:.2f}%")

print("\n--- ZZ500 Data (sorted by date DESC) ---")
for i, (date, close, pct) in enumerate(zz500):
    print(f"  [{i}] {date}: close={close:.2f}, daily_pct={pct:.2f}%")

zz500_latest = zz500[0][1]  # 04-23 close
zz500_fifth = zz500[4][1]   # 04-17 close
zz500_pct_5d = (zz500_latest - zz500_fifth) / zz500_fifth * 100

print(f"\nZZ500 5-day pct calculation:")
print(f"  latest (iloc[0]) = {zz500_latest:.2f} ({zz500[0][0]})")
print(f"  fifth  (iloc[4]) = {zz500_fifth:.2f} ({zz500[4][0]})")
print(f"  pct_5d = ({zz500_latest:.2f} - {zz500_fifth:.2f}) / {zz500_fifth:.2f} * 100")
print(f"  pct_5d = {zz500_pct_5d:.2f}%")

print("\n--- Market Status Calculation ---")
market_pct = hs300_pct_5d * 0.6 + zz500_pct_5d * 0.4
print(f"market_pct = {hs300_pct_5d:.2f} * 0.6 + {zz500_pct_5d:.2f} * 0.4")
print(f"market_pct = {market_pct:.2f}%")

print("\n--- Status Thresholds ---")
print("  >= 3%  -> Strong Market")
print("  >= 1%  -> Slightly Strong")
print("  >= -1% -> Oscillation")
print("  >= -3% -> Slightly Weak")
print("  < -3%  -> Weak Market")

print(f"\nCurrent: {market_pct:.2f}%")
if market_pct >= 3:
    status = "Strong Market"
elif market_pct >= 1:
    status = "Slightly Strong"
elif market_pct >= -1:
    status = "Oscillation"
elif market_pct >= -3:
    status = "Slightly Weak"
else:
    status = "Weak Market"

print(f"Result: {status}")

print("\n--- Important Note ---")
print("Daily pct_chg (今日涨跌) is DIFFERENT from 5-day pct!")
print(f"  HS300 today: {hs300[0][2]:.2f}% (daily)")
print(f"  HS300 5-day: {hs300_pct_5d:.2f}% (5-day cumulative)")
print(f"  ZZ500 today: {zz500[0][2]:.2f}% (daily)")
print(f"  ZZ500 5-day: {zz500_pct_5d:.2f}% (5-day cumulative)")

print("\n" + "=" * 60)
conn.close()