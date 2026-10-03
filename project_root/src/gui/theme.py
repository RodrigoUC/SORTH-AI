"""Canonical native appearance, safe local previews and application-wide updates.

Only validated color values reach QSS. Asset paths are generated here and never
come from theme data. Domain state, exports, locale and motion are not touched.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from string import Template
import struct
from types import MappingProxyType

from PyQt6.QtCore import QObject, Qt, pyqtSignal, qRegisterResourceData
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6 import sip

from .theme_contract import ThemeSpec, ThemeValidationError, validate_theme


class ThemePreparationError(OSError):
    """No preference/live theme changed because native presentation could not stage."""


@dataclass(frozen=True)
class ThemeChoice:
    key: str
    spec: ThemeSpec


_ORIGINAL_COLORS = {'canvas': '#EFF3F9', 'surface': '#FFFFFF', 'surface_alt': '#F3F6FC', 'header': '#183153', 'header_hover': '#24476E', 'on_header': '#FFFFFF', 'on_header_muted': '#D3E5FA', 'text': '#1D2D44', 'muted': '#52647D', 'heading': '#183153', 'border': '#7688A1', 'divider': '#D6DFEB', 'primary': '#087F83', 'primary_hover': '#066B70', 'primary_pressed': '#055A61', 'on_primary': '#FFFFFF', 'primary_soft': '#E2F4F2', 'on_primary_soft': '#183153', 'accent': '#6545AD', 'on_accent': '#FFFFFF', 'accent_soft': '#EFE9FA', 'focus': '#6545AD', 'disabled': '#E1E7F0', 'disabled_text': '#56667D', 'success': '#246448', 'success_soft': '#E3F3EA', 'warning': '#88551A', 'warning_soft': '#FFF0D5', 'danger': '#A12D46', 'danger_soft': '#FCE8EC'}

_NOCTURNO_COLORS = {'canvas': '#131922', 'surface': '#1B2430', 'surface_alt': '#222E3D', 'header': '#101A29', 'header_hover': '#22374D', 'on_header': '#F4F7FC', 'on_header_muted': '#C4D6E8', 'text': '#F0F4FA', 'muted': '#BECADC', 'heading': '#DAE7FA', 'border': '#8294AE', 'divider': '#39485D', 'primary': '#63C7C3', 'primary_hover': '#7ADAD5', 'primary_pressed': '#9DE9E3', 'on_primary': '#10282D', 'primary_soft': '#203D40', 'on_primary_soft': '#C2F1E9', 'accent': '#B49AE6', 'on_accent': '#201B32', 'accent_soft': '#353049', 'focus': '#9579C8', 'disabled': '#303B4B', 'disabled_text': '#C1CBD9', 'success': '#8DD5AC', 'success_soft': '#233D32', 'warning': '#EDC17E', 'warning_soft': '#413524', 'danger': '#F2A3B3', 'danger_soft': '#472B34'}

_HIGH_CONTRAST_COLORS = {'canvas': '#FFFFFF', 'surface': '#FFFFFF', 'surface_alt': '#F2F4F8', 'header': '#10243C', 'header_hover': '#203A5A', 'on_header': '#FFFFFF', 'on_header_muted': '#FFFFFF', 'text': '#101D30', 'muted': '#34445B', 'heading': '#10243C', 'border': '#34445B', 'divider': '#64748B', 'primary': '#00666B', 'primary_hover': '#00585D', 'primary_pressed': '#004A50', 'on_primary': '#FFFFFF', 'primary_soft': '#E2F4F2', 'on_primary_soft': '#183153', 'accent': '#4D278E', 'on_accent': '#FFFFFF', 'accent_soft': '#EFE9FA', 'focus': '#4D278E', 'disabled': '#E5E9F0', 'disabled_text': '#37465A', 'success': '#164B31', 'success_soft': '#E3F3EA', 'warning': '#663B09', 'warning_soft': '#FFF0D5', 'danger': '#801C33', 'danger_soft': '#FCE8EC'}

def _builtin(key, name, mode, colors):
    return ThemeChoice(key, validate_theme({"schema_version": 1, "name": name,
                                           "mode": mode, "colors": colors}))


_BUILTINS = (
    _builtin("original", "Original claro", "light", _ORIGINAL_COLORS),
    _builtin("nocturno", "Nocturno", "dark", _NOCTURNO_COLORS),
    _builtin("high_contrast", "Alto contraste claro", "light", _HIGH_CONTRAST_COLORS),
)
_current = _BUILTINS[0].spec


def builtin_themes() -> tuple[ThemeChoice, ...]:
    return _BUILTINS


def current_theme() -> ThemeSpec:
    return _current


class _CurrentColors(Mapping):
    """Stable imported object, dynamically resolving current semantic colors."""
    def __getitem__(self, role):
        return _current.colors[role]

    def __iter__(self):
        return iter(_current.colors)

    def __len__(self):
        return len(_current.colors)


COLORS = _CurrentColors()

# Substitution keeps Qt selectors readable and color ownership centralized.
_QSS = """
QWidget { font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; font-size: 10pt; color: $text; }
QMainWindow, QDialog { background: $canvas; }
QWidget[sorthThemePreview="true"] { background: $canvas; }
QFrame#brandHeader { background: $header; border-radius: 9px; }
QLabel#appTitle { font-size: 24pt; font-weight: 700; color: $on_header; background: transparent; }
QLabel#subtitle { color: $on_header_muted; padding-left: 12px; background: transparent; }
QLabel#overview { padding: 10px 12px; color: $on_primary_soft; background: $primary_soft; border-radius: 6px; font-size: 11pt; }
QLabel#helpText { background: $accent_soft; color: $text; padding: 12px; border-radius: 6px; }
QLabel#mutedText { color: $muted; }
QFrame#settingsHeader { background: $header; border-radius: 7px; }
QLabel#settingsTitle { color: $on_header; background: transparent; font-size: 14pt; font-weight: 700; }
QLabel#settingsSubtitle { color: $on_header_muted; background: transparent; }
QWidget#settingsContent { background: $surface; border-radius: 7px; }
QWidget#settingsContent QCheckBox { border: 2px solid transparent; }
QWidget#settingsContent QCheckBox:focus { border-color: $focus; }
QLabel#settingsSectionTitle { color: $heading; font-size: 12pt; font-weight: 700; }
QLabel#settingsStepTitle { color: $heading; font-weight: 600; }
QFrame#settingsDivider { background: $divider; border: 0; }
QLabel#settingsNotice { color: $muted; background: $surface_alt; padding: 10px; border-radius: 5px; }
QLabel#settingsSaveState { color: $muted; }
QLabel#settingsSaveState[pending="true"] { color: $warning; }

