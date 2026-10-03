# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

root = Path(SPECPATH)

a = Analysis(
    [str(root / 'gui_app.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'data/input'), 'data/input'), (str(root / 'assets'), 'assets'), (str(root / 'README.md'), '.'), (str(root / 'MCP_OPTIONAL.md'), '.'), (str(root.parent / 'CREDITS.md'), '.'), (str(root.parent / 'LICENSE'), '.'), (str(root.parent / 'LICENSING.md'), '.'), (str(root.parent / 'third_party'), 'third_party')],
    hiddenimports=['PyQt6'],
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
    name='SORTH',
    version=str(root / 'windows_version_info.txt'),
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
    icon=[str(root / 'assets/sorth.ico')],
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SORTH')
