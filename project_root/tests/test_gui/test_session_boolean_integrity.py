"""Restoration cannot turn corrupt flags into accepted autosave state."""
import sqlite3

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.mark.parametrize('field', ['force_split', 'lab_override', 'pinned'])
@pytest.mark.parametrize('value', ['false', 2, 0.5])
def test_corrupt_flag_locks_restore_and_prevents_unrelated_autosave(tmp_path, field, value):
    app = QApplication.instance() or QApplication([])
    path = tmp_path / 'session.db'
    repo = SessionRepository(str(path))
    repo.save_session(None, 42, {'R': Classroom('R', 40, 'REGULAR')},
        [Course('LAB', 1, 60, 'LAB', force_split=False),
         Course('LONG', 1, 300, 'REGULAR', force_split=False)], {},
        {'LAB-G1': ('R', 1, 480, 540)})
    with sqlite3.connect(path) as con:
        con.execute('PRAGMA ignore_check_constraints=ON')
        table = 'courses' if field == 'force_split' else 'assignments'
        con.execute(f'UPDATE {table} SET {field}=?', (value,))
    original = path.read_bytes()
    win = MainWindow(repo, restore_session=False,
        feature_settings=QSettings(str(tmp_path / 'features.ini'), QSettings.Format.IniFormat))
    try:
        win._restore_session_if_exists(confirm=False, show_status=False)
        assert win._restore_failed and win._busy
        assert field in str(win._save_error)
        assert not win.btn_load.isEnabled()
        assert win.current_schedule is None
        assert win.current_groups is None
        assert not win.course_manager.get_courses()
        win.seed_input.setValue(43)
        assert not win._save_session()
        assert not win._retry_session()
        assert path.read_bytes() == original
        assert not list(tmp_path.glob('*session-*.db'))
    finally:
        win._unsaved = False
        win.close()
