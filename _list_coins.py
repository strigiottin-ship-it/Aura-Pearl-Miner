from pathlib import Path
import importlib.util
p = Path(r"C:\Users\neno\Downloads\Aura\_app\coins.py")
if not p.exists():
    # find it
    hits = list(Path(r"C:\Users\neno\Downloads\Aura").rglob("coins.py"))
    print("hits", hits)
    p = hits[0]
print("using", p)
spec = importlib.util.spec_from_file_location("coins", p)
coins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coins)
ORDER = getattr(coins, "ORDER", None)
print("ORDER", ORDER)
# find coin dict
for name in dir(coins):
    obj = getattr(coins, name)
    if isinstance(obj, dict) and obj:
        v = next(iter(obj.values()))
        if isinstance(v, dict) and ("algo" in v or "pool" in v):
            print("DICT", name, len(obj))
            keys = list(ORDER) if ORDER else list(obj.keys())
            for code in keys:
                c = obj.get(code) or {}
                print(f"{code}\talgo={c.get('algo')}\tpool={c.get('pool')}\tsolo={c.get('solo')}\tminer={c.get('pool_miner') or c.get('miner')}\tlabel={c.get('label') or c.get('name')}")
            break
