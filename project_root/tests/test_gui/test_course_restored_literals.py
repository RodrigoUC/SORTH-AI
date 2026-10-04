"""Untouched restored literals survive an editor; real edits still normalize."""
from copy import deepcopy

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QDialog

from src.application.edit_history import encoded
from src.gui.course_manager_widget import CourseDialog, QMessageBox
from src.gui.main_window import MainWindow
from src.infrastructure.excel_reader import ExcelReader
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def restored_window(tmp_path):
    repo = SessionRepository(str(tmp_path / 'session.db'))
    window = MainWindow(repo, restore_session=False,
        feature_settings=QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat))
    yield window
    window._unsaved = False
    window.close()


def restore_course(window, course):
    groups = course.generate_groups()
    assignments = {groups[0].group_id: ('R', 1, 480, 540)}
    window._repo.save_session(None, 42, {'R': Classroom('R', 30, 'REGULAR')},
                             [course], {}, assignments)
    window._restore_session_if_exists(confirm=False, show_status=False)
    assert not window._restore_failed
    assert window.current_schedule == assignments


@pytest.mark.parametrize('field,value', [
    ('name', ''), ('name', ' Biology '), ('code', ' BIO '),
    ('suggested_classroom', ''), ('suggested_classroom', ' R '),
    ('force_split', None), ('force_split', True), ('force_split', False),
])
@pytest.mark.parametrize('history_enabled', [False, True])
def test_restored_literal_noop_preserves_state_disk_and_both_history_branches(
        restored_window, tmp_path, monkeypatch, field, value, history_enabled):
    window = restored_window
    course = Course('BIO', 1, 60, 'REGULAR')
    setattr(course, field, value)
    restore_course(window, course)
    window._features.save({**window._features.values(), 'undo_redo': True, 'pinned_sessions': True})
    gid = course.generate_groups()[0].group_id
    window._toggle_pin(gid)
    window._toggle_pin(gid)
    assert window._travel_history(True)
    assert window._history.can_undo and window._history.can_redo
    window._features.save({**window._features.values(), 'undo_redo': history_enabled})
    before = encoded(window._capture_edit_state())
    history = encoded(vars(window._history))
    disk = (tmp_path / 'session.db').read_bytes()
    monkeypatch.setattr(window._repo, 'save_session', lambda **kwargs: pytest.fail('No-op must not save'))
    monkeypatch.setattr(CourseDialog, 'exec', lambda dialog: QDialog.DialogCode.Accepted)
    window.course_manager.edit_course_by_code(course.code)
    assert encoded(window._capture_edit_state()) == before
    assert encoded(vars(window._history)) == history
    assert (tmp_path / 'session.db').read_bytes() == disk


@pytest.mark.parametrize('field,text,expected', [
    ('code', ' NEWP ', 'NEWP'), ('name', ' Changed ', 'Changed'),
    ('suggested_classroom', ' R2 ', 'R2'), ('name', '   ', None),
    ('suggested_classroom', '   ', None),
])
def test_actual_text_edit_normalizes_only_changed_field(restored_window, field, text, expected):
    window = restored_window
    original = Course(' BIO ', 1, 60, 'REGULAR', name='', suggested_classroom=' R ')
    restore_course(window, original)
    dialog = CourseDialog(window, window.course_manager.courses[0])
    editor = {'code': dialog.code_edit, 'name': dialog.name_edit,
              'suggested_classroom': dialog.classroom_edit}[field]
    editor.setText(text)
    result = dialog.get_course()
    expected_values = deepcopy(vars(original))
    expected_values[field] = expected
    if field == 'code':
        expected_values['required_room_type'] = 'LAB'
    assert vars(result) == expected_values
    assert window.course_manager._replace_course(0, result)
    assert vars(window._repo.load_session()['courses'][0]) == expected_values
    assert not window.current_schedule


@pytest.mark.parametrize('edit', ['unchanged', 'valid', 'invalid_unicode'])
def test_valid_excel_name_at_native_text_limit_remains_editable(
        restored_window, tmp_path, monkeypatch, edit):
    from openpyxl import Workbook
    window = restored_window
    workbook = Workbook()
    rooms = workbook.active
    rooms.title = 'Aulas'
    rooms.append(['# DE AULA', 'CAPACIDAD'])
    rooms.append(['R', 30])
    courses = workbook.create_sheet('Cursos')
    courses.append(['Curso', 'Nombre de Curso', 'Horas', 'Aula', 'Días'])
    # Excel's accepted code-point limit can exceed QLineEdit's UTF-16 limit.
    name = 'a' * 32766 + '🧬'
    courses.append(['BIO', name, '0800-0900', 'R', 'L'])
    path = tmp_path / 'literal.xlsx'
    workbook.save(path)
    imported = ExcelReader(path).load_validated()
    assert not imported.warnings
    assert imported.courses[0].name == name
    restore_course(window, imported.courses[0])
    before = encoded(window._capture_edit_state())
    history = encoded(vars(window._history))
    disk = (tmp_path / 'session.db').read_bytes()
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    dialog = CourseDialog(window, window.course_manager.courses[0])
    assert dialog.name_edit.text() == name
    assert dialog.name_edit.maxLength() == 32768
    if edit == 'valid':
        dialog.name_edit.setText('b' + name[1:])
    elif edit == 'invalid_unicode':
        dialog.name_edit.setText('b' + name[1:-1] + '\ud83e')
    if edit != 'valid':
        monkeypatch.setattr(window._repo, 'save_session', lambda **kwargs: pytest.fail('Must not save'))
    result = window.course_manager._replace_course(0, dialog.get_course())
    assert result is (edit != 'invalid_unicode')
    assert bool(warnings) is (edit == 'invalid_unicode')
    if edit == 'valid':
        assert window._repo.load_session()['courses'][0].name == 'b' + name[1:]
        assert not window.current_schedule
    else:
        assert encoded(window._capture_edit_state()) == before
        assert encoded(vars(window._history)) == history
        assert (tmp_path / 'session.db').read_bytes() == disk


def test_new_course_keeps_default_text_limits():
    dialog = CourseDialog()
    assert all(editor.maxLength() == 32767 for editor in (
        dialog.code_edit, dialog.name_edit, dialog.classroom_edit))
