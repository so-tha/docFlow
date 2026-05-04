# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller — executável Windows (onefile). Rodar na raiz: pyinstaller --noconfirm Loglife.spec"""

import os

from PyInstaller.utils.hooks import collect_all

block_cipher = None

spec_dir = os.path.dirname(os.path.abspath(SPEC))

qt_datas, qt_binaries, qt_hidden = collect_all("PyQt6")

hiddenimports = list(qt_hidden) + [
    "sqlalchemy.dialects.sqlite",
]

a = Analysis(
    ["main.py"],
    pathex=[spec_dir],
    binaries=qt_binaries,
    datas=qt_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="Loglife",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
