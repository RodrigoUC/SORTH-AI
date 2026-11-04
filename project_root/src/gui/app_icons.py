from pathlib import Path
import re
import struct
import sys
from PyQt6.QtCore import qRegisterResourceData
from PyQt6.QtGui import QIcon

_ICONS_DIR = None
_ICON_CACHE = {}
_RESOURCE_BUFFERS = []

def _resolve_icons_dir():
    global _ICONS_DIR
    if _ICONS_DIR is None:
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS) / 'assets' / 'icons'
        else:
            base = Path(__file__).resolve().parents[2] / 'assets' / 'icons'
        _ICONS_DIR = base
    return _ICONS_DIR

def _get_tinted_icon_path(name: str, color: str, path: Path) -> str:
    key = (name, color.lower())
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    svg_text = path.read_text(encoding='utf-8')
    tinted_svg = re.sub(r'stroke="[^"]*"', f'stroke="{color}"', svg_text)
    tinted_svg = re.sub(r'fill="(?!(?:none|transparent))[^"]*"', f'fill="{color}"', tinted_svg)
    svg_bytes = tinted_svg.encode('utf-8')

    clean_hex = color.lstrip('#').lower()
    filename = f'sorth_icon_{name}_{clean_hex}.svg'
    name_hash = 0
    for char in filename:
        name_hash = (name_hash << 4) + ord(char)
        name_hash ^= (name_hash & 0xf0000000) >> 23
        name_hash &= 0x0fffffff

    names = struct.pack('>HI', len(filename), name_hash) + filename.encode('utf-16-be')
    data = struct.pack('>I', len(svg_bytes)) + svg_bytes
    tree = struct.pack('>IHII', 0, 2, 1, 1) + struct.pack('>IHHHI', 0, 0, 0, 1, 0)

    if qRegisterResourceData(1, tree, names, data):
        _RESOURCE_BUFFERS.append((tree, names, data))
        resource_path = ':/' + filename
        _ICON_CACHE[key] = resource_path
        return resource_path
    return str(path)

def app_icon(name: str, color: str | None = None) -> QIcon:
    path = _resolve_icons_dir() / f'{name}.svg'
    if not path.exists():
        return QIcon()
    if not color:
        return QIcon(str(path))

    try:
        icon_path = _get_tinted_icon_path(name, color, path)
        return QIcon(icon_path)
    except Exception:
        return QIcon(str(path))
