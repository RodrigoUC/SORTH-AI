"""Latest export outcome remains visible after a real atomic-write failure."""
from copy import deepcopy

import pytest
from PyQt6.QtCore import QSettings, QTimer, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QFileDialog, QPlainTextEdit

from src.gui.i18n import language_manager
from src.gui.main_window import MainWindow, _InfoDialog
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.time_model import TimeModel


@pytest.fixture
def window(tmp_path):
    settings = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')),
                        restore_session=False, feature_settings=settings)
    window._classrooms = {'Aula': Classroom('Aula', 30, 'REGULAR')}
    courses = [Course('BIO', 1, 60, 'REGULAR'), Course('QUI', 1, 60, 'REGULAR')]
    window.course_manager.load_courses_from_excel(courses)
    window.current_groups = [group for course in courses for group in course.generate_groups()]
    window.current_schedule = {'BIO-G1': ('Aula', 1, 480, 540), 'QUI-G1': ('Aula', 2, 480, 540)}
    window.schedule_viewer.display_schedule(window.current_schedule, TimeModel.default(), window.current_groups)
    window._save_session()
    window.resize(960, 640)
    window.show()
    QApplication.processEvents()
    yield window
    window.close()


def f6_status(window):
    observed = []
    def inspect():
        dialog = QApplication.activeModalWidget()
        observed.append(dialog.findChild(QPlainTextEdit).toPlainText())
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
    window.activateWindow()
    QApplication.processEvents()
    QTimer.singleShot(30, inspect)
    QTest.keyClick(window, Qt.Key.Key_F6)
    assert len(observed) == 1
    return observed[0]


@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('suffix', ['.xlsx', '.csv', '.pdf'])
@pytest.mark.parametrize('filtered', [False, True])
def test_real_export_collision_retains_latest_failure_then_next_success(
        window, tmp_path, monkeypatch, language, suffix, filtered):
    manager, old_language = language_manager(), language_manager().language
    modals = []
    original_exec = _InfoDialog.exec
    def inspect(dialog):
        # Exercise a real modal event loop and dismiss using the keyboard.
        modals.append((dialog.windowTitle(), window.status_bar.currentMessage()))
        QTimer.singleShot(30, lambda: QTest.keyClick(dialog, Qt.Key.Key_Escape))
        return original_exec(dialog)
    monkeypatch.setattr(_InfoDialog, 'exec', inspect)
    if filtered:
        window.schedule_viewer._list_search.setText('BIO')
    before_schedule = deepcopy(window.current_schedule)
    before_disk = (tmp_path / 'session.db').read_bytes()
    old_export = tmp_path / ('old-success' + suffix)
    destination = tmp_path / ('latest-failed & export' + suffix)
    destination.mkdir()
    marker = destination / 'preserved.txt'
    marker.write_text('synthetic existing destination')
    next_export = tmp_path / ('next-success' + suffix)
    paths = iter([str(old_export), str(destination), '', str(next_export)])
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (next(paths), ''))
    try:
        manager.set_language(language, persist=False)
        window._export_schedule(filtered=filtered)
        old_bytes = old_export.read_bytes()
        assert old_bytes and old_export.name in window.status_bar.currentMessage()
        assert not modals
        assert str(old_export) in f6_status(window)
        window._export_schedule(filtered=filtered)
        failure = window.status_bar.currentMessage()
        assert ('Could not export to' if language == 'en' else 'No se pudo exportar a') in failure
        assert destination.name in failure and old_export.name not in failure
        assert str(tmp_path) not in failure
        assert len(modals) == 1 and modals[0][0] == 'Error'
        assert modals[0][1] == failure
        snapshot = f6_status(window)
        assert destination.name in snapshot and old_export.name not in snapshot
        assert str(tmp_path) not in snapshot
        assert old_export.read_bytes() == old_bytes
        assert marker.read_text() == 'synthetic existing destination'
        assert not list(tmp_path.glob('.sorth-export-*'))
        assert window.current_schedule == before_schedule
        assert (tmp_path / 'session.db').read_bytes() == before_disk
        manager.set_language('en' if language == 'es' else 'es', persist=False)
        translated_failure = window.status_bar.currentMessage()
        assert destination.name in translated_failure and translated_failure != failure
        assert destination.name in f6_status(window)
        # Dismissing a new picker did not perform an export; retain its last outcome.
        window._export_schedule(filtered=filtered)
        assert window.status_bar.currentMessage() == translated_failure and len(modals) == 1
        window._export_schedule(filtered=filtered)
        assert next_export.is_file() and next_export.stat().st_size
        assert next_export.name in window.status_bar.currentMessage()
        assert destination.name not in window.status_bar.currentMessage()
        assert destination.name not in f6_status(window)
        assert str(next_export) in f6_status(window)
        assert len(modals) == 1
    finally:
        manager.set_language(old_language, persist=False)


def test_new_export_from_error_modal_keeps_its_newer_outcome(window, tmp_path, monkeypatch):
    destination = tmp_path / 'failed.xlsx'
    destination.mkdir()
    replacement = tmp_path / 'replacement.xlsx'
    paths = iter([str(destination), str(replacement)])
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (next(paths), ''))
    calls = []
    def inspect(dialog):
        calls.append(dialog.windowTitle())
        if dialog.windowTitle() == 'Error':
            window._export_schedule()
        return 0
    monkeypatch.setattr(_InfoDialog, 'exec', inspect)
    window._export_schedule()
    assert calls == ['Error']
    assert replacement.exists()
    assert replacement.name in window.status_bar.currentMessage()
    assert destination.name not in window.status_bar.currentMessage()
    assert str(replacement) in f6_status(window)
