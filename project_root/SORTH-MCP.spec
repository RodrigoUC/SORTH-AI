# -*- mode: python ; coding: utf-8 -*-
# Isolated console onedir companion: never inject MCP into the GUI environment.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH)
metadata = copy_metadata('mcp', recursive=True)
a = Analysis(
    [str(root / 'mcp_app.py')],
    pathex=[str(root)],
    binaries=[],
    datas=metadata + collect_data_files('jsonschema_specifications') + [
        (str(root / 'build/identity/build-identity.json'), '.'),
        (str(root.parent / 'LICENSE'), '.'),
        (str(root.parent / 'LICENSING.md'), '.'),
        (str(root.parent / 'third_party/mcp'), 'third_party/mcp'),
        (str(root.parent / 'third_party/licenses/cpython-3.12.10.txt'), 'third_party/licenses'),
    ],
    hiddenimports=['src.mcp_adapter.server', 'src.mcp_adapter.execution',
                   'src.mcp_adapter.worker', 'mcp', 'mcp.server.lowlevel'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PyQt6', 'PySide6', 'pandas', 'numpy', 'openai',
              'anthropic', 'torch', 'pytest', 'pip'],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SORTH-MCP',
          version=str(root / 'build/identity/windows_version_info.txt'),
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=True, contents_directory='_internal')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='SORTH-MCP')
