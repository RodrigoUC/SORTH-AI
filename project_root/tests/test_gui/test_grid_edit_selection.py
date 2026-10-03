"""Grid edit/history restoration must follow blocks, never row coordinates."""
import pytest
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.gui.edit_view_state import EditViewState
from src.gui.main_window import MainWindow
from src.gui.schedule_grid_delegate import GRID_BLOCK_ROLE
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: QMessageBox.StandardButton.Cancel)
    settings = QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)
    w = MainWindow(SessionRepository(str(tmp_path / 'session.db')),
                   restore_session=False, feature_settings=settings)
    flags = w._features.values()
    flags['undo_redo'] = True
    w._features.save(flags)
    w._apply_feature_preferences()
    w._classrooms = {'R': Classroom('R', 30, 'REGULAR'),
                     'S': Classroom('S', 30, 'REGULAR')}
    courses = [Course(code, 1, duration, 'REGULAR', size=20)
               for code, duration in [('A', 10), ('B', 30), ('C', 30)]]
    w.course_manager.load_courses_from_excel(courses)
    w._on_schedule_done({'A-G1': ('R', 1, 490, 500),
                         'B-G1': ('R', 1, 540, 570),
                         'C-G1': ('R', 1, 600, 630)},
                        [group for course in courses for group in course.generate_groups()])
    w.tabs.setCurrentIndex(1)
    w.schedule_viewer.tabs.setCurrentIndex(1)
    yield w
    w._unsaved = False
    w.close()


def select(viewer, gids):
    table = viewer.grid_table
    for row in range(table.rowCount()):
        for col in range(1, table.columnCount()):
            item = table.item(row, col)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == gids:
                table.setCurrentItem(item)
                return item.data(GRID_BLOCK_ROLE)
    pytest.fail(f'Missing grid block {gids}')


def assert_empty(viewer):
    assert viewer.grid_table.currentItem() is None
    assert not viewer.grid_table.selectedItems()
    assert viewer._selected_grid_gids() == ()
    assert not viewer._btn_grid_details.isEnabled()
    viewer._show_grid_details()
    assert viewer._grid_details_dialog is None


def test_redo_preserves_session_through_off_half_hour_row_shift_and_details(window):
    v = window.schedule_viewer
    v.tabs.setCurrentIndex(0)
    v._remove_group('A-G1')
    v.tabs.setCurrentIndex(1)
    assert window._travel_history(True)
    identity = select(v, ('B-G1',))
    original_row = v.grid_table.currentRow()
    for _ in range(2):
        assert window._travel_history(False)
        assert v.grid_table.currentRow() != original_row
        assert v._selected_grid_gids() == ('B-G1',)
        assert v.grid_table.currentItem().data(GRID_BLOCK_ROLE) == identity
        assert window._repo.load_session()['assignments'] == {
            'B-G1': ('R', 1, 540, 570), 'C-G1': ('R', 1, 600, 630)}
        assert window._travel_history(True)
        assert v._selected_grid_gids() == ('B-G1',)
    assert window._travel_history(False)
    v._show_grid_details()
    dialog = v._grid_details_dialog
    assert dialog.session_selector.currentData() == 'B-G1'
    dialog._view_in_list()
    assert v._selected_gid(v.list_table) == 'B-G1'


def test_removing_selected_session_clears_without_selecting_replacement(window):
    v = window.schedule_viewer
    select(v, ('B-G1',))
    window._on_group_removed('B-G1')
    assert_empty(v)
    assert window._travel_history(True)
    assert_empty(v)
    select(v, ('B-G1',))
    assert window._travel_history(False)
    assert_empty(v)


@pytest.mark.parametrize('filter_kind', ['search', 'day', 'room', 'status'])
def test_history_restores_filters_and_selected_block(window, filter_kind):
    v = window.schedule_viewer
    if filter_kind == 'search':
        v._list_search.setText('B')
    else:
        control, value = {'day': (v._day_filter, 1), 'room': (v._room_filter, 'R'),
                          'status': (v._status_filter, 'assigned')}[filter_kind]
        control.setCurrentIndex(control.findData(value))
    select(v, ('B-G1',))
    before = EditViewState.capture(window)
    window._on_group_removed('A-G1')
    for undo in [True, False]:
        assert window._travel_history(undo)
        after = EditViewState.capture(window)
        assert after.filters == before.filters
        assert after.schedule_query == before.schedule_query
        assert v._selected_grid_gids() == ('B-G1',)


def test_changed_conflict_segment_clears_even_when_selected_session_survives(window):
    v = window.schedule_viewer
    assignments = dict(window.current_schedule, **{'A-G1': ('R', 1, 550, 560)})
    # Conflict rendering is supported for consultation; history correctly rejects
    # conflicting domain schedules, so exercise its presentation snapshot directly.
    def display(values):
        v.display_schedule(values, v._time_model, window.current_groups,
                           classrooms=window._classrooms)

    display(assignments)
    for gids in [('B-G1',), ('B-G1', 'A-G1')]:
        display(assignments)
        select(v, gids)
        snapshot = EditViewState.capture(window)
        display({key: value for key, value in assignments.items() if key != 'A-G1'})
        snapshot.restore(window)
        assert_empty(v)


def test_scroll_focus_and_no_selection_survive_history(window):
    v = window.schedule_viewer
    window.show()
    window.activateWindow()
    select(v, ('B-G1',))
    v.grid_table.setFocus()
    QApplication.processEvents()
    v.grid_table.verticalScrollBar().setValue(2)
    vertical = v.grid_table.verticalScrollBar().value()
    horizontal = v.grid_table.horizontalScrollBar().value()
    window._on_group_removed('A-G1')
    assert v._selected_grid_gids() == ('B-G1',)
    assert v.grid_table.verticalScrollBar().value() == vertical
    assert v.grid_table.horizontalScrollBar().value() == horizontal
    assert QApplication.focusWidget() is v.grid_table
    v.grid_table.clearSelection()
    v.grid_table.setCurrentItem(None)
    assert window._travel_history(True)
    assert_empty(v)


@pytest.mark.parametrize('change', ['room', 'filter', 'unselected'])
def test_grid_snapshot_never_falls_back_to_coordinates(window, change):
    v = window.schedule_viewer
    select(v, ('B-G1',))
    if change == 'unselected':
        v.grid_table.clearSelection()  # A native current cell is not a selection.
    snapshot = EditViewState.capture(window)
    if change == 'room':
        assignments = {gid: ('S', *value[1:]) for gid, value in window.current_schedule.items()}
        v.display_schedule(assignments, v._time_model, window.current_groups,
                           classrooms=window._classrooms)
        v.classroom_selector.setCurrentText('S')
    elif change == 'filter':
        v._list_search.setText('C')
    # Isolate the grid snapshot: EditViewState normally restores the saved room
    # and filters first. A mismatched grid must still never match another room.
    snapshot.grid.restore(v)
    assert_empty(v)
