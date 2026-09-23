import json, urllib.request, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\neno\Downloads\Aura\_app")
from srb_live import summarize_srb

btc = "YOUR_BTC_WALLET"
req = urllib.request.Request(f"https://api.unmineable.com/v4/address/{btc}?coin=BTC", headers={"User-Agent": "Aura"})
data = json.loads(urllib.request.urlopen(req, timeout=12).read())["data"]
bal = float(data.get("balance") or data.get("balance_payable") or 0)
thr = float(data.get("payment_threshold") or 0.00075)
need = max(0.0, thr - bal)
pct = 100.0 * bal / thr if thr else 0

s = summarize_srb()
th = float(s.get("hashrate_hs") or 0) / 1e12
# ~0.000001 BTC/h at 60 TH/s, 1% fee
rate_h = 0.000001 * (th / 60.0) * 0.99 if th else 0.00000106

hours = need / rate_h if rate_h > 0 else float("inf")
days = hours / 24

# BTC EUR
try:
    px = json.loads(urllib.request.urlopen(urllib.request.Request(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur",
        headers={"User-Agent": "Aura"}), timeout=12).read())
    btc_eur = float(px["bitcoin"]["eur"])
except Exception:
    btc_eur = 75300.0

print(f"bal={bal:.8f}")
print(f"thr={thr:.8f}")
print(f"need={need:.8f}")
print(f"pct={pct:.2f}")
print(f"th={th:.2f}")
print(f"rate_h={rate_h:.8f}")
print(f"hours={hours:.1f}")
print(f"days={days:.1f}")
print(f"bal_eur={bal*btc_eur:.3f}")
print(f"thr_eur={thr*btc_eur:.2f}")
print(f"need_eur={need*btc_eur:.2f}")
print(f"accepted={s.get("accepted")} uptime={s.get("uptime")}")
