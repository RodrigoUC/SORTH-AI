from copy import deepcopy
import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox, QDialog
from src.gui.main_window import MainWindow
from src.gui.manual_assignment_dialog import ManualAssignmentDialog
from src.application.edit_history import fingerprint
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def window(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path/'settings.ini'), QSettings.Format.IniFormat)
    for key in ('undo_redo', 'pinned_sessions'):
        settings.setValue('features/'+key, True)
    w = MainWindow(SessionRepository(str(tmp_path/'session.db')), restore_session=False, feature_settings=settings)
    w._classrooms = {'R': Classroom('R', 30, 'REGULAR')}
    w.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR', size=20)])
    w._on_schedule_done({'BIO-G1': ('R', 1, 480, 540)}, w.course_manager.courses[0].generate_groups())
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: QMessageBox.StandardButton.Cancel)
    yield w
    w._unsaved = False
    w.close()


def test_edit_delete_undo_redo_pin_and_metadata(window):
    original = fingerprint(window._capture_edit_state())
    course = deepcopy(window.course_manager.courses[0])
    course.name = 'Edited'
    window.course_manager._replace_course(0, course)
    edited = fingerprint(window._capture_edit_state())
    assert edited != original
    assert window._commit_course_edit([], 'delete')
    assert not window.course_manager.courses
    assert window._travel_history(True)
    assert fingerprint(window._capture_edit_state()) == edited
    assert window._travel_history(True)
    assert fingerprint(window._capture_edit_state()) == original
    assert window._travel_history(False)
    assert window._travel_history(True)
    window._toggle_pin('BIO-G1')
    pinned = fingerprint(window._capture_edit_state())
    assert window.pinned_group_ids == {'BIO-G1'}
    assert window._travel_history(True)
    assert fingerprint(window._capture_edit_state()) == original
    assert window._travel_history(False)
    assert fingerprint(window._capture_edit_state()) == pinned


def test_save_error_after_unpin_confirmation_is_atomic(window, monkeypatch):
    window._toggle_pin('BIO-G1')
    before = fingerprint(window._capture_edit_state())
    before_db = window._repo.load_session()
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: QMessageBox.StandardButton.Yes)
    def fail(**kwargs):
        raise OSError('full')
    monkeypatch.setattr(window._repo, 'save_session', fail)
    assert not window._commit_course_edit([], 'delete')
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == fingerprint(before_db)
    assert window._history.can_undo
    assert not window._travel_history(True)
    assert fingerprint(window._capture_edit_state()) == before
    assert window._history.can_undo


def test_hiding_preserves_history_external_edits_invalidate(window):
    window._toggle_pin('BIO-G1')
    before = fingerprint(window._capture_edit_state())
    values = window._features.values()
    values['undo_redo'] = False
    window._features.save(values)
    window._apply_feature_preferences()
    assert window.btn_undo.isHidden() and not window._undo_action.isEnabled()
    assert not window._travel_history(True)
    assert window._history.can_undo
    assert fingerprint(window._capture_edit_state()) == before
    values['undo_redo'] = True
    window._features.save(values)
    window._apply_feature_preferences()
    assert window._travel_history(True)
    window.seed_input.setValue(21)
    window._save_session()
    assert not window._history.can_redo


def test_manual_failure_cancel_and_undo_lab_exception(window, monkeypatch):
    course = deepcopy(window.course_manager.courses[0])
    course.required_room_type = 'LAB'
    assert window._commit_course_edit([course], 'edit')
    window._on_schedule_done({}, course.generate_groups())
    before = fingerprint(window._capture_edit_state())
    monkeypatch.setattr(ManualAssignmentDialog, 'exec', lambda d: QDialog.DialogCode.Rejected)
    window._manual_assignment('BIO-G1')
    assert fingerprint(window._capture_edit_state()) == before
    def accept(d):
        d.result_assignment = ('R', 1, 480, 540)
        d.lab_override = True
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(ManualAssignmentDialog, 'exec', accept)
    window._manual_assignment('BIO-G1')
    assert window.current_groups[0].lab_override
    assert window._travel_history(True)
    assert fingerprint(window._capture_edit_state()) == before
    assert window._travel_history(False)
    assert window._repo.load_session()['lab_overrides'] == {'BIO-G1'}


