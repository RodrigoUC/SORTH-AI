"""Native calendar controls remain readable and reachable on a small desktop."""
from pathlib import Path
import re
import time

import pytest
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QStyleFactory, QWidget, QDialogButtonBox

from src.gui.calendar_dialog import CalendarDialog
from src.gui.i18n import language_manager
from src.gui.theme import builtin_themes, theme_manager
from src.gui.theme_contract import load_theme_file
from src.scheduling.project_calendar import ProjectCalendar
from tests.test_gui.test_project_calendar import window


CUSTOM = load_theme_file(Path(__file__).resolve().parents[3] /
                         '.agents/skills/sorth-theme-designer/assets/midnight-dark.sorth-theme.json')


def settle(dialog):
    deadline = time.monotonic() + 2
    previous = None
    stable = 0
    while time.monotonic() < deadline:
        QApplication.processEvents()
        snapshot = (dialog.size(), dialog.scroll.viewport().size(),
                    dialog.scroll.widget().size(), dialog.buttons.size(),
                    tuple((action.text(), action.size()) for action in dialog.break_actions))
        stable = stable + 1 if snapshot == previous and not (
            dialog._responsive_actions.timer.isActive() or dialog.buttons._metric_timer.isActive()
            or dialog._focus_reveal_timer.isActive()) else 0
        if stable >= 2:
            return
        previous = snapshot
        QTest.qWait(1)
    pytest.fail('Calendar native layout did not settle')


@pytest.fixture
def dialog():
    parent = QWidget()
    parent.calendar = ProjectCalendar()
    result = CalendarDialog(parent)
    yield result
    result.reject()
    parent.close()


@pytest.fixture
def presentation():
    app = QApplication.instance()
    manager = theme_manager()
    original = (app.style().objectName(), language_manager().language, manager.current)
    yield app, manager
    app.setStyle(original[0])
    language_manager().set_language(original[1], persist=False)
    manager._apply(original[2])


def assert_footer_visible(dialog):
    for action in dialog.buttons.buttons():
        assert action.isVisible()
        assert action.width() >= action.minimumSizeHint().width()
        assert action.height() >= action.minimumSizeHint().height()
        assert dialog.rect().contains(action.mapTo(dialog, action.rect().topLeft()))
        assert dialog.rect().contains(action.mapTo(dialog, action.rect().bottomRight()))


@pytest.mark.parametrize('style_name', ['Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('large', [False, True])
@pytest.mark.parametrize('spec', [builtin_themes()[0].spec, builtin_themes()[1].spec, CUSTOM],
                         ids=['light', 'dark', 'custom'])
def test_calendar_fits_complete_controls_at_compact_size(dialog, presentation, style_name, locale, large, spec):
    app, manager = presentation
    if style_name not in QStyleFactory.keys():
        pytest.skip(f'{style_name} unavailable')
    app.setStyle(style_name)
    manager._apply(spec)
    language_manager().set_language(locale, persist=False)
    if large:
        dialog.setStyleSheet('QPushButton, QCheckBox, QLabel, QTimeEdit { font-size: 20pt; }')
    dialog.resize(460, 420)
    dialog.show()
    settle(dialog)
    assert dialog.size() == QSize(460, 420)
    assert dialog.scroll.horizontalScrollBar().maximum() == 0
    assert dialog.scroll.viewport().height() >= 200
    assert_footer_visible(dialog)
    for action in [*dialog.days.values(), *dialog.break_actions]:
        assert action.width() >= action.minimumSizeHint().width()
        assert action.height() >= action.minimumSizeHint().height()
        source = action._messages['setText'][1][0].render()
        assert re.fullmatch(r'\s*'.join(re.escape(part) for part in action.text().split('\n')), source)
        assert action.accessibleName() == source
    for row in range(dialog.breaks.rowCount()):
        for column in range(2):
            control = dialog.breaks.cellWidget(row, column)
            assert control.height() >= control.minimumSizeHint().height()
            assert dialog.breaks.rowHeight(row) >= control.minimumSizeHint().height()
    assert dialog.value() == ProjectCalendar()


@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('backwards', [False, True], ids=['Tab', 'Shift-Tab'])
def test_keyboard_reaches_controls_and_footer_after_repeated_break_edits(dialog, presentation, locale, backwards):
    language_manager().set_language(locale, persist=False)
    dialog.setStyleSheet('QPushButton, QCheckBox, QLabel, QTimeEdit { font-size: 20pt; }')
    dialog.resize(460, 420)
    dialog.show()
    for repeat in range(3):
        dialog.add_break(900, 930)
        dialog.breaks.setCurrentCell(0, 0)
        dialog.remove_break()
        settle(dialog)
        first = dialog.days['Lunes']
        first.setFocus()
        seen = []
        modifiers = Qt.KeyboardModifier.ShiftModifier if backwards else Qt.KeyboardModifier.NoModifier
        for _ in range(60):
            QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab, modifiers)
            settle(dialog)
            focused = QApplication.focusWidget()
            assert focused is not None and focused.isVisible()
            if focused is first:
                break
            seen.append(focused)
            if dialog.scroll.widget().isAncestorOf(focused):
                viewport = dialog.scroll.viewport()
                assert viewport.rect().contains(focused.mapTo(viewport, focused.rect().center()))
        else:
            pytest.fail('Calendar Tab traversal never returned to the first weekday')
        required = [*list(dialog.days.values())[1:], dialog.opening, dialog.closing,
                    *dialog.break_actions, dialog.apply_button,
                    dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel)]
        required.extend(dialog.breaks.cellWidget(row, column)
                        for row in range(dialog.breaks.rowCount()) for column in range(2))
        assert all(control in seen for control in required)
        assert_footer_visible(dialog)
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Escape)
    assert not dialog.isVisible()
    assert dialog.parentWidget().calendar == ProjectCalendar()


