from pathlib import Path
import json
import re

root = Path(r"C:\Users\neno\Downloads\Aura")
wm = root / "_app" / "webui" / "web_main.py"
js = root / "_app" / "webui" / "app.js"

# --- harden save_config: never write without wallets if disk had them ---
t = wm.read_text(encoding="utf-8-sig")
# strip BOM permanently
if t.startswith("\ufeff"):
    t = t.lstrip("\ufeff")

old_save_start = t.find("def save_config(cfg: dict) -> None:")
old_save_end = t.find("\ndef _gpu_telemetry", old_save_start)
if old_save_start < 0 or old_save_end < 0:
    raise SystemExit("save_config block not found")
new_save = '''def save_config(cfg: dict) -> None:
    try:
        old = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        old = {}
    if not isinstance(cfg, dict):
        cfg = {}
    if isinstance(old, dict) and old:
        for k in ("wallets", "address", "payout", "worker_name", "pearl_ai", "auto_ai", "pearl_ai_boost", "ai_intensity", "withdraw_addresses", "coin", "mode", "host", "port", "pool_password"):
            if k not in cfg and k in old:
                cfg[k] = old[k]
        if isinstance(old.get("wallets"), dict):
            merged = dict(old["wallets"])
            if isinstance(cfg.get("wallets"), dict):
                for kk, vv in cfg["wallets"].items():
                    if str(vv or "").strip():
                        merged[kk] = vv
            cfg["wallets"] = merged
        # hard guard: never persist a config that dropped all wallets
        if old.get("wallets") and not (isinstance(cfg.get("wallets"), dict) and any(str(v or "").strip() for v in cfg["wallets"].values())):
            cfg["wallets"] = old["wallets"]
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
'''
t = t[:old_save_start] + new_save + t[old_save_end:]

# load_config utf-8-sig
t = t.replace(
    'return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))',
    'return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))',
)

# AUTO_START always PRL Pearl if wallets present
t = t.replace(
    'api.toggle_mining(str(cfg.get("coin") or "PRL"))',
    'api.toggle_mining("PRL" if (cfg.get("wallets") or {}).get("BTC") or (cfg.get("wallets") or {}).get("PRL") else str(cfg.get("coin") or "PRL"))',
)

wm.write_text(t, encoding="utf-8")
print("web_main patched, no BOM", wm.read_bytes()[:3])

# --- fix app.js applySettingsForm race ---
j = js.read_text(encoding="utf-8")
old_js = '''function applySettingsForm(s) {
  if (!s) return;
  setMode(s.mode || "pool");
  if (s.coin) {
    if ($("setCoin")) $("setCoin").value = s.coin;
    if ($("coinSelect")) $("coinSelect").value = s.coin;
  }'''
new_js = '''function applySettingsForm(s) {
  if (!s) return;
  if (s.coin) {
    if ($("setCoin")) $("setCoin").value = s.coin;
    if ($("coinSelect")) $("coinSelect").value = s.coin;
  }
  setMode(s.mode || "pool", false);
  if (s.coin) {
    api("apply_mode", (s.mode === "solo" ? "solo" : "pool"), s.coin).catch(() => {});
  }'''
if old_js not in j:
    # try flexible
    if "setMode(s.mode || \"pool\");" in j and "if (s.coin)" in j:
        j2 = j.replace(
            "  setMode(s.mode || \"pool\");\n  if (s.coin) {\n    if ($(\"setCoin\")) $(\"setCoin\").value = s.coin;\n    if ($(\"coinSelect\")) $(\"coinSelect\").value = s.coin;\n  }",
            "  if (s.coin) {\n    if ($(\"setCoin\")) $(\"setCoin\").value = s.coin;\n    if ($(\"coinSelect\")) $(\"coinSelect\").value = s.coin;\n  }\n  setMode(s.mode || \"pool\", false);\n  if (s.coin) {\n    api(\"apply_mode\", (s.mode === \"solo\" ? \"solo\" : \"pool\"), s.coin).catch(() => {});\n  }",
            1,
        )
        if j2 == j:
            raise SystemExit("app.js pattern not replaced")
        j = j2
        print("app.js patched via flexible")
    else:
        raise SystemExit("app.js pattern missing")
else:
    j = j.replace(old_js, new_js, 1)
    print("app.js patched exact")
js.write_text(j, encoding="utf-8")

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
(root / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("config written")

# clear pycache
import shutil
for p in (root / "_app" / "webui" / "__pycache__", root / "_app" / "__pycache__"):
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
        print("cleared", p)
