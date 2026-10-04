"""Accepting unchanged room restrictions preserves the accepted result."""
from copy import deepcopy
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import QDialog

from src.application.edit_history import encoded
from src.gui.dialogs import ClassroomRestrictionsDialog
from src.gui.edit_view_state import EditViewState
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources


@pytest.fixture
def window(tmp_path):
    settings = QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)
    for key in ('undo_redo', 'pinned_sessions'):
        settings.setValue('features/' + key, True)
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')),
                        restore_session=False, feature_settings=settings)
    window._classrooms = {'R': Classroom('R', 30, 'REGULAR'),
                          'L': Classroom('L', 30, 'LAB')}
    window._classroom_course_map = {'R': ['A', 'B'], 'L': ['B']}
    window.course_manager.load_courses_from_excel([
        Course('A', 2, 60, 'REGULAR', size=20),
        Course('B', 1, 60, 'LAB', size=20),
    ])
    groups = [group for course in window.course_manager.courses
              for group in course.generate_groups()]
    groups[-1].lab_override = True
    window.resources = SchedulingResources((ResourceCatalog(
        'teacher', True, (Resource('shared', 'Synthetic alias'),),
        tuple((group.group_id, ('shared',)) for group in groups)),))
    window._on_schedule_done({group.group_id: ('R', day, 480, 540)
                              for day, group in enumerate(groups, 1)}, groups)
    yield window
    window._unsaved = False
    window.close()


def view_values(window):
    view = EditViewState.capture(window)
    return (view.course_query, view.schedule_query, view.filters, view.room, view.tabs,
            tuple((table.selected, table.current) for table in view.tables))


@pytest.mark.parametrize('restricted', [False, True])
@pytest.mark.parametrize('pinned', [False, True])
@pytest.mark.parametrize('history_enabled', [False, True])
def test_unchanged_restrictions_preserve_result_disk_and_redo(
        window, monkeypatch, restricted, pinned, history_enabled):
    # Deliberately use the reverse of the dialog's sorted classroom order.
    window.classroom_restrictions = {'R': {'B', 'A'}, 'L': {'B'}} if restricted else {}
    assert window._save_session()
    if pinned:
        window._toggle_pin('A-G1')
    if history_enabled:
        window._toggle_pin('A-G2')
        assert window._travel_history(True)
        assert window._history.can_redo
    else:
        window._features.save({**window._features.values(), 'undo_redo': False})
        window._apply_feature_preferences()
    manager, viewer = window.course_manager, window.schedule_viewer
    manager._search.setText('A')
    manager.table.sortItems(0, Qt.SortOrder.DescendingOrder)
    manager.table.selectRow(next(row for row in range(manager.table.rowCount())
                                if manager.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == 'A'))
    viewer._list_search.setText('A')
    viewer._room_filter.setCurrentIndex(viewer._room_filter.findData('R'))
    viewer._day_filter.setCurrentIndex(viewer._day_filter.findData(1))
    window.tabs.setCurrentIndex(1)
    viewer.tabs.setCurrentIndex(2)
    state = encoded(window._capture_edit_state())
    history = encoded(vars(window._history))
    disk = Path(window._repo._db_path).read_bytes()
    view = view_values(window)
    restrictions = deepcopy(window.classroom_restrictions)
    monkeypatch.setattr(ClassroomRestrictionsDialog, 'exec', lambda _: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(window._repo, 'save_session',
                        lambda **kwargs: pytest.fail('Unchanged restrictions must not save'))
    monkeypatch.setattr(window, '_confirm_pin_inputs',
                        lambda **kwargs: pytest.fail('Unchanged restrictions must not revalidate pins'))
    for _ in range(3):
        window._configure_restrictions()
        assert window.classroom_restrictions == restrictions
        assert encoded(window._capture_edit_state()) == state
        assert encoded(vars(window._history)) == history
        assert Path(window._repo._db_path).read_bytes() == disk
        assert view_values(window) == view


@pytest.mark.parametrize('clear_restrictions', [False, True])
def test_actual_restriction_change_still_invalidates_nonpinned_placements(
        window, monkeypatch, clear_restrictions):
    window.classroom_restrictions = {'R': {'A', 'B'}} if clear_restrictions else {}
    assert window._save_session()
    window._toggle_pin('A-G1')
    proposed = {} if clear_restrictions else {'R': {'A', 'B'}}
    monkeypatch.setattr(ClassroomRestrictionsDialog, 'exec', lambda _: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(ClassroomRestrictionsDialog, 'get_restrictions', lambda _: deepcopy(proposed))
    window._configure_restrictions()
    assert window.classroom_restrictions == proposed
    assert window.current_schedule == {'A-G1': ('R', 1, 480, 540)}
    assert window.pinned_group_ids == {'A-G1'}
    assert not any(group.lab_override for group in window.current_groups)
    assert window._repo.load_session()['assignments'] == window.current_schedule
    assert not window._history.can_undo and not window._history.can_redo


def test_unchecking_all_courses_is_a_real_change_not_an_empty_noop(window, monkeypatch):
    window.classroom_restrictions = {'R': {'A', 'B'}}
    assert window._save_session()
    def accept_without_courses(dialog):
        dialog.cls_list.setCurrentRow(next(row for row in range(dialog.cls_list.count())
                                          if dialog.cls_list.item(row).text() == 'R'))
        dialog._uncheck_all()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(ClassroomRestrictionsDialog, 'exec', accept_without_courses)
    window._configure_restrictions()
    assert window.classroom_restrictions == {}
    assert window.current_schedule is None
    assert window._repo.load_session()['assignments'] is None
