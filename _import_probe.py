import traceback, sys
from pathlib import Path
ROOT = Path(r"C:\Users\neno\Downloads\Aura")
sys.path.insert(0, str(ROOT/"_app"))
sys.path.insert(0, str(ROOT/"_app"/"webui"))
try:
    import webview
    print("webview", getattr(webview, "__file__", "?"))
    from web_main import main
    print("calling main briefly - will fail if GUI blocked")
except Exception:
    Path(r"C:\Users\neno\Downloads\Aura\import_err.txt").write_text(traceback.format_exc(), encoding="utf-8")
    print(traceback.format_exc())
