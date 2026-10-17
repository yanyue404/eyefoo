# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 规格。在项目根目录执行 packaging/build_windows.ps1。"""

from pathlib import Path

root = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(root / "run.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=["pystray", "PIL", "PIL.Image", "PIL.ImageDraw", "six"],
    hookspath=[],
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
    [],
    exclude_binaries=True,
    name="EyeGuard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="EyeGuard",
)
