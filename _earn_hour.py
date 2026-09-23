import json, time, urllib.request
from pathlib import Path
import sys
sys.path.insert(0, r"C:\Users\neno\Downloads\Aura\_app")
from srb_live import summarize_srb
from webui.web_main import Api

c = json.loads(Path(r"C:\Users\neno\Downloads\Aura\config.json").read_text(encoding="utf-8-sig"))
btc = (c.get("wallets") or {}).get("BTC")
print("wallet", btc)
print("coin", c.get("coin"), c.get("host"), "pearl_ai", c.get("pearl_ai"), "boost", c.get("pearl_ai_boost"))
s = summarize_srb()
print("SRB", s)
st = Api().get_withdraw_state()
print("POVUCI", st.get("balance_text"), "bal", st.get("balance"), "thr", st.get("threshold"))

# unMineable stats API if possible
def get(url):
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

# common unmineable endpoints
for url in [
    f"https://api.unmineable.com/v4/address/{btc}?coin=BTC",
    f"https://api.unmineable.com/v4/stats/{btc}",
    f"https://api.unmineable.com/v3/stats/{btc}?coin=BTC",
]:
    data = get(url)
    print("API", url.split(".com")[-1][:40], ":", json.dumps(data)[:400])
