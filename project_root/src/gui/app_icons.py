from pathlib import Path
import re
import sys
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer

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

def app_icon(name: str, color: str | None = None) -> QIcon:
    path = _resolve_icons_dir() / f'{name}.svg'
    if not path.exists():
        return QIcon()
    if not color:
        return QIcon(str(path))

    try:
        svg_text = path.read_text(encoding='utf-8')
        tinted_svg = re.sub(r'stroke="[^"]*"', f'stroke="{color}"', svg_text)
        tinted_svg = re.sub(r'fill="(?!(?:none|transparent))[^"]*"', f'fill="{color}"', tinted_svg)
        renderer = QSvgRenderer(tinted_svg.encode('utf-8'))
        icon = QIcon()
        for size in (16, 20, 24, 32, 48):
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(0, 0, 0, 0))
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            icon.addPixmap(pixmap)
        return icon
    except Exception:
        return QIcon(str(path))
