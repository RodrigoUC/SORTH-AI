import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sqlite3

import pytest
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    win = MainWindow(SessionRepository(str(tmp_path / "session.db")), restore_session=False)
    yield win
    win._unsaved = False
    win.close()


def fail(*args, **kwargs):
    raise sqlite3.OperationalError("database or disk is full")


def test_failed_save_retains_state_after_other_status_messages(window, monkeypatch):
    monkeypatch.setattr(window._repo, "save_session", fail)
    assert not window._save_session()
    window.status_bar.showMessage("Another successful action")
    assert window._unsaved
    assert window._save_state_label.text() == "Cambios sin guardar"
    assert "disk is full" in window._save_state_label.toolTip()
    assert not window._retry_save_button.isHidden()


@pytest.mark.parametrize("choice, accepted", [(QMessageBox.StandardButton.Cancel, False),
                                                (QMessageBox.StandardButton.Discard, True)])
def test_failed_save_close_requires_explicit_choice(window, monkeypatch, choice, accepted):
    monkeypatch.setattr(window._repo, "save_session", fail)
    window._save_session()
    calls = []
    def prompt(*args):
        calls.append(args)
        return choice
    monkeypatch.setattr(QMessageBox, "warning", prompt)
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted() is accepted
    assert calls[0][-1] == QMessageBox.StandardButton.Cancel
    assert window._unsaved


def test_close_retry_succeeds_without_losing_pending_changes(window, monkeypatch):
    real_save = window._repo.save_session
    window.course_manager.load_courses_from_excel([Course("NEW", 1, 60, "REGULAR")])
    monkeypatch.setattr(window._repo, "save_session", fail)
    window._save_session()
    def prompt(*args):
        monkeypatch.setattr(window._repo, "save_session", real_save)
        return QMessageBox.StandardButton.Retry
    monkeypatch.setattr(QMessageBox, "warning", prompt)
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    assert not window._unsaved
    assert window._save_error is None
    assert window._repo.load_session()["courses"][0].code == "NEW"


def test_retry_button_clears_failure_only_after_success(window, monkeypatch):
    real_save = window._repo.save_session
    monkeypatch.setattr(window._repo, "save_session", fail)
    window._save_session()
    assert not window._retry_session()
    assert window._save_error
    monkeypatch.setattr(window._repo, "save_session", real_save)
    assert window._retry_session()
    assert not window._unsaved
    assert window._retry_save_button.isHidden()


def test_declined_restore_unchanged_close_preserves_database(app, tmp_path, monkeypatch):
    path = tmp_path / "session.db"
    repo = SessionRepository(str(path))
    repo.save_session(None, 5, {}, [Course("OLD", 1, 60, "REGULAR")], {}, None)
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    win = MainWindow(repo)
    win.close()
    assert repo.load_session()["courses"][0].code == "OLD"
    assert not list(tmp_path.glob("previous-session-*"))


def test_new_edits_after_declining_restore_keep_backup(app, tmp_path, monkeypatch):
    repo = SessionRepository(str(tmp_path / "session.db"))
    repo.save_session(None, 5, {}, [Course("OLD", 1, 60, "REGULAR")], {}, None)
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    win = MainWindow(repo)
    win.course_manager.load_courses_from_excel([Course("NEW", 1, 60, "REGULAR")])
    assert win._save_session()
    backups = list(tmp_path.glob("previous-session-*"))
    assert len(backups) == 1
    assert SessionRepository(str(backups[0])).load_session()["courses"][0].code == "OLD"
    assert repo.load_session()["courses"][0].code == "NEW"
    win.close()


def test_corrupt_startup_shows_error_and_never_writes(app, tmp_path, monkeypatch):
    path = tmp_path / "bad.db"
    path.write_bytes(b"unreadable session")
    monkeypatch.setattr(SessionRepository, "default_path", staticmethod(lambda: path))
    win = MainWindow()
    assert win._restore_failed
    assert not win.btn_load.isEnabled()
    assert win._save_state_label.text() == "Sesión no disponible"
    assert not win._retry_session()
    assert path.read_bytes() == b"unreadable session"
    win.close()


def test_failed_load_blocks_save_until_readable(window, monkeypatch):
    real_load = window._repo.load_session
    monkeypatch.setattr(window._repo, "has_session", lambda: True)
    monkeypatch.setattr(window._repo, "load_session", fail)
    window._restore_session_if_exists()
    assert window._restore_failed
    assert not window._save_session()
    assert window._repo.load_session == fail
    monkeypatch.setattr(window._repo, "load_session", real_load)
    monkeypatch.setattr(window._repo, "has_session", lambda: False)
    assert window._retry_session()
    assert not window._restore_failed
    assert window.btn_load.isEnabled()
