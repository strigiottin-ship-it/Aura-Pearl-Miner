# -*- mode: python ; coding: utf-8 -*-
block_cipher = None
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    (r'C:\Users\neno\Downloads\Aura\_app\webui\index.html', 'webui'),
    (r'C:\Users\neno\Downloads\Aura\_app\webui\styles.css', 'webui'),
    (r'C:\Users\neno\Downloads\Aura\_app\webui\app.js', 'webui'),
    (r'C:\Users\neno\Downloads\Aura\assets\Aura.ico', 'assets'),
]
binaries = []
hiddenimports = [
    'webview','webview.platforms.winforms','clr','pythonnet',
    'coins','engine','license','market','multiprocessing','ctypes',
]
try:
    d,b,h = collect_all('webview')
    datas += d; binaries += b; hiddenimports += h
except Exception:
    pass
try:
    hiddenimports += collect_submodules('webview')
except Exception:
    pass

a = Analysis(
    [r'C:\Users\neno\Downloads\Aura\_app\webui\web_main.py'],
    pathex=[r'C:\Users\neno\Downloads\Aura\_app'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='Aura',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'C:\Users\neno\Downloads\Aura\assets\Aura.ico',
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[], name='Aura',
)