def test_viewer_remove_failure_and_restore_reset(window, monkeypatch):
    before = fingerprint(window._capture_edit_state())
    with monkeypatch.context() as patch:
        patch.setattr(window._repo, 'save_session', lambda **kw: (_ for _ in ()).throw(OSError('full')))
        window.schedule_viewer._remove_group('BIO-G1')
    assert fingerprint(window._capture_edit_state()) == before
    assert window.schedule_viewer._assignments == window.current_schedule
    window._on_group_removed('BIO-G1')
    assert window._history.can_undo
    window._restore_session_if_exists(confirm=False, show_status=False)
    assert not window._history.can_undo
    assert window._history.reset_reason == 'restore'


def test_keyboard_undo_redo_and_busy_availability(window):
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication
    before = fingerprint(window._capture_edit_state())
    window._commit_course_edit([], 'delete')
    window.show()
    window.activateWindow()
    window.course_manager.table.setFocus()
    QApplication.processEvents()
    QTest.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert fingerprint(window._capture_edit_state()) == before
    QTest.keyClick(window, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    assert not window.course_manager.courses
    window._set_busy(True)
    assert not window._undo_action.isEnabled() and not window.btn_undo.isEnabled()
    assert not window._travel_history(True)
    window._set_busy(False)
    assert window._undo_action.isEnabled()


def test_render_failure_rolls_back_database_model_history_and_references(window, monkeypatch):
    before = fingerprint(window._capture_edit_state())
    before_db = fingerprint(window._repo.load_session())
    courses, groups, schedule = window.course_manager.courses, window.current_groups, window.current_schedule
    original = window.course_manager._refresh_table
    calls = []
    def fail_once():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError('injected renderer failure')
        return original()
    monkeypatch.setattr(window.course_manager, '_refresh_table', fail_once)
    assert not window._commit_course_edit([], 'delete')
    assert len(calls) == 2
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == before_db
    assert window.course_manager.courses is courses
    assert window.current_groups is groups and window.current_schedule is schedule
    assert not window._history.can_undo and not window._restore_failed


def test_database_commit_failure_after_materialization_restores_accepted_state(window, monkeypatch):
    from contextlib import contextmanager
    before = fingerprint(window._capture_edit_state())
    before_db = fingerprint(window._repo.load_session())
    original = window._repo._connect
    @contextmanager
    def fail_commit():
        with original() as con:
            yield con
            raise OSError('injected commit failure')
    with monkeypatch.context() as patch:
        patch.setattr(window._repo, '_connect', fail_commit)
        assert not window._commit_course_edit([], 'delete')
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == before_db
    assert not window._history.can_undo and not window._restore_failed


def test_permanent_renderer_failure_preserves_data_and_locks_recovery(window, monkeypatch):
    before = fingerprint(window._capture_edit_state())
    before_db = fingerprint(window._repo.load_session())
    monkeypatch.setattr(window, '_display_edit_state', lambda _: (_ for _ in ()).throw(RuntimeError('renderer unavailable')))
    assert not window._commit_course_edit([], 'delete')
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == before_db
    assert window._restore_failed and window._busy
    assert not window._history.can_undo


def test_undo_render_failure_does_not_consume_command(window, monkeypatch):
    assert window._commit_course_edit([], 'delete')
    before = fingerprint(window._capture_edit_state())
    original = window._display_edit_state
    calls = []
    def fail_once(state):
        calls.append(1)
        original(state)
        if len(calls) == 1:
            raise RuntimeError('injected post-render failure')
    monkeypatch.setattr(window, '_display_edit_state', fail_once)
    assert not window._travel_history(True)
    assert fingerprint(window._capture_edit_state()) == before
    assert window._history.can_undo and not window._history.can_redo


def test_postcommit_presentation_failure_is_saved_and_locked_not_rolled_back(window, monkeypatch):
    monkeypatch.setattr(window, '_edit_status', lambda _: (_ for _ in ()).throw(RuntimeError('status failed')))
    assert window._commit_course_edit([], 'delete')
    assert window._repo.load_session()['courses'] == []
    assert window.course_manager.courses == []
    assert window._history.can_undo
    assert window._restore_failed and window._busy
    assert 'se guardó' in window.status_bar.currentMessage()


def test_no_duplicate_save_state_setter_after_commit(window, monkeypatch):
    original = window._update_save_state
    calls = []
    def second_fails():
        calls.append(True)
        if len(calls) == 2:
            raise RuntimeError('redundant postcommit renderer')
        original()
    monkeypatch.setattr(window, '_update_save_state', second_fails)
    assert window._commit_course_edit([], 'delete')
    assert calls == [True]
    assert window._repo.load_session()['courses'] == []


def test_full_view_filters_focus_selection_preserved_on_pin_and_failed_undo(window, monkeypatch):
    from src.gui.edit_view_state import EditViewState
    from PyQt6.QtWidgets import QApplication
    viewer = window.schedule_viewer
    window.show()
    window.tabs.setCurrentIndex(1)
    viewer.tabs.setCurrentIndex(2)
    viewer._list_search.setText('BIO')
    viewer._status_filter.setCurrentIndex(viewer._status_filter.findData('assigned'))
    viewer._day_filter.setCurrentIndex(viewer._day_filter.findData(1))
    viewer.classroom_selector.setCurrentText('R')
    viewer.classroom_table.setCurrentCell(0, 2)
    viewer._list_search.setFocus()
    QApplication.processEvents()
    before = EditViewState.capture(window)
    window._toggle_pin('BIO-G1')
    after = EditViewState.capture(window)
    for field in ('course_query', 'schedule_query', 'filters', 'room', 'tabs'):
        assert getattr(after, field) == getattr(before, field)
    assert after.tables[2].current == before.tables[2].current
    assert after.tables[2].selected == before.tables[2].selected
    original = viewer.display_schedule
    calls = []
    def fail_once(*args, **kwargs):
        original(*args, **kwargs)
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError('view failed after clear')
    monkeypatch.setattr(viewer, 'display_schedule', fail_once)
    assert not window._travel_history(True)
    restored = EditViewState.capture(window)
    for field in ('course_query', 'schedule_query', 'filters', 'room', 'tabs'):
        assert getattr(restored, field) == getattr(before, field)
    assert restored.tables[2].selected == before.tables[2].selected


def test_persistent_feedback_failure_preserves_old_state_and_disables_editing(window, monkeypatch):
    before = fingerprint(window._capture_edit_state())
    before_db = fingerprint(window._repo.load_session())
    monkeypatch.setattr(window, '_update_save_state', lambda: (_ for _ in ()).throw(RuntimeError('persistent label failure')))
    assert not window._commit_course_edit([], 'delete')
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == before_db
    assert window._restore_failed and window._busy
    assert not window.course_manager.isEnabled()
    assert not window.schedule_viewer.isEnabled()
    assert 'se conservaron' in window.status_bar.currentMessage()


def test_last_assignment_removal_retains_empty_room_filter(window):
    viewer = window.schedule_viewer
    viewer._room_filter.setCurrentIndex(viewer._room_filter.findData('R'))
    viewer.classroom_selector.setCurrentText('R')
    window._on_group_removed('BIO-G1')
    assert viewer._room_filter.currentData() == 'R'
    assert viewer.classroom_selector.currentText() == 'R'
    assert not window.current_schedule
