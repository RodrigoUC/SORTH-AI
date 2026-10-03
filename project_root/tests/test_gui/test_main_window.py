import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt6.QtGui import QCloseEvent
from src.gui.main_window import MainWindow
from src.gui.scheduler_worker import SchedulerWorker
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    yield window
    window.close()


def load_inputs(window):
    window._classrooms = {'A1': Classroom('A1', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])


def test_busy_controls_and_repeat_generation_guard(window):
    load_inputs(window)
    window._set_busy(True)
    assert not window.btn_load.isEnabled()
    assert not window.course_manager.isEnabled()
    assert not window.btn_add_classroom.isEnabled()
    window._generate_schedule()
    assert window._worker is None
    window._set_busy(False)
    assert window.btn_generate.isEnabled()
    assert window.btn_load.isEnabled()


def test_input_edit_invalidates_export_and_saved_schedule(window):
    load_inputs(window)
    window.current_schedule = {'BIO-G1': ('A1', 1, 480, 540)}
    window.btn_export.setEnabled(True)
    window.course_manager.courses_changed.emit()
    assert window.current_schedule is None
    assert not window.btn_export.isEnabled()
    assert window._repo.load_session()['assignments'] is None


def test_failed_import_preserves_previous_inputs(window, monkeypatch):
    load_inputs(window)
    window.excel_path = 'previous.xlsx'
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a: ('missing.xlsx', ''))
    monkeypatch.setattr(QMessageBox, 'critical', lambda *a: None)
    window._load_excel()
    from tests.test_gui.import_helpers import wait_for_import
    wait_for_import(window)
    assert window.excel_path == 'previous.xlsx'
    assert window.course_manager.get_courses()[0].code == 'BIO'
    assert 'A1' in window._classrooms


def test_worker_snapshots_inputs_before_thread_start():
    course = Course('BIO', 1, 60, 'REGULAR')
    room = Classroom('A1', 30, 'REGULAR')
    restrictions = {'A1': {'BIO'}}
    worker = SchedulerWorker(None, [course], {'A1': room}, restrictions, 42)
    course.duration_min = 999
    room.capacity = 1
    restrictions['A1'].clear()
    assert worker._courses[0].duration_min == 60
    assert worker._classrooms['A1'].capacity == 30
    assert worker._restrictions['A1'] == {'BIO'}


def test_close_during_generation_does_not_destroy_worker(window):
    class RunningWorker:
        def isRunning(self):
            return True
    window._worker = RunningWorker()
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()
    window._worker = None


def test_deleted_group_is_persisted(window):
    load_inputs(window)
    window.current_schedule = {'BIO-G1': ('A1', 1, 480, 540)}
    window._on_group_removed('BIO-G1')
    assert not window.btn_export.isEnabled()
    assert window._repo.load_session()['assignments'] is None


def test_sorted_course_selection_keeps_identity(window):
    from PyQt6.QtCore import Qt
    window.course_manager.load_courses_from_excel([
        Course('ZOO', 1, 60, 'REGULAR'), Course('BIO', 2, 90, 'REGULAR')])
    table = window.course_manager.table
    table.sortItems(0, Qt.SortOrder.AscendingOrder)
    table.setCurrentCell(0, 0)
    assert table.item(0, 0).text() == 'BIO'
    assert window.course_manager._selected_course_index() == 1
    assert table.item(0, 2).text() == '2'


def test_sorted_schedule_edit_uses_stable_group_id(window):
    from PyQt6.QtCore import Qt
    from src.scheduling.time_model import TimeModel
    viewer = window.schedule_viewer
    viewer.display_schedule({'ZOO-G1': ('A1', 1, 480, 540), 'BIO-G1': ('A1', 1, 600, 660)}, TimeModel.default())
    viewer.list_table.sortItems(0, Qt.SortOrder.DescendingOrder)
    viewer.list_table.setCurrentCell(0, 0)
    edits = []
    viewer.edit_course_requested.disconnect()
    viewer.edit_course_requested.connect(edits.append)
    viewer._action_edit(viewer.list_table, viewer._gid_by_list_row)
    assert edits == ['ZOO']


