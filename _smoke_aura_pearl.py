from pathlib import Path
import json, sys, time, importlib

ROOT = Path(r"C:\Users\neno\Downloads\Aura")
cfg_path = ROOT / "config.json"
cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
cfg["coin"] = "PRL"
cfg["mode"] = "pool"
cfg["host"] = "pearlpow.unmineable.com"
cfg["port"] = "3333"
cfg["auto_ai"] = True
cfg["worker_name"] = "Aura"
w = dict(cfg.get("wallets") or {})
w["PRL"] = "YOUR_PRL_WALLET"
cfg["wallets"] = w
cfg["address"] = w["PRL"]
cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print("saved wallet", w["PRL"])

sys.path[:0] = [str(ROOT / "_app"), str(ROOT / "_app" / "webui")]
import web_main
importlib.reload(web_main)
api = web_main.Api()
print("loaded wallets", api.cfg.get("wallets", {}).get("PRL"))
r = api.toggle_mining("PRL")
print("start", r)
time.sleep(12)
s = api.get_state()
print(
    "running", s.get("running"),
    "rate", s.get("hashrate_s"),
    "acc", s.get("accepted"),
    "engine", s.get("engine"),
    "status", s.get("status"),
)
for x in (s.get("log") or [])[-20:]:
    print("L", x)
print("pearl_alive", api.pearl.is_running())
logf = ROOT / "bin" / "aura-pearl.log"
if logf.exists():
    print("---PEARL LOG---")
    print("\n".join(logf.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]))