def test_locale_resize_reflow_preserves_draft_and_input_names(dialog, presentation):
    dialog.setStyleSheet('QPushButton, QCheckBox, QLabel, QTimeEdit { font-size: 20pt; }')
    dialog.days['Martes'].setChecked(False)
    dialog.add_break(900, 930)
    expected = dialog.value()
    dialog.show()
    for locale in ['en', 'es', 'en']:
        language_manager().set_language(locale, persist=False)
        assert dialog.opening.accessibleName() == ('Opening time' if locale == 'en' else 'Hora de apertura')
        assert dialog.breaks.cellWidget(0, 0).accessibleName() == ('Break start' if locale == 'en' else 'Inicio del descanso')
        for width in [460, 1200, 460]:
            dialog.resize(width, 420)
            settle(dialog)
            assert dialog.size() == QSize(width, 420)
            assert dialog.scroll.horizontalScrollBar().maximum() == 0
            assert_footer_visible(dialog)
            assert dialog.value() == expected
    dialog.reject()


def test_validation_feedback_and_resizing_keep_focus_reachable(dialog, presentation):
    dialog.setStyleSheet('QPushButton, QCheckBox, QLabel, QTimeEdit { font-size: 20pt; }')
    dialog.resize(460, 420)
    dialog.show()
    settle(dialog)
    dialog._show_feedback('Synthetic validation feedback. ' * 6)
    settle(dialog)
    assert dialog.feedback.hasFocus()
    assert dialog.feedback.isVisible()
    for size in [QSize(1000, 720), QSize(460, 420)]:
        dialog.resize(size)
        settle(dialog)
        viewport = dialog.scroll.viewport()
        assert viewport.rect().contains(dialog.feedback.mapTo(viewport, dialog.feedback.rect().center()))
        assert_footer_visible(dialog)
    assert dialog.value() == ProjectCalendar()


def test_invalid_calendar_reveals_error_and_cancel_preserves_disk(window, presentation):
    assert window._save_session()
    before = Path(window._repo._db_path).read_bytes()
    dialog = CalendarDialog(window)
    dialog.setStyleSheet('QPushButton, QCheckBox, QLabel, QTimeEdit { font-size: 20pt; }')
    dialog.resize(460, 420)
    dialog.show()
    for control in dialog.days.values():
        control.setChecked(False)
    dialog.apply_button.click()
    settle(dialog)
    assert dialog.isVisible() and dialog.feedback.hasFocus()
    assert dialog.feedback.text()
    viewport = dialog.scroll.viewport()
    assert viewport.rect().contains(dialog.feedback.mapTo(viewport, dialog.feedback.rect().center()))
    dialog.load(ProjectCalendar())
    dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel).click()
    assert not dialog.isVisible()
    assert window.calendar == ProjectCalendar()
    assert Path(window._repo._db_path).read_bytes() == before
