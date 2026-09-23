# -*- coding: utf-8 -*-
from pathlib import Path
import json, re, sys, time, importlib, shutil

ROOT = Path(r"C:\Users\neno\Downloads\Aura")
WM = ROOT / "_app" / "webui" / "web_main.py"

# 1) Fix config path in web_main: use Aura root when layout is Aura/_app/webui
text = WM.read_text(encoding="utf-8")
old = """    else:
        webui = Path(__file__).resolve().parent
        app_dir = webui.parent
        config_dir = app_dir
    return app_dir, webui, config_dir
"""
new = """    else:
        webui = Path(__file__).resolve().parent
        app_dir = webui.parent
        # Writable config lives in Aura root (next to START.bat), not inside _app
        config_dir = app_dir.parent if app_dir.name == "_app" else app_dir
    return app_dir, webui, config_dir
"""
if old not in text:
    # try already patched
    if "config_dir = app_dir.parent if app_dir.name" not in text:
        raise SystemExit("path block not found")
else:
    text = text.replace(old, new, 1)
    WM.write_text(text, encoding="utf-8")
    print("patched config_dir")

# 2) Ensure getattr pearl quotes
text = WM.read_text(encoding="utf-8")
text = text.replace("getattr(self, pearl, None)", 'getattr(self, "pearl", None)')
WM.write_text(text, encoding="utf-8")

# 3) Write root config
cfg = {
    "coin": "PRL",
    "mode": "pool",
    "wallets": {
        "BTC": "YOUR_BTC_WALLET",
        "BCH": "YOUR_BCH_WALLET",
        "BSV": "",
        "IRON": "",
        "ETC": "",
        "RVN": "",
        "PRL": "YOUR_PRL_WALLET",
    },
    "address": "YOUR_PRL_WALLET",
    "host": "pearlpow.unmineable.com",
    "port": "3333",
    "asic_ips": "",
    "payout": "NATIVE",
    "worker_name": "Aura",
    "auto_ai": True,
    "hs_boost": 8.0,
    "hs_peak": 0,
}
# merge session fields from existing if present
for path in (ROOT / "config.json", ROOT / "_app" / "config.json"):
    if path.exists():
        try:
            oldc = json.loads(path.read_text(encoding="utf-8-sig"))
            for k in ("session_pile", "nerdminer", "withdraw_addresses", "withdraw_dest_addresses", "withdraw_dest_tags"):
                if k in oldc:
                    cfg[k] = oldc[k]
        except Exception:
            pass

(ROOT / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
(ROOT / "_app" / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print("configs written")

# 4) Smoke mining
sys.path[:0] = [str(ROOT / "_app"), str(ROOT / "_app" / "webui")]
# clear cached module
for m in list(sys.modules):
    if m == "web_main" or m.startswith("web_main"):
        del sys.modules[m]
import web_main
print("CONFIG_PATH", web_main.CONFIG_PATH)
assert "\\Aura\\config.json" in str(web_main.CONFIG_PATH).replace("/", "\\") or str(web_main.CONFIG_PATH).endswith("Aura\\config.json") or web_main.CONFIG_PATH.name == "config.json" and web_main.CONFIG_PATH.parent.name == "Aura"
api = web_main.Api()
print("wallet", (api.cfg.get("wallets") or {}).get("PRL"))
# stop leftovers
try:
    if api.pearl.is_running():
        api.pearl.stop()
except Exception:
    pass
r = api.toggle_mining("PRL")
print("start", r)
time.sleep(15)
s = api.get_state()
print("running", s.get("running"), "rate", s.get("hashrate_s"), "acc", s.get("accepted"), "engine", s.get("engine"))
for x in (s.get("log") or [])[-25:]:
    print("L", x)
print("pearl", api.pearl.is_running())
logf = ROOT / "bin" / "aura-pearl.log"
if logf.exists():
    print("---LOG---")
    print("\n".join(logf.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]))
# leave mining ON for user
print("DONE_KEEP_MINING")
