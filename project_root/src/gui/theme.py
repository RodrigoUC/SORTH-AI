"""SORTH desktop palette. Role names are independent of interface language."""

COLORS = {
    "canvas": "#EFF3F9", "surface": "#FFFFFF", "surface_alt": "#F3F6FC",
    "navy": "#183153", "navy_hover": "#24476E", "on_navy": "#FFFFFF",
    "on_navy_muted": "#D3E5FA", "text": "#1D2D44", "muted": "#52647D",
    "border": "#7688A1", "divider": "#D6DFEB",
    "primary": "#087F83", "primary_hover": "#066B70", "primary_pressed": "#055A61",
    "on_primary": "#FFFFFF", "primary_soft": "#E2F4F2",
    "accent": "#6545AD", "accent_soft": "#EFE9FA", "focus": "#6545AD",
    "disabled": "#E1E7F0", "disabled_text": "#56667D",
    "success": "#246448", "success_soft": "#E3F3EA",
    "warning": "#88551A", "warning_soft": "#FFF0D5",
    "danger": "#A12D46", "danger_soft": "#FCE8EC",
}

# Substitution keeps Qt selectors readable and every color role in one owner.
_QSS = """
QWidget { font-family: 'Segoe UI', 'DejaVu Sans', sans-serif; font-size: 10pt; color: $text; }
QMainWindow, QDialog { background: $canvas; }
QFrame#brandHeader { background: $navy; border-radius: 9px; }
QLabel#appTitle { font-size: 24pt; font-weight: 700; color: $on_navy; background: transparent; }
QLabel#subtitle { color: $on_navy_muted; padding-left: 12px; background: transparent; }
QLabel#overview { padding: 10px 12px; color: $navy; background: $primary_soft; border-radius: 6px; font-size: 11pt; }
QLabel#helpText { background: $accent_soft; color: $text; padding: 12px; border-radius: 6px; }
QLabel#mutedText { color: $muted; }
QFrame#settingsHeader { background: $navy; border-radius: 7px; }
QLabel#settingsTitle { color: $on_navy; background: transparent; font-size: 14pt; font-weight: 700; }
QLabel#settingsSubtitle { color: $on_navy_muted; background: transparent; }
QWidget#settingsContent { background: $surface; border-radius: 7px; }
QLabel#settingsSectionTitle { color: $navy; font-size: 12pt; font-weight: 700; }
QLabel#settingsStepTitle { color: $navy; font-weight: 600; }
QFrame#settingsDivider { background: $divider; border: 0; }
QLabel#settingsNotice { color: $muted; background: $surface_alt; padding: 10px; border-radius: 5px; }
QLabel#settingsSaveState { color: $muted; }
QLabel#settingsSaveState[pending="true"] { color: $warning; }

QPushButton { background: $surface; border: 1px solid $border; border-radius: 5px; padding: 8px 14px; }
QPushButton:hover { background: $primary_soft; border-color: $primary; }
QPushButton:pressed, QPushButton:checked { background: $accent_soft; border-color: $accent; }
QPushButton:disabled { background: $disabled; color: $disabled_text; border-color: $divider; }
QPushButton#headerAction { background: $navy; border-color: $on_navy_muted; color: $on_navy; }
QPushButton#headerAction:hover, QPushButton#headerAction:checked { background: $navy_hover; }
QPushButton#primaryAction { background: $primary; border-color: $primary; color: $on_primary; font-weight: 600; }
QPushButton#primaryAction:hover { background: $primary_hover; border-color: $primary_hover; }
QPushButton#primaryAction:pressed { background: $primary_pressed; border-color: $primary_pressed; }
QPushButton#primaryAction:disabled { background: $disabled; border-color: $divider; color: $disabled_text; }
QPushButton#dangerAction { color: $danger; border-color: $danger; }
QPushButton#dangerAction:hover { background: $danger_soft; }
QPushButton#dangerAction:disabled { color: $disabled_text; border-color: $divider; background: $disabled; }
QLineEdit, QSpinBox, QTimeEdit, QComboBox { background: $surface; border: 1px solid $border; border-radius: 4px; padding: 6px; selection-background-color: $accent; selection-color: $surface; }
QLineEdit { placeholder-text-color: $muted; }
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled { background: $disabled; color: $disabled_text; }
QPushButton:focus, QPushButton#primaryAction:focus, QPushButton#dangerAction:focus, QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus, QComboBox:focus, QTableWidget:focus, QListWidget:focus, QPlainTextEdit:focus, QLabel:focus { border: 2px solid $focus; }
QPushButton#primaryAction:focus { border: 2px solid $on_primary; }
QPushButton#headerAction:focus { border: 2px solid $on_navy; }
QCheckBox:focus, QTabBar::tab:focus { border: 2px solid $focus; }
QTabWidget::pane { border: 1px solid $divider; background: $surface; }
QTabBar::tab { padding: 11px 20px; background: $accent_soft; color: $muted; border: 0; margin-right: 3px; }
QTabBar::tab:selected { background: $surface; color: $accent; font-weight: 600; border-bottom: 3px solid $accent; }
QTabBar::tab:hover:!selected { background: $primary_soft; color: $primary_hover; }
QTabBar::tab:focus { border-top: 2px solid $focus; }
QTableWidget { background: $surface; alternate-background-color: $surface_alt; border: 1px solid $divider; gridline-color: $divider; selection-background-color: $accent_soft; selection-color: $text; }
QTableWidget::item:focus { border: 1px solid $focus; }
QHeaderView::section { background: $navy; color: $on_navy; padding: 9px 7px; border: 0; border-bottom: 1px solid $navy; font-weight: 600; }
QHeaderView::up-arrow { image: url("$sort_up"); width: 8px; height: 5px; }
QHeaderView::down-arrow { image: url("$sort_down"); width: 8px; height: 5px; }
QTableCornerButton::section { background: $navy; border: 0; }
QStatusBar { background: $navy; color: $on_navy_muted; padding: 5px; }
QStatusBar QLabel { color: $on_navy_muted; }
QStatusBar QCheckBox { color: $on_navy_muted; border: 1px solid transparent; padding: 1px 3px; }
QStatusBar QCheckBox:focus { border-color: $on_navy; }
QProgressBar { background: $primary_soft; border: 0; border-radius: 3px; }
QProgressBar::chunk { background: $primary; }
QMenu, QComboBox QAbstractItemView { background: $surface; color: $text; border: 1px solid $border; selection-background-color: $accent_soft; selection-color: $text; }
QMenu::item:selected { background: $accent_soft; color: $accent; }
QToolTip { background: $navy; color: $on_navy; border: 1px solid $navy; padding: 6px; }
QScrollBar:vertical { background: $surface_alt; width: 14px; }
QScrollBar:horizontal { background: $surface_alt; height: 14px; }
QScrollBar::handle { background: $border; border-radius: 4px; min-height: 24px; min-width: 24px; }
QScrollBar::handle:hover { background: $muted; }
"""

from pathlib import Path
from string import Template

_ICON_DIR = Path(__file__).resolve().parents[2] / "assets"
COLORS["sort_up"] = (_ICON_DIR / "sort-up.svg").as_posix()
COLORS["sort_down"] = (_ICON_DIR / "sort-down.svg").as_posix()
STYLESHEET = Template(_QSS).substitute(COLORS)


def apply_theme(widget):
    widget.setStyleSheet(STYLESHEET)
