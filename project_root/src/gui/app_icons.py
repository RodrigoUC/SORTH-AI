from pathlib import Path
import sys
from PyQt6.QtGui import QIcon

_ICONS_DIR = None

def _resolve_icons_dir():
    global _ICONS_DIR
    if _ICONS_DIR is None:
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS) / 'assets' / 'icons'
        else:
            base = Path(__file__).resolve().parents[2] / 'assets' / 'icons'
        _ICONS_DIR = base
    return _ICONS_DIR

def app_icon(name: str) -> QIcon:
    path = _resolve_icons_dir() / f'{name}.svg'
    if path.exists():
        return QIcon(str(path))
    return QIcon()