QPushButton { background: $surface; border: 1px solid $border; border-radius: 5px; padding: 8px 14px; }
QPushButton:hover { background: $primary_soft; border-color: $primary; }
QPushButton:pressed, QPushButton:checked { background: $accent_soft; border-color: $accent; }
QPushButton:disabled { background: $disabled; color: $disabled_text; border-color: $divider; }
QPushButton#headerAction { background: $header; border-color: $on_header_muted; color: $on_header; }
QPushButton#headerAction:hover, QPushButton#headerAction:checked { background: $header_hover; }
QPushButton#headerAction:disabled { background: $disabled; color: $disabled_text; border-color: $divider; }
QPushButton#primaryAction { background: $primary; border-color: $primary; color: $on_primary; font-weight: 600; }
QPushButton#primaryAction:hover { background: $primary_hover; border-color: $primary_hover; }
QPushButton#primaryAction:pressed { background: $primary_pressed; border-color: $primary_pressed; }
QPushButton#primaryAction:disabled { background: $disabled; border-color: $divider; color: $disabled_text; }
QPushButton#dangerAction { color: $danger; border-color: $danger; }
QPushButton#dangerAction:hover { background: $danger_soft; }
QPushButton#dangerAction:disabled { color: $disabled_text; border-color: $divider; background: $disabled; }
QLineEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit, QDateTimeEdit, QComboBox { background: $surface; border: 1px solid $border; border-radius: 4px; padding: 6px; selection-background-color: $accent; selection-color: $on_accent; }
QLineEdit { placeholder-text-color: $muted; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QTimeEdit:disabled, QDateEdit:disabled, QDateTimeEdit:disabled, QComboBox:disabled, QPlainTextEdit:disabled, QTextEdit:disabled { background: $disabled; color: $disabled_text; }
QPushButton:focus, QPushButton#primaryAction:focus, QPushButton#dangerAction:focus, QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus, QComboBox:focus, QTableWidget:focus, QListWidget:focus, QPlainTextEdit:focus, QLabel:focus { border: 2px solid $focus; }
QPushButton#primaryAction:focus { border: 2px solid $on_primary; }
QPushButton#dangerAction:focus { border: 2px solid $danger; }
QPushButton#headerAction:focus { border: 2px solid $on_header; }
QCheckBox:focus, QTabBar::tab:focus { border: 2px solid $focus; }
QTabWidget::pane { border: 1px solid $divider; background: $surface; }
QTabBar::tab { padding: 11px 20px; background: $accent_soft; color: $muted; border: 0; margin-right: 3px; }
QTabBar::tab:selected { background: $surface; color: $accent; font-weight: 600; border-bottom: 3px solid $accent; }
QTabBar::tab:hover:!selected { background: $primary_soft; color: $on_primary_soft; }
QTabBar::tab:focus { border-top: 2px solid $focus; }
QTableView, QListView, QTreeView, QPlainTextEdit, QTextEdit { background: $surface; alternate-background-color: $surface_alt; border: 1px solid $divider; gridline-color: $divider; selection-background-color: $accent_soft; selection-color: $text; }
QTableWidget::item:focus { border: 1px solid $focus; }
QHeaderView::section { background: $header; color: $on_header; padding: 9px 7px; border: 0; border-bottom: 1px solid $header; font-weight: 600; }
QHeaderView::up-arrow { image: url("$sort_up"); width: 8px; height: 5px; }
QHeaderView::down-arrow { image: url("$sort_down"); width: 8px; height: 5px; }
QTableCornerButton::section { background: $header; border: 0; }
QStatusBar { background: $header; color: $on_header_muted; padding: 5px; }
QStatusBar QLabel { color: $on_header_muted; }
QStatusBar QCheckBox { color: $on_header_muted; border: 1px solid transparent; padding: 1px 3px; }
QStatusBar QCheckBox:focus { border-color: $on_header; }
QProgressBar { background: $primary_soft; border: 0; border-radius: 3px; }
QProgressBar::chunk { background: $primary; }
QMenu, QComboBox QAbstractItemView { background: $surface; color: $text; border: 1px solid $border; selection-background-color: $accent_soft; selection-color: $text; }
QMenu::item:selected { background: $accent_soft; color: $accent; }
QToolTip { background: $header; color: $on_header; border: 1px solid $header; padding: 6px; }
QScrollBar:vertical { background: $surface_alt; width: 14px; }
QScrollBar:horizontal { background: $surface_alt; height: 14px; }
QScrollBar::handle { background: $border; border-radius: 4px; min-height: 24px; min-width: 24px; }
QScrollBar::handle:hover { background: $muted; }

QLabel#headerMutedText { color: $on_header_muted; background: transparent; }
QLabel#headingText { color: $heading; }
QLabel#successText { color: $success; }
QLabel#dangerText { color: $danger; font-weight: bold; }
QLabel#themeRecoveryNotice { color: $warning; }
QLabel#dialogWarningHeader { color: $warning; background: $warning_soft; font-size: 12pt; font-weight: bold; padding: 14px 20px; }
QLabel#dialogInfoHeader { color: $on_primary_soft; background: $primary_soft; font-size: 12pt; font-weight: bold; padding: 14px 20px; }
QFrame#summaryCard { border-radius: 6px; padding: 4px; }
QFrame#summaryCard[tone="success"] { background: $success_soft; }
QFrame#summaryCard[tone="danger"] { background: $danger_soft; }
QFrame#summaryCard[tone="primary"] { background: $primary_soft; }
QFrame#summaryCard[tone="accent"] { background: $accent_soft; }
QFrame#summaryCard QLabel { background: transparent; }
QFrame#summaryCard[tone="success"] QLabel { color: $success; }
QFrame#summaryCard[tone="danger"] QLabel { color: $danger; }
QFrame#summaryCard[tone="primary"] QLabel { color: $on_primary_soft; }
QFrame#summaryCard[tone="accent"] QLabel { color: $text; }
QLabel#summaryValue { font-size: 16px; font-weight: bold; }
QLabel#summaryCaption { font-size: 10px; }
QWidget:disabled { color: $muted; }
QMenu::item:disabled { color: $disabled_text; background: $disabled; }
QComboBox QAbstractItemView::item:disabled { color: $disabled_text; background: $disabled; }

QCheckBox::indicator, QAbstractItemView::indicator { width: 13px; height: 13px; border: 1px solid $border; background: $surface; }
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked { border-color: $primary; background: $primary; image: url("$check_mark"); }
QCheckBox::indicator:disabled, QAbstractItemView::indicator:disabled { border-color: $disabled_text; background: $disabled; }
QCheckBox::indicator:checked:disabled, QAbstractItemView::indicator:checked:disabled { image: url("$disabled_check_mark"); }
QComboBox::down-arrow { image: url("$control_down"); width: 8px; height: 5px; }
QComboBox::down-arrow:disabled { image: url("$disabled_control_down"); }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QTimeEdit::up-arrow, QDateEdit::up-arrow, QDateTimeEdit::up-arrow { image: url("$control_up"); width: 8px; height: 5px; }
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled, QTimeEdit::up-arrow:disabled, QDateEdit::up-arrow:disabled, QDateTimeEdit::up-arrow:disabled { image: url("$disabled_control_up"); }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QTimeEdit::down-arrow, QDateEdit::down-arrow, QDateTimeEdit::down-arrow { image: url("$control_down"); width: 8px; height: 5px; }
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled, QTimeEdit::down-arrow:disabled, QDateEdit::down-arrow:disabled, QDateTimeEdit::down-arrow:disabled { image: url("$disabled_control_down"); }
QGroupBox { border: 1px solid $divider; border-radius: 4px; margin-top: 10px; padding-top: 8px; }
QGroupBox::title { color: $heading; subcontrol-origin: margin; left: 8px; }
QProgressBar { color: $on_primary_soft; }
"""

_ICON_DIR = Path(__file__).resolve().parents[2] / "assets"
_icon_cache = {}
_resource_buffers = []


def _resource_svg(name, drawing, color, width=8, height=5):
    """Register a tiny trusted SVG entirely in memory, without a temp directory.

    Qt's public qRegisterResourceData accepts the same v1 tree/name/data buffers
    generated by rcc. One root and one leaf keep the fixed internal format small.
    Buffers remain owned for the process lifetime, as required by Qt resources.
    """
    key = (name, color)
    if key not in _icon_cache:
        filename = f'sorth_theme_{name}_{color[1:]}.svg'
        name_hash = 0
        for char in filename:
            name_hash = (name_hash << 4) + ord(char)
            name_hash ^= (name_hash & 0xf0000000) >> 23
            name_hash &= 0x0fffffff
        names = struct.pack('>HI', len(filename), name_hash) + filename.encode('utf-16-be')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
               f'viewBox="0 0 {width} {height}">{drawing.format(color=color)}</svg>').encode('ascii')
        data = struct.pack('>I', len(svg)) + svg
        tree = struct.pack('>IHII', 0, 2, 1, 1) + struct.pack('>IHHHI', 0, 0, 0, 1, 0)
        if not qRegisterResourceData(1, tree, names, data):
            raise ThemePreparationError('Could not prepare internal appearance icons')
        _resource_buffers.append((tree, names, data))
        _icon_cache[key] = ':/' + filename
    return _icon_cache[key]


def trusted_assets(spec: ThemeSpec | None = None):
    """Generate internal resources only; imported themes never provide paths."""
    spec = validate_theme((spec or current_theme()).to_dict())
    paths = {}
    for prefix, role in (('sort', 'on_header'), ('control', 'text'),
                         ('disabled_control', 'disabled_text')):
        color = spec.colors[role]
        for direction, points in (('up', '0,5 4,0 8,5'), ('down', '0,0 4,5 8,0')):
            name = prefix + '_' + direction
            if prefix == 'sort' and color.lower() == '#ffffff':
                paths[name] = (_ICON_DIR / f'sort-{direction}.svg').as_posix()
            else:
                paths[name] = _resource_svg(name, '<polygon points="' + points + '" fill="{color}"/>', color)
    check = '<path d="M2,6 L5,9 L10,3" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    paths['check_mark'] = _resource_svg('check', check, spec.colors['on_primary'], 13, 13)
    paths['disabled_check_mark'] = _resource_svg('check', check, spec.colors['disabled_text'], 13, 13)
    return MappingProxyType(paths)


def stylesheet_for(spec: ThemeSpec) -> str:
    spec = validate_theme(spec.to_dict())
    return Template(_QSS).substitute({**spec.colors, **trusted_assets(spec)})


def palette_for(spec: ThemeSpec) -> QPalette:
    """Complete app-owned palette for Active, Inactive and Disabled states."""
    spec = validate_theme(spec.to_dict())
    colors = spec.colors
    palette = QPalette()
    roles = {
        'Window': 'canvas', 'WindowText': 'text', 'Base': 'surface',
        'AlternateBase': 'surface_alt', 'ToolTipBase': 'header',
        'ToolTipText': 'on_header', 'Text': 'text', 'Button': 'surface',
        'ButtonText': 'text', 'BrightText': 'on_primary', 'Light': 'surface_alt',
        'Midlight': 'divider', 'Dark': 'border', 'Mid': 'border', 'Shadow': 'border',
        'Highlight': 'accent', 'HighlightedText': 'on_accent', 'Link': 'accent',
        'LinkVisited': 'accent', 'PlaceholderText': 'muted', 'Accent': 'accent',
    }
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive,
                  QPalette.ColorGroup.Disabled):
        for name, role in roles.items():
            qt_role = getattr(QPalette.ColorRole, name, None)
            if qt_role is None:
                continue
            if group == QPalette.ColorGroup.Disabled:
                role = {'Base': 'disabled', 'Button': 'disabled',
                        'Text': 'disabled_text', 'ButtonText': 'disabled_text',
                        'WindowText': 'muted', 'Highlight': 'disabled',
                        'HighlightedText': 'disabled_text', 'PlaceholderText': 'disabled_text',
                        'Link': 'muted', 'LinkVisited': 'muted'}.get(name, role)
            palette.setColor(group, qt_role, QColor(colors[role]))
    return palette


def _prepare_theme(spec):
    try:
        return stylesheet_for(spec), palette_for(spec)
    except (ThemeValidationError, ThemePreparationError):
        raise
    except Exception as error:
        raise ThemePreparationError(f'Could not prepare native appearance: {error}') from error


# Compatibility constant: Original, not a mutable live stylesheet snapshot.
STYLESHEET = stylesheet_for(_BUILTINS[0].spec)


def preview_theme(widget: QWidget, spec: ThemeSpec):
    """Style only a dialog-owned sample subtree; no preferences/global state."""
    spec = validate_theme(spec.to_dict())
    stylesheet, palette = _prepare_theme(spec)
    widget.setProperty('sorthThemePreview', True)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    widget.setPalette(palette)
    widget.setStyleSheet(stylesheet)
    widget.update()


class ThemeApplicationError(RuntimeError):
    """The preference committed, but an open control could not finish repainting."""
    def __init__(self, saved_theme, issues):
        self.saved_theme = saved_theme
        self.issues = tuple(issues)
        super().__init__('Appearance was saved, but some open controls could not update. '
                         'Restart SORTH to finish applying it. ' + '; '.join(self.issues))


class ThemeManager(QObject):
    changed = pyqtSignal(object)

    def __init__(self, app=None, preferences=None):
        app = app or QApplication.instance()
        if app is None:
            raise RuntimeError('A QApplication is required to apply appearance')
        super().__init__(app)
        from .theme_preferences import ThemePreferences
        self.app = app
        self.preferences = preferences if preferences is not None else ThemePreferences()
        self._current = self.preferences.current
        self._current_key = self.preferences.current_key
        self.application_issue = None
        self.startup_issue = None
        try:
            self._apply(self._current)
        except Exception as error:
            # Preparation can fail before a live style exists. The already-built
            # Original stylesheet is independent of imported/generated resources.
            # Preserve the saved record and report this separately from corruption.
            self.startup_issue = f'{type(error).__name__}: {error}'
            self._current_key = _BUILTINS[0].key
            self._apply(_BUILTINS[0].spec,
                        prepared=(STYLESHEET, palette_for(_BUILTINS[0].spec)))

    @property
    def current(self):
        return self._current

    @property
    def current_key(self):
        return self._current_key

    @property
    def recovery_issue(self):
        return self.preferences.recovery_issue

    def refresh_preferences(self):
        """Reconcile disk on explicit reopen; never apply or write during a read."""
        from .theme_preferences import ThemePreferences
        previous = self.preferences
        fresh = ThemePreferences(previous.path)
        changed = (fresh._snapshot != previous._snapshot or
                   fresh.recovery_issue != previous.recovery_issue)
        self.preferences = fresh
        return changed

    def _apply(self, spec, *, prepared=None):
        global _current
        stylesheet, palette = prepared or _prepare_theme(spec)
        _current = self._current = spec
        issues = []
        for name, operation, value in (('palette', self.app.setPalette, palette),
                                       ('stylesheet', self.app.setStyleSheet, stylesheet)):
            try:
                operation(value)
            except Exception as error:
                issues.append(f'{name}: {type(error).__name__}: {error}')
        # A failed custom refresh never prevents remaining owned controls from
        # updating, and never turns a successful disk commit into a failed save.
        for widget in self.app.allWidgets():
            if sip.isdeleted(widget):
                continue
            try:
                ancestor = widget
                in_preview = False
                while ancestor is not None:
                    if ancestor.property('sorthThemePreview'):
                        in_preview = True
                        break
                    ancestor = ancestor.parentWidget()
                if in_preview:
                    continue
                refresh = getattr(widget, 'refresh_theme', None)
                if refresh is not None:
                    refresh()
                widget.update()
            except Exception as error:
                issues.append(f'{type(widget).__name__}: {type(error).__name__}: {error}')
        self.application_issue = '; '.join(issues) if issues else None
        return tuple(issues)

    def save_and_apply(self, spec: ThemeSpec, key='custom', *, recover=False):
        """Commit first; distinguish rejected save from incomplete live refresh."""
        spec = validate_theme(spec.to_dict())
        prepared = _prepare_theme(spec)
        self.preferences.save(spec, key=key, recover=recover)
        self._current_key = self.preferences.current_key
        self.startup_issue = None
        issues = self._apply(self.preferences.current, prepared=prepared)
        self.changed.emit(self.current)
        if issues:
            raise ThemeApplicationError(self.current, issues)
        return self.current


def theme_manager() -> ThemeManager:
    app = QApplication.instance()
    if app is None:
        raise RuntimeError('A QApplication is required to apply appearance')
    manager = getattr(app, '_sorth_theme_manager', None)
    if manager is None or sip.isdeleted(manager):
        manager = ThemeManager(app)
        app._sorth_theme_manager = manager
    return manager


def apply_theme(widget):
    """Join SORTH's app-local appearance without changing operating-system settings."""
    theme_manager()
    widget.update()
