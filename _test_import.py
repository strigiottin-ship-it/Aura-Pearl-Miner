import traceback, sys
from pathlib import Path
DIST = Path(r"C:\Users\neno\Downloads\Aura\dist\Aura")
sys.path.insert(0, str(DIST / "_app"))
sys.path.insert(0, str(DIST / "_app" / "webui"))
try:
    import web_main
    print("import ok")
    print("WEBUI", web_main.WEBUI)
    print("APP_DIR", web_main.APP_DIR)
    print("index", (web_main.WEBUI / "index.html").exists())
except Exception:
    traceback.print_exc()
