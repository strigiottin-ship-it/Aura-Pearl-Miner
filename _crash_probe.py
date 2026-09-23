import traceback, sys, os
from pathlib import Path
log = Path(r"C:\Users\neno\Downloads\Aura\dist\Aura\aura_crash.log")
try:
    # Run frozen exe and also try importing bundled
    import subprocess
    p = subprocess.run([r"C:\Users\neno\Downloads\Aura\dist\Aura\Aura.exe"], cwd=r"C:\Users\neno\Downloads\Aura\dist\Aura", capture_output=True, text=True, timeout=8)
    log.write_text(f"exit={p.returncode}\nstdout={p.stdout}\nstderr={p.stderr}\n", encoding="utf-8")
except Exception:
    log.write_text(traceback.format_exc(), encoding="utf-8")
print(log.read_text(encoding="utf-8")[:2000])
