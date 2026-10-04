"""Compact native course edits retain readable fields and exact saved meaning."""
from copy import deepcopy
from pathlib import Path
import time

import pytest
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QStyleFactory

from src.gui.course_manager_widget import CourseDialog
from src.gui.i18n import language_manager
from src.gui.theme import builtin_themes, theme_manager
from src.gui.theme_contract import load_theme_file
from src.scheduling.course import Course


CUSTOM = load_theme_file(Path(__file__).resolve().parents[3] /
    '.agents/skills/sorth-theme-designer/assets/midnight-dark.sorth-theme.json')
LARGE = 'QPushButton, QCheckBox, QLabel, QTimeEdit, QSpinBox, QLineEdit, QComboBox { font-size: 20pt; }'


def settle(dialog):
    deadline = time.monotonic() + 2
    previous = None
    stable = 0
    while time.monotonic() < deadline:
        QApplication.processEvents()
        snapshot = (dialog.size(), dialog.scroll.viewport().size(),
            dialog.scroll.widget().size(), dialog.buttons.size(),
            tuple((control.geometry(), control.minimumSizeHint()) for control in controls(dialog)))
        stable = stable + 1 if snapshot == previous and not (
            dialog._responsive_actions.timer.isActive() or dialog.buttons._metric_timer.isActive()
            or dialog._focus_reveal_timer.isActive()) else 0
        if stable >= 2:
            return
        previous = snapshot
        QTest.qWait(1)
    pytest.fail('Course dialog native layout did not settle')


def controls(dialog):
    return [dialog.code_edit, dialog.name_edit, dialog.groups_spin, dialog.dur_hours,
            dialog.dur_mins, dialog.room_type_label, dialog.classroom_edit,
            dialog.day_combo, dialog.chk_pref_time, dialog.pref_time_edit, dialog.split_combo]


@pytest.fixture
def presentation():
    app = QApplication.instance()
    manager = theme_manager()
    original = (app.style().objectName(), language_manager().language, manager.current)
    yield app, manager
    app.setStyle(original[0])
    language_manager().set_language(original[1], persist=False)
    manager._apply(original[2])


def assert_fits(dialog):
    assert dialog.size() == QSize(460, 420)
    assert dialog.scroll.horizontalScrollBar().maximum() == 0
    assert dialog.scroll.viewport().height() >= 200
    for action in dialog.buttons.buttons():
        assert action.isVisible()
        assert action.width() >= action.minimumSizeHint().width()
        assert action.height() >= action.minimumSizeHint().height()
        assert dialog.rect().contains(action.mapTo(dialog, action.rect().topLeft()))
        assert dialog.rect().contains(action.mapTo(dialog, action.rect().bottomRight()))
    time_bottom = dialog.pref_time_edit.mapTo(
        dialog.scroll.widget(), dialog.pref_time_edit.rect().bottomLeft()).y()
    assert time_bottom < dialog.split_combo.y()
    for control in controls(dialog):
        assert control.isVisible()
        assert control.height() >= control.minimumSizeHint().height(), (
            type(control).__name__, control.geometry(), control.minimumSizeHint())


@pytest.mark.parametrize('style_name', ['Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('large', [False, True])
@pytest.mark.parametrize('spec', [builtin_themes()[0].spec, builtin_themes()[1].spec, CUSTOM],
                         ids=['light', 'dark', 'custom'])
def test_compact_form_and_live_locale_keep_controls_complete(presentation, style_name, locale, large, spec):
    app, manager = presentation
    if style_name not in QStyleFactory.keys():
        pytest.skip(f'{style_name} unavailable')
    app.setStyle(style_name)
    manager._apply(spec)
    language_manager().set_language(locale, persist=False)
    course = Course('BIOP', 51, 959, 'REGULAR', name='Long restored name ' * 100,
                    preferred_start_min=819, preferred_day='Domingo', force_split=False)
    dialog = CourseDialog(course=course)
    if large:
        dialog.setStyleSheet(LARGE)
    dialog.show()
    for language in [locale, 'en' if locale == 'es' else 'es', locale]:
        language_manager().set_language(language, persist=False)
        settle(dialog)
        assert_fits(dialog)
        assert vars(dialog.get_course()) == vars(course)
        assert dialog.name_edit.text() == course.name
        assert dialog.day_combo.currentData() == 'Domingo'
        assert dialog.pref_time_edit.accessibleName() == (
            'Preferred start time' if language == 'en' else 'Hora de inicio preferida')
        assert 'REGULAR' in dialog.room_type_label.text()
        assert ('saved in the course' if language == 'en' else 'guardado en el curso') in dialog.room_type_label.text()
        if large:
            assert all(control.font().pointSize() == 20 for control in controls(dialog))
    dialog.reject()


@pytest.mark.parametrize('backwards', [False, True], ids=['Tab', 'Shift-Tab'])
@pytest.mark.parametrize('locale', ['es', 'en'])
def test_keyboard_reveals_whole_fields_and_cancel_reopens_saved_values(presentation, backwards, locale):
    _, manager = presentation
    manager._apply(CUSTOM)
    language_manager().set_language(locale, persist=False)
    course = Course('BIOP', 1, 60, 'REGULAR', name='Original ' * 200,
                    preferred_start_min=819, size=30, group_suggestions=[{'aula': 'R'}])
    original = deepcopy(vars(course))
    for repeat in range(2):
        dialog = CourseDialog(course=course)
        dialog.setStyleSheet(LARGE)
        dialog.show()
        settle(dialog)
        assert vars(dialog.get_course()) == original
        dialog.name_edit.setText('Draft only')
        dialog.groups_spin.setValue(2)
        dialog.code_edit.setFocus()
        seen = []
        modifier = Qt.KeyboardModifier.ShiftModifier if backwards else Qt.KeyboardModifier.NoModifier
        for _ in range(30):
            QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab, modifier)
            settle(dialog)
            focused = QApplication.focusWidget()
            assert focused is not None
            if focused is dialog.code_edit:
                break
            seen.append(focused)
            if dialog.scroll.widget().isAncestorOf(focused):
                viewport = dialog.scroll.viewport()
                assert viewport.rect().contains(focused.mapTo(viewport, focused.rect().topLeft()))
                assert viewport.rect().contains(focused.mapTo(viewport, focused.rect().bottomRight()))
            assert_fits(dialog)
        else:
            pytest.fail('Tab traversal did not return to course code')
        assert all(control in seen for control in controls(dialog)[1:])
        assert all(action in seen for action in dialog.buttons.buttons())
        QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Escape)
        assert not dialog.isVisible()
        assert vars(course) == original


