from pathlib import Path
import re, json, sys
sys.path.insert(0, r"C:\Users\neno\Downloads\Aura\_app")
from srb_live import summarize_srb
c=json.loads(Path(r"C:\Users\neno\Downloads\Aura\config.json").read_text(encoding="utf-8-sig"))
print("cfg boost", c.get("pearl_ai_boost"), "ai_intensity", c.get("ai_intensity"), "pearl_ai", c.get("pearl_ai"))
s=summarize_srb()
print("live", s.get("hashrate"), "temp", s.get("temp"), "power", s.get("power"), "core", s.get("core_clock"), "mem", s.get("mem_clock"))
# pearl_ai limits
p=Path(r"C:\Users\neno\Downloads\Aura\_app\pearl_ai.py")
if not p.exists():
 p=Path(r"C:\Users\neno\Downloads\Aura\pearl_ai.py")
t=p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
print("pearl_ai path", p, "exists", p.exists())
for pat in ["boost", "max", "intensity", "power", "nudge", "race"]:
    pass
# print relevant constants/functions
for m in re.finditer(r"(.{0,40}(boost|intensity|MAX_|max_boost|power_limit|nvidia).{0,80})", t, re.I):
    line=m.group(1).replace("\n"," ")
    if any(k in line.lower() for k in ["boost", "intensity", "power", "max"]):
        print(line[:160])
