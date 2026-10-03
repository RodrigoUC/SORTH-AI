import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from copy import deepcopy
import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox, QPushButton
from PyQt6.QtCore import Qt, QSettings
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.time_model import TimeModel


@pytest.fixture
def window(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / 'features.ini'), QSettings.Format.IniFormat)
    settings.setValue('features/pinned_sessions', True)
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False, feature_settings=settings)
    window._classrooms = {'R': Classroom('R', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('BIO', 2, 60, 'REGULAR')])
    groups = window.course_manager.get_courses()[0].generate_groups()
    assignments = {'BIO-G1': ('R', 1, 480, 540), 'BIO-G2': ('R', 2, 480, 540)}
    for g in groups:
        g.assignment = assignments[g.group_id]
    window._on_schedule_done(assignments, groups)
    yield window
    window.close()
    app.processEvents()


def test_explicit_pin_native_controls_retain_selected_identity(window):
    viewer = window.schedule_viewer
    assert not window.pinned_group_ids
    viewer.list_table.sortItems(0, Qt.SortOrder.DescendingOrder)
    viewer.list_table.setCurrentCell(0, 0)
    gid = viewer._selected_gid(viewer.list_table)
    pins = [b for b in viewer.findChildren(QPushButton) if b.text() == 'Fijar sesión' and b.isEnabled()]
    assert len(pins) == 1
    pins[0].click()
    assert window.pinned_group_ids == {gid}
    assert 'Fijada' in viewer.list_table.item(viewer.list_table.currentRow(), 7).text()
    assert viewer._selected_gid(viewer.list_table) == gid
    assert window._repo.load_session()['pinned_group_ids'] == {gid}
    pins[0].click()
    assert not window.pinned_group_ids
    assert 'Fijada' not in viewer.list_table.item(viewer.list_table.currentRow(), 7).text()


@pytest.mark.parametrize('kind', ['duration', 'removed_course', 'removed_room', 'restriction', 'capacity', 'split'])
def test_invalid_input_change_cancel_retains_everything(window, monkeypatch, kind):
    window._toggle_pin('BIO-G1')
    before = deepcopy(window.current_schedule)
    before_courses = window.course_manager.get_courses()
    captured = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: captured.append(args[2]) or QMessageBox.StandardButton.Cancel)
    kwargs = {
        'duration': {'courses': [Course('BIO', 2, 120, 'REGULAR')]},
        'removed_course': {'courses': []},
        'removed_room': {'classrooms': {}},
        'restriction': {'restrictions': {'R': {'OTHER'}}},
        'capacity': {'courses': [Course('BIO', 2, 60, 'REGULAR', size=99)]},
        'split': {'courses': [Course('BIO', 2, 360, 'REGULAR')]},
    }[kind]
    assert not window._confirm_pin_inputs(**kwargs)
    assert captured and 'BIO-G1' in captured[0]
    assert window.current_schedule == before
    assert window.pinned_group_ids == {'BIO-G1'}
    assert window.course_manager.get_courses() == before_courses
    assert window._repo.load_session()['pinned_group_ids'] == {'BIO-G1'}


def test_course_gate_cancel_and_confirm_before_mutation(window, monkeypatch):
    window._toggle_pin('BIO-G1')
    previous = window.course_manager.get_courses()[0]
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: QMessageBox.StandardButton.Cancel)
    window.course_manager._replace_course(0, Course('BIO', 2, 120, 'REGULAR'))
    assert window.course_manager.get_courses()[0] is previous
    assert window.current_schedule and window.pinned_group_ids
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: QMessageBox.StandardButton.Yes)
    window.course_manager._replace_course(0, Course('BIO', 2, 120, 'REGULAR'))
    assert not window.pinned_group_ids
    assert window.current_schedule is None
    assert window.course_manager.get_courses()[0].duration_min == 120


def test_valid_edit_preserves_only_pinned_assignments(window):
    window._toggle_pin('BIO-G1')
    window.course_manager._replace_course(0, Course('BIO', 3, 60, 'REGULAR', name='Renamed'))
    assert window.current_schedule == {'BIO-G1': ('R', 1, 480, 540)}
    assert len(window.current_groups) == 3
    assert len([g for g in window.current_groups if g.is_assigned()]) == 1
    assert window._repo.load_session()['pinned_group_ids'] == {'BIO-G1'}


