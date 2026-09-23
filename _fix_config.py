from pathlib import Path
import json

wm = Path(r"C:\Users\neno\Downloads\Aura\_app\webui\web_main.py")
t = wm.read_text(encoding="utf-8")
old = 'return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))'
new = 'return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))'
if old not in t:
    # already patched or different quotes
    if "utf-8-sig" not in t[t.find("def load_config"):t.find("def load_config")+200]:
        raise SystemExit("load_config pattern not found")
    print("load_config already utf-8-sig or missing")
else:
    wm.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("patched load_config")

# harden save_config: never drop wallets if present on disk
old_save = '''def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")'''
new_save = '''def save_config(cfg: dict) -> None:
    try:
        old = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        if isinstance(old, dict):
            # preserve wallets / payout / AI flags if caller omitted them
            for k in ("wallets", "address", "payout", "worker_name", "pearl_ai", "auto_ai", "pearl_ai_boost", "ai_intensity", "withdraw_addresses"):
                if k not in cfg and k in old:
                    cfg[k] = old[k]
            if isinstance(old.get("wallets"), dict):
                merged = dict(old["wallets"])
                if isinstance(cfg.get("wallets"), dict):
                    merged.update(cfg["wallets"])
                cfg["wallets"] = merged
    except Exception:
        pass
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")'''
if old_save in t or old_save in wm.read_text(encoding="utf-8"):
    tt = wm.read_text(encoding="utf-8")
    if "preserve wallets" not in tt:
        if old_save not in tt:
            raise SystemExit("save_config pattern missing")
        wm.write_text(tt.replace(old_save, new_save, 1), encoding="utf-8")
        print("patched save_config merge")
    else:
        print("save_config already merge-safe")
else:
    print("save_config pattern mismatch - skip merge patch")

cfg = {
  "coin": "PRL",
  "mode": "pool",
  "wallets": {
    "BTC": "YOUR_BTC_WALLET",
    "BCH": "YOUR_BCH_WALLET",
    "PRL": "YOUR_PRL_WALLET"
  },
  "address": "YOUR_PRL_WALLET",
  "host": "pearlpow.unmineable.com",
  "port": "4444",
  "worker_name": "Aura",
  "payout": "BTC",
  "pool_password": "x",
  "pearl_ai": True,
  "auto_ai": True,
  "pearl_ai_boost": 5,
  "ai_intensity": 5
}
Path(r"C:\Users\neno\Downloads\Aura\config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("wrote config, first bytes", Path(r"C:\Users\neno\Downloads\Aura\config.json").read_bytes()[:8])

import sys
sys.path.insert(0, r"C:\Users\neno\Downloads\Aura\_app")
from webui.web_main import load_config, Api
c = load_config()
print("loaded keys", list(c.keys()))
print("wallets", c.get("wallets"))
st = Api().get_withdraw_state()
print("POVUCI", st.get("balance_text"))
print("mining_address", st.get("mining_address"))
