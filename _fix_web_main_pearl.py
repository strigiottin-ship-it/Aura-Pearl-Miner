from pathlib import Path
p = Path(r"C:\Users\neno\Downloads\Aura\_app\webui\web_main.py")
raw = p.read_text(encoding="utf-8")
bad = "getattr(self, pearl, None)"
good = 'getattr(self, "pearl", None)'
n = raw.count(bad)
raw2 = raw.replace(bad, good)
p.write_text(raw2, encoding="utf-8")
print("replaced", n)
raw3 = p.read_text(encoding="utf-8")
assert bad not in raw3, "still broken"
assert good in raw3
for i, line in enumerate(raw3.splitlines(), 1):
    if "getattr(self" in line and "pearl" in line:
        print(i, line.strip())
print("OK")