def test_failed_generation_preserves_pins_and_last_schedule(window, monkeypatch):
    window._toggle_pin('BIO-G1')
    before = deepcopy(window.current_schedule)
    errors = []
    monkeypatch.setattr(window, '_on_schedule_error', errors.append)
    result = {**before, 'BIO-G1': ('R', 4, 480, 540)}
    window._on_schedule_done(result, window.current_groups)
    assert errors
    assert window.current_schedule == before
    assert window.pinned_group_ids == {'BIO-G1'}


def test_restoration_pins_and_lab_exception(window, monkeypatch):
    from src.gui.i18n_widgets import QDialog
    window._toggle_pin('BIO-G1')
    monkeypatch.setattr(QDialog, 'exec', lambda *a: QDialog.DialogCode.Accepted)
    other = MainWindow(window._repo)
    assert other.pinned_group_ids == {'BIO-G1'}
    assert other.current_groups[0].pinned
    assert other.current_schedule == window.current_schedule
    other.close()


def test_cancel_generation_ignores_late_success(window):
    window._toggle_pin('BIO-G1')
    before = deepcopy(window.current_schedule)
    class Worker:
        interrupted = False
        def requestInterruption(self):
            self.interrupted = True
        def isRunning(self):
            return False
    worker = Worker()
    window._worker = worker
    window._set_busy(True)
    window._cancel_generation()
    assert worker.interrupted
    window._on_schedule_done({}, [])
    window._set_busy(False)
    assert window.current_schedule == before
    assert window.pinned_group_ids == {'BIO-G1'}
    assert window._repo.load_session()['assignments'] == before


def test_replacing_excel_with_missing_room_cancel_is_atomic(window, monkeypatch):
    from types import SimpleNamespace
    from PyQt6.QtWidgets import QFileDialog
    from src.gui import main_window
    window._toggle_pin('BIO-G1')
    before = deepcopy(window.current_schedule)
    imported = SimpleNamespace(classrooms={'NEW': Classroom('NEW',30,'REGULAR')},
        courses=[Course('BIO',2,60,'REGULAR')], classroom_course_map={}, warnings=[])
    class Reader:
        def __init__(self, *a): pass
        def load_validated(self): return imported
    from src.gui import import_worker
    from src.infrastructure.import_candidate import ImportCandidate
    monkeypatch.setattr(import_worker, 'read_candidate', lambda path, cancelled, previous: previous or ImportCandidate(path, b'x', imported))
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a:('new.xlsx',''))
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:QMessageBox.StandardButton.Cancel)
    window._load_excel()
    from tests.test_gui.import_helpers import wait_for_import
    wait_for_import(window)
    assert window.excel_path is None
    assert set(window._classrooms) == {'R'}
    assert window.current_schedule == before
    assert window.pinned_group_ids == {'BIO-G1'}


def test_worker_snapshots_pins_and_overrides():
    from src.gui.scheduler_worker import SchedulerWorker
    pins = {'BIO-G1': ('R',1,480,540)}
    overrides = {'BIO-G1'}
    worker = SchedulerWorker(None,[Course('BIO',1,60,'LAB')],
        {'R':Classroom('R',30,'REGULAR')},{},42,pins,overrides)
    pins.clear();overrides.clear()
    assert worker._pinned_assignments == {'BIO-G1':('R',1,480,540)}
    assert worker._lab_overrides == {'BIO-G1'}


def test_real_worker_regenerates_with_confirmed_pinned_lab_exception(window):
    import time
    course = Course('BIO', 2, 60, 'LAB')
    window.course_manager.load_courses_from_excel([course])
    groups = course.generate_groups()
    groups[0].assignment = ('R',1,480,540)
    groups[0].lab_override = True
    window._on_schedule_done({'BIO-G1':groups[0].assignment},groups)
    window._toggle_pin('BIO-G1')
    window._generate_schedule()
    app = QApplication.instance()
    deadline = time.monotonic() + 5
    while window._busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.005)
    assert window._worker is None or window._worker.wait(1000)
    app.processEvents()
    assert not window._busy
    assert window.current_schedule == {'BIO-G1':('R',1,480,540)}
    assert window.pinned_group_ids == {'BIO-G1'}
    assert window.current_groups[0].lab_override
    assert not window.current_groups[1].is_assigned()