def test_grid_includes_last_hour(window):
    from src.scheduling.time_model import TimeModel
    viewer = window.schedule_viewer
    viewer.display_schedule({'BIO-G1': ('A1', 1, 1260, 1320)}, TimeModel.default())
    viewer.tabs.setCurrentIndex(1)
    assert viewer.grid_table.rowCount() == 30
    assert viewer.grid_table.item(28, 1).text()


def test_actual_worker_completes_and_controls_recover(window, app):
    import time
    load_inputs(window)
    window._generate_schedule()
    assert window._busy
    deadline = time.monotonic() + 5
    while (window._busy or window._worker.isRunning()) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert window._worker.wait(1000)
    app.processEvents()
    assert not window._busy
    assert window.current_schedule
    assert window.btn_export.isEnabled()
    assert window.btn_load.isEnabled()
    assert not window._classrooms['A1'].occupancy


@pytest.mark.parametrize('cancel_at', ['file', 'warnings', 'invalid'])
def test_import_cancel_and_validation_preserve_complete_session(window, tmp_path, monkeypatch, cancel_at):
    import pandas as pd
    load_inputs(window)
    window.excel_path = 'previous.xlsx'
    window.classroom_restrictions = {'A1': {'BIO'}}
    window._classroom_course_map = {'A1': ['BIO']}
    window.current_schedule = {'BIO-G1': ('A1', 1, 480, 540)}
    window.btn_export.setEnabled(True)
    window._save_session()
    from pathlib import Path
    before = Path(window._repo._db_path).read_bytes()
    path = tmp_path / 'import.xlsx'
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'# DE AULA': ['NEW'], 'CAPACIDAD': [30]}).to_excel(writer, sheet_name='Aulas', index=False)
        pd.DataFrame({'Curso': ['NEW'], 'Horas': ['wrong' if cancel_at == 'invalid' else '0800-0900'], 'Aula': ['UNKNOWN']}).to_excel(writer, sheet_name='Cursos', index=False)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a: ('' if cancel_at == 'file' else str(path), ''))
    monkeypatch.setattr(QMessageBox, 'critical', lambda *a: None)
    monkeypatch.setattr(QMessageBox, 'exec', lambda *a: QMessageBox.StandardButton.Cancel)
    window._load_excel()
    from tests.test_gui.import_helpers import wait_for_import
    wait_for_import(window)
    assert window.excel_path == 'previous.xlsx'
    assert set(window._classrooms) == {'A1'}
    assert window.course_manager.get_courses()[0].code == 'BIO'
    assert window.classroom_restrictions == {'A1': {'BIO'}}
    assert window._classroom_course_map == {'A1': ['BIO']}
    assert window.current_schedule == {'BIO-G1': ('A1', 1, 480, 540)}
    assert window.btn_export.isEnabled()
    assert Path(window._repo._db_path).read_bytes() == before
    assert not window._loading


def test_successful_import_commits_all_inputs(window, tmp_path, monkeypatch):
    import pandas as pd
    load_inputs(window)
    path = tmp_path / 'input.xlsx'
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'# DE AULA': ['NEW'], 'CAPACIDAD': [30]}).to_excel(writer, sheet_name='Aulas', index=False)
        pd.DataFrame({'Curso': ['NEW'], 'Aula': ['NEW']}).to_excel(writer, sheet_name='Cursos', index=False)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a: (str(path), ''))
    window._load_excel()
    from tests.test_gui.import_helpers import wait_for_import
    wait_for_import(window)
    assert window.excel_path == str(path)
    assert set(window._classrooms) == {'NEW'}
    assert window.course_manager.get_courses()[0].code == 'NEW'
    assert window._classroom_course_map == {'NEW': ['NEW']}
    assert window.current_schedule is None
    assert window.btn_generate.isEnabled()
