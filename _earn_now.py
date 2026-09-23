import json, urllib.request
from pathlib import Path
import sys
sys.path.insert(0, r"C:\Users\neno\Downloads\Aura\_app")
from srb_live import summarize_srb
from webui.web_main import Api

c = json.loads(Path(r"C:\Users\neno\Downloads\Aura\config.json").read_text(encoding="utf-8-sig"))
s = summarize_srb()
st = Api().get_withdraw_state()
print("hashrate", s.get("hashrate"))
print("hashrate_hs", s.get("hashrate_hs"))
print("accepted", s.get("accepted"), "rejected", s.get("rejected"))
print("uptime", s.get("uptime"))
print("temp", s.get("temp"), "power", s.get("power"))
print("ai", c.get("pearl_ai"), "boost", c.get("pearl_ai_boost"))
print("balance", st.get("balance"), st.get("balance_text"))
print("pool", s.get("pool"))

# BTC EUR via coingecko simple
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AuraEarn/1"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode())
try:
    px = get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur")
    btc_eur = float(px["bitcoin"]["eur"])
    print("btc_eur", btc_eur)
except Exception as e:
    print("btc_eur_err", e)
    btc_eur = None

th = float(s.get("hashrate_hs") or 0) / 1e12
# WhatToMine baseline ~0.000001 BTC/h at 60 TH/s (recent)
btc_per_h = 0.000001 * (th / 60.0) if th else 0
# unmineable 1% fee
btc_per_h *= 0.99
print("th", round(th, 2))
print("btc_h", f"{btc_per_h:.8f}")
print("btc_d", f"{btc_per_h*24:.8f}")
if btc_eur:
    print("eur_h", round(btc_per_h * btc_eur, 3))
    print("eur_d", round(btc_per_h * 24 * btc_eur, 2))
    print("bal_eur", round(float(st.get("balance") or 0) * btc_eur, 4))
