"""Shared quiet focus stays visible without moving native control contents."""
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateEdit,
    QDateTimeEdit, QDoubleSpinBox, QLabel, QLineEdit, QListWidget, QPlainTextEdit,
    QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTextEdit, QTimeEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from src.gui.theme import builtin_themes, preview_theme
from src.gui.theme_contract import load_theme_file

CUSTOM = load_theme_file(Path(__file__).resolve().parents[3] /
    '.agents/skills/sorth-theme-designer/assets/midnight-dark.sorth-theme.json')
THEMES = [choice.spec for choice in builtin_themes()] + [CUSTOM]


def focus_sample(spec, language='es', points=10):
    root = QWidget()
    layout = QVBoxLayout(root)
    label = QLabel('Campo seleccionado' if language == 'es' else 'Selected field')
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard)
    button = QPushButton('Guardar' if language == 'es' else 'Save')
    check = QCheckBox('Activar opción' if language == 'es' else 'Enable option')
    check.setChecked(True)
    line = QLineEdit('LBIOCOMP')
    combo = QComboBox(); combo.addItems(['LBIOCOMP', 'LAB-02'])
    table = QTableWidget(1, 1); table.setItem(0, 0, QTableWidgetItem('LBIOCOMP'))
    table.setCurrentCell(0, 0)
    items = QListWidget(); items.addItem('LBIOCOMP'); items.setCurrentRow(0)
    tree = QTreeWidget(); tree.addTopLevelItem(QTreeWidgetItem(['LBIOCOMP']))
    controls = [line, check, combo, QSpinBox(), QDoubleSpinBox(), QTimeEdit(),
                QDateEdit(), QDateTimeEdit(), button, label, table, items, tree,
                QPlainTextEdit('LBIOCOMP'), QTextEdit('LBIOCOMP')]
    for control in controls:
        if isinstance(control, (QPlainTextEdit, QTextEdit)):
            control.setTabChangesFocus(True)
        layout.addWidget(control)
        if isinstance(control, (QTableWidget, QListWidget, QTreeWidget, QPlainTextEdit, QTextEdit)):
            control.setFixedHeight(90)
    preview_theme(root, spec)
    root.setStyleSheet(root.styleSheet() + f'\nQWidget {{ font-size: {points}pt; }}')
    root.resize(480, 1300)
    root.show(); root.activateWindow()
    QApplication.processEvents()
    return root, controls


@pytest.mark.parametrize('style', ['Fusion', 'Windows'])
@pytest.mark.parametrize('spec', THEMES, ids=lambda spec: spec.name)
@pytest.mark.parametrize('language,points', [('es', 10), ('en', 20)])
def test_shared_focus_geometry_and_paint(style, spec, language, points):
    app = QApplication.instance()
    previous = app.style().objectName()
    root = None
    try:
        app.setStyle(style)
        root, controls = focus_sample(spec, language, points)
        # Establish settled resting geometry with focus outside every control.
        root.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        root.setFocus(); app.processEvents()
        geometry = [control.geometry() for control in controls]
        hints = [control.sizeHint() for control in controls]
        for index, control in enumerate(controls):
            control.setFocus(Qt.FocusReason.TabFocusReason); app.processEvents()
            assert control.hasFocus()
            assert [item.geometry() for item in controls] == geometry
            assert control.sizeHint() == hints[index]
            image = control.grab().toImage()
            focus_color = spec.colors['focus'].lower()
            # The authored one-pixel boundary must actually paint, not merely
            # exist in a selector which a more-specific platform rule hides.
            dpr = image.devicePixelRatio()
            x = image.width() // 2
            assert any(image.pixelColor(x, y).name() == focus_color
                       for y in range(min(image.height(), max(3, int(3*dpr)))))
            # Native date/time fields traverse their sections before leaving.
            for _ in range(8):
                QTest.keyClick(control, Qt.Key.Key_Tab)
                if app.focusWidget() is not control:
                    break
            assert app.focusWidget() is not control
        # A selected item remains selected when keyboard focus leaves it.
        table = controls[10]
        controls[0].setFocus(); app.processEvents()
        assert table.item(0, 0).isSelected()
        checkbox = controls[1]
        checkbox.setFocus(); QTest.keyClick(checkbox, Qt.Key.Key_Space)
        assert not checkbox.isChecked()
    finally:
        if root is not None:
            root.close()
        app.setStyle(previous)


@pytest.mark.parametrize('style', ['Fusion', 'Windows'])
@pytest.mark.parametrize('spec', THEMES, ids=lambda spec: spec.name)
def test_semantic_action_focus_and_tab_selection(spec, style):
    from PyQt6.QtWidgets import QTabWidget
    app = QApplication.instance()
    previous_style = app.style().objectName()
    app.setStyle(style)
    root = QWidget(); layout = QVBoxLayout(root)
    root.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    buttons = []
    for role in ('primaryAction', 'headerAction', 'dangerAction'):
        button = QPushButton('Action'); button.setObjectName(role)
        layout.addWidget(button); buttons.append(button)
    tabs = QTabWidget(); tabs.addTab(QWidget(), 'Cursos'); tabs.addTab(QWidget(), 'Horario')
    layout.addWidget(tabs)
    preview_theme(root, spec)
    root.show(); root.activateWindow(); app.processEvents()
    try:
        for button, color in zip(buttons, ('on_primary', 'on_header', 'focus')):
            root.setFocus(); app.processEvents()
            resting = button.grab().toImage()
            size = button.sizeHint()
            button.setFocus(); app.processEvents()
            assert button.sizeHint() == size
            image = button.grab().toImage()
            assert image != resting, 'Keyboard focus must be distinguishable from resting paint.'
            assert image.pixelColor(image.width()//2, 0).name() == spec.colors[color].lower()
        bar = tabs.tabBar()
        before = bar.tabRect(0)
        bar.setFocus(); app.processEvents()
        assert bar.tabRect(0) == before
        assert tabs.currentIndex() == 0
        QTest.keyClick(bar, Qt.Key.Key_Right)
        assert tabs.currentIndex() == 1
    finally:
        root.close()
        app.setStyle(previous_style)
