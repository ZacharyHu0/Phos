# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[
(r"C:/Users/Hao/AppData/Roaming/Python/Python310/site-packages/streamlit/","./streamlit/"),
(r"C:\Users\Hao\.conda\envs\phos\Lib\urllib/","./urllib/"),

#(r"C:/Users/Hao/AppData/Roaming/Python/Python310/site-packages/streamlit/static","./streamlit/static"),
#(r"C:/Users/Hao/AppData/Roaming/Python/Python310/site-packages/streamlit/web","./streamlit/web"),
('./emoji-film_frames.ico', '.'),('./phos', 'phos')],
    hiddenimports=['click','secrets','blinker','http'],
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='phos_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='emoji-film_frames.ico',
)
