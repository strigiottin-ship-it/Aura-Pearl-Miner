from pathlib import Path
import json

p = Path(r"C:\Users\neno\Downloads\Aura\_app\webui\web_main.py")
t = p.read_text(encoding="utf-8")
start = t.find("def save_config(cfg: dict) -> None:")
end = t.find("\ndef _gpu_telemetry", start)
if start < 0 or end < 0:
    raise SystemExit(f"block missing {start} {end}")
print("broken snippet:")
print(t[start:end])
new_save = (
    "def save_config(cfg: dict) -> None:\n"
    "    try:\n"
    "        old = json.loads(CONFIG_PATH.read_text(encoding=\"utf-8-sig\"))\n"
    "    except Exception:\n"
    "        old = {}\n"
    "    if not isinstance(cfg, dict):\n"
    "        cfg = {}\n"
    "    if isinstance(old, dict) and old:\n"
    "        for k in (\"wallets\", \"address\", \"payout\", \"worker_name\", \"pearl_ai\", \"auto_ai\", \"pearl_ai_boost\", \"ai_intensity\", \"withdraw_addresses\", \"coin\", \"mode\", \"host\", \"port\", \"pool_password\"):\n"
    "            if k not in cfg and k in old:\n"
    "                cfg[k] = old[k]\n"
    "        if isinstance(old.get(\"wallets\"), dict):\n"
    "            merged = dict(old[\"wallets\"])\n"
    "            if isinstance(cfg.get(\"wallets\"), dict):\n"
    "                for kk, vv in cfg[\"wallets\"].items():\n"
    "                    if str(vv or \"\").strip():\n"
    "                        merged[kk] = vv\n"
    "            cfg[\"wallets\"] = merged\n"
    "        if old.get(\"wallets\") and not (isinstance(cfg.get(\"wallets\"), dict) and any(str(v or \"\").strip() for v in cfg[\"wallets\"].values())):\n"
    "            cfg[\"wallets\"] = old[\"wallets\"]\n"
    "    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + chr(10), encoding=\"utf-8\")\n"
)
t2 = t[:start] + new_save + t[end:]
p.write_text(t2, encoding="utf-8")
compile(t2, str(p), "exec")
print("OK compiled")
