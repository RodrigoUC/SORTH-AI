import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from copy import deepcopy

import pytest
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog

from src.gui.main_window import MainWindow
from src.infrastructure.excel_reader import ExcelReader, ExcelImport, notice
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom
from src.scheduling.time_model import TimeModel


@pytest.fixture
def window(tmp_path):
    app = QApplication.instance() or QApplication([])
    win = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    win._classrooms = {'R': Classroom('R', 30, 'REGULAR')}
    win._classroom_course_map = {'R': {'BIO'}}
    win.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])
    win.classroom_restrictions = {'R': {'BIO'}}
    win.excel_path = 'previous.xlsx'
    win.current_groups = win.course_manager.get_courses()[0].generate_groups()
    win.current_schedule = {'BIO-G1': ('R', 1, 480, 540)}
    win.current_groups[0].assignment = win.current_schedule['BIO-G1']
    win.current_groups[0].lab_override = True
    win.schedule_viewer.display_schedule(win.current_schedule, TimeModel.default(), win.current_groups)
    win._update_export_actions()
    win._save_session()
    yield win
    win._unsaved = False
    win.close()


def snapshot(win):
    return deepcopy((win.excel_path, {k: vars(v) for k, v in win._classrooms.items()},
                     [vars(c) for c in win.course_manager.get_courses()],
                     win.classroom_restrictions, win._classroom_course_map,
                     win.current_schedule, [vars(g) for g in win.current_groups],
                     win.btn_export.isEnabled(), win._unsaved, win._save_error))


@pytest.mark.parametrize('mode', ['file_cancel', 'warning_cancel', 'malformed'])
def test_import_cancel_or_failure_preserves_complete_state_and_disk(window, tmp_path, monkeypatch, mode):
    path = tmp_path / 'bad.xlsx'
    path.write_bytes(b'not an Excel workbook')
    before = snapshot(window)
    disk = open(window._repo._db_path, 'rb').read()
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a: ('' if mode == 'file_cancel' else str(path), ''))
    monkeypatch.setattr(QMessageBox, 'critical', lambda *a: None)
    if mode == 'warning_cancel':
        monkeypatch.setattr(ExcelReader, 'load_validated', lambda self: ExcelImport({}, [], {}, [notice('warning')]))
        monkeypatch.setattr(QMessageBox, 'exec', lambda self: QMessageBox.StandardButton.Cancel)
    window._load_excel()
    assert snapshot(window) == before
    assert open(window._repo._db_path, 'rb').read() == disk


def test_classroom_only_session_is_offered_for_restore(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    repo = SessionRepository(str(tmp_path / 'session.db'))
    repo.save_session(None, 9, {'R': Classroom('R', 30, 'REGULAR')}, [], {}, None)
    monkeypatch.setattr(QDialog, 'exec', lambda self: QDialog.DialogCode.Accepted)
    win = MainWindow(repo)
    assert 'R' in win._classrooms
    assert win.seed_input.value() == 9
    win.close()
    assert 'R' in repo.load_session()['classrooms']