@pytest.mark.parametrize('original_code,room_type', [
    ('BIOP', 'REGULAR'), ('BIO', 'LAB'), (' BIOP ', 'REGULAR'), (' bio ', 'LAB')])
def test_displayed_room_type_matches_preserved_or_new_code(presentation, original_code, room_type):
    original = Course(original_code, 1, 60, room_type, name=' Literal ', size=25,
                      group_suggestions=[{'aula': 'R'}])
    original.extra_metadata = {'keep': [1, 2]}
    dialog = CourseDialog(course=original)
    for code in [original_code, ' NEWP ', original_code, ' NEW ', original_code]:
        dialog.code_edit.setText(code)
        for locale in ['es', 'en']:
            language_manager().set_language(locale, persist=False)
            result = dialog.get_course()
            expected = room_type if code == original_code else ('LAB' if code.strip().endswith('P') else 'REGULAR')
            assert result.required_room_type == expected
            if code == original_code:
                assert dialog.room_type_label.text().startswith(expected)
            else:
                assert expected in dialog.room_type_label.text()
            assert result.name == original.name
            assert result.size == original.size
            assert result.group_suggestions == original.group_suggestions
            assert result.extra_metadata == original.extra_metadata
            if code == original_code:
                assert vars(result) == vars(original)
    dialog.reject()


def test_normalized_code_matching_original_keeps_saved_type(presentation):
    dialog = CourseDialog(course=Course('BIOP', 1, 60, 'REGULAR'))
    dialog.code_edit.setText(' BIOP ')
    assert dialog.get_course().code == 'BIOP'
    assert dialog.get_course().required_room_type == 'REGULAR'
    assert dialog.room_type_label.text().startswith('REGULAR')


@pytest.mark.parametrize('locale', ['es', 'en'])
def test_native_split_popup_and_widening_preserve_draft(presentation, locale):
    _, manager = presentation
    manager._apply(CUSTOM)
    language_manager().set_language(locale, persist=False)
    dialog = CourseDialog(course=Course('BIO', 1, 60, 'LAB', name='Restored ' * 100))
    dialog.setStyleSheet(LARGE)
    dialog.show()
    settle(dialog)
    dialog.split_combo.setFocus()
    settle(dialog)
    dialog.split_combo.showPopup()
    QApplication.processEvents()
    view = dialog.split_combo.view()
    assert view.isVisible()
    for row in range(dialog.split_combo.count()):
        caption = dialog.split_combo.itemText(row)
        assert view.viewport().width() >= view.fontMetrics().horizontalAdvance(caption)
    QTest.keyClick(view, Qt.Key.Key_End)
    QTest.keyClick(view, Qt.Key.Key_Return)
    settle(dialog)
    assert not view.isVisible()
    assert dialog.get_course().force_split is False
    assert dialog.isVisible()
    expected = vars(dialog.get_course())
    dialog.name_edit.setFocus()
    dialog.name_edit.setSelection(4, 8)
    for width in [1000, 460, 1000, 460]:
        dialog.resize(width, 420)
        settle(dialog)
        assert dialog.size() == QSize(width, 420)
        assert dialog.scroll.horizontalScrollBar().maximum() == 0
        assert dialog.name_edit.hasFocus()
        assert dialog.name_edit.selectionStart() == 4
        assert dialog.name_edit.selectedText() == dialog.name_edit.text()[4:12]
        assert vars(dialog.get_course()) == expected
        if width == 460:
            assert_fits(dialog)
    dialog.reject()
