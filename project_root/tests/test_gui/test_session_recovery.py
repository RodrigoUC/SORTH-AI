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
    assert not window._retry_session()
    assert window._restore_failed and not window.btn_load.isEnabled()
    window._repo.save_session(None, 5, {}, [], {}, None)
    monkeypatch.setattr(window._repo, "has_session", lambda: True)
    assert window._retry_session()
    assert not window._restore_failed
    assert window.btn_load.isEnabled()


@pytest.mark.parametrize('reject_prompt', [True, False])
def test_retry_materializes_before_unlocking(window, monkeypatch, tmp_path, reject_prompt):
    from src.scheduling.classroom import Classroom
    repo = window._repo
    repo.save_session(None, 5, {'R': Classroom('R', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'REGULAR')], {},
                      {'BIO-G1': ('R', 1, 480, 540)})
    before = (tmp_path / 'session.db').read_bytes()
    render = window.course_manager.load_courses_from_excel
    monkeypatch.setattr(window.course_manager, 'load_courses_from_excel', fail)
    window._restore_session_if_exists(confirm=False)
    assert window._restore_failed and window._busy
    assert not window.course_manager.get_courses() and set(window._classrooms) == {'R'}
    prompts = []
    def prompt(dialog):
        prompts.append(dialog)
        return QDialog.DialogCode.Rejected if reject_prompt else QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog, 'exec', prompt)
    assert not window._retry_session()
    assert window._restore_failed and window._busy and not window.btn_load.isEnabled()
    assert not window._save_session()
    assert (tmp_path / 'session.db').read_bytes() == before
    monkeypatch.setattr(window.course_manager, 'load_courses_from_excel', render)
    assert window._retry_session()
    assert not prompts  # Retry itself already authorizes restoration.
    assert not window._restore_failed and not window._busy
    assert [c.code for c in window.course_manager.get_courses()] == ['BIO']
    assert window.current_schedule == {'BIO-G1': ('R', 1, 480, 540)}
    assert (tmp_path / 'session.db').read_bytes() == before
    window.seed_input.setValue(22)
    assert [c.code for c in repo.load_session()['courses']] == ['BIO']
    assert window._retry_session()
    assert not list(tmp_path.glob('previous-session-*'))


def test_missing_session_after_partial_restore_stays_locked(window, monkeypatch, tmp_path):
    window._repo.save_session(None, 5, {}, [Course('BIO', 1, 60, 'REGULAR')], {}, None)
    monkeypatch.setattr(window.course_manager, 'load_courses_from_excel', fail)
    window._restore_session_if_exists(confirm=False)
    before = (tmp_path / 'session.db').read_bytes()
    monkeypatch.setattr(window._repo, 'has_session', lambda: False)
    assert not window._retry_session()
    assert window._restore_failed and window._busy
    assert not window._save_session()
    assert (tmp_path / 'session.db').read_bytes() == before


@pytest.mark.parametrize('comparison_error', [OSError('temporary read failure'),
                                              ValueError('invalid comparison data')])
def test_postcommit_comparison_failure_is_saved_and_read_only_retry(window, monkeypatch, tmp_path, comparison_error):
    from src.application.scenario_comparison import session_fingerprint
    window.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])
    assert window._save_session()
    window._scenario_name = 'Baseline'
    window._scenario_baseline = session_fingerprint(window._repo.load_session())
    load, save = window._repo.load_session, window._repo.save_session
    saves = []
    def failed_comparison(*args, **kwargs):
        raise comparison_error
    def committed_save(**kwargs):
        save(**kwargs)
        saves.append(kwargs)
        monkeypatch.setattr(window._repo, 'load_session', failed_comparison)
    monkeypatch.setattr(window._repo, 'save_session', committed_save)
    assert window._save_session()  # Persistence succeeded even if comparison did not.
    assert not window._unsaved and window._save_error is None
    assert window._scenario_comparison_error
    assert 'Comparación pendiente' in window._save_state_label.text()
    assert 'Sin cambios pendientes' in window._save_state_label.text()
    assert 'Sesión guardada' in window.status_bar.currentMessage()
    assert not window._retry_save_button.isHidden()
    before = (tmp_path / 'session.db').read_bytes()
    for _ in range(2):
        assert not window._retry_session()
    assert len(saves) == 1 and not window._unsaved
    assert (tmp_path / 'session.db').read_bytes() == before
    assert not list(tmp_path.glob('previous-session-*'))
    monkeypatch.setattr(window._repo, 'load_session', load)
    assert window._retry_session()
    assert len(saves) == 1
    assert window._scenario_comparison_error is None and not window._scenario_dirty
    assert window._retry_save_button.isHidden()
    assert [c.code for c in load()['courses']] == ['BIO']
    # A real Qt autosave signal must also contain the fault after committing.
    window.seed_input.setValue(window.seed_input.value() + 1)
    assert len(saves) == 2 and not window._unsaved and window._save_error is None
    monkeypatch.setattr(window._repo, 'load_session', load)
    assert window._retry_session()
    assert window._scenario_dirty


def test_unsaved_changes_take_precedence_over_pending_comparison(window, monkeypatch):
    from src.application.scenario_comparison import session_fingerprint
    assert window._save_session()
    window._scenario_name = 'Baseline'
    window._scenario_baseline = session_fingerprint(window._repo.load_session())
    window._scenario_comparison_error = 'Comparison pending'
    save = window._repo.save_session
    monkeypatch.setattr(window._repo, 'save_session', fail)
    assert not window._save_session()
    assert window._unsaved and window._save_error
    assert not window._retry_session()
    monkeypatch.setattr(window._repo, 'save_session', save)
    assert window._retry_session()
    assert not window._unsaved and window._save_error is None
    assert window._scenario_comparison_error is None
    assert not window._scenario_dirty


@pytest.mark.parametrize('language,display_language', [('es', 'es'), ('en', 'en'),
                                                     ('es', 'en'), ('en', 'es')])
def test_f6_retains_comparison_explanation_until_read_only_retry(window, monkeypatch, language, display_language):
    from PyQt6.QtCore import QTimer, Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QPlainTextEdit
    from src.application.scenario_comparison import session_fingerprint
    from src.gui.i18n import language_manager, msg

    manager, previous_language = language_manager(), language_manager().language
    manager.set_language(language, persist=False)
    try:
        assert window._save_session()
        window._scenario_name = 'Baseline'
        window._scenario_baseline = session_fingerprint(window._repo.load_session())
        load, save = window._repo.load_session, window._repo.save_session
        def comparison_failure():
            raise OSError('temporary comparison read failure')
        def commit_then_fail_comparison(**kwargs):
            save(**kwargs)
            monkeypatch.setattr(window._repo, 'load_session', comparison_failure)
        monkeypatch.setattr(window._repo, 'save_session', commit_then_fail_comparison)
        assert window._save_session()
        manager.set_language(display_language, persist=False)
        explanation = window._scenario_comparison_error.render()
        window.status_bar.showMessage('Unrelated status')
        window.show()
        window.activateWindow()
        QApplication.processEvents()

        def read_status():
            window.activateWindow()
            QApplication.processEvents()
            observed = []
            def inspect():
                dialog = QApplication.activeModalWidget()
                if dialog is None:
                    observed.append('No active status dialog')
                    return
                observed.append(dialog.findChild(QPlainTextEdit).toPlainText())
                QTest.keyClick(dialog, Qt.Key.Key_Escape)
            QTimer.singleShot(30, inspect)
            QTest.keyClick(window, Qt.Key.Key_F6)
            assert len(observed) == 1
            return observed[0]

        pending = read_status()
        assert explanation in pending
        assert str(msg('Sin cambios pendientes')) in pending
        assert str(msg('Comparación pendiente')) in pending
        assert 'Unrelated status' in pending
        assert window._repo._db_path not in pending
        assert not window._unsaved and window._save_error is None
        monkeypatch.setattr(window._repo, 'load_session', load)
        monkeypatch.setattr(window._repo, 'save_session', lambda **kwargs: pytest.fail('Retry wrote saved data'))
        assert window._retry_session()
        window.status_bar.showMessage('Another unrelated status')
        recovered = read_status()
        assert explanation not in recovered and 'temporary comparison read failure' not in recovered
        assert str(msg('Comparación pendiente')) not in recovered
        assert str(msg('Sin cambios pendientes')) in recovered
    finally:
        manager.set_language(previous_language, persist=False)


def test_f6_preserves_plain_comparison_diagnostic(window, monkeypatch):
    from PyQt6.QtWidgets import QPlainTextEdit
    window._scenario_comparison_error = 'Plain diagnostic <not markup>'
    observed = []
    def inspect(dialog):
        observed.append(dialog.findChild(QPlainTextEdit).toPlainText())
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(QDialog, 'exec', inspect)
    window._show_accessible_status()
    assert window._scenario_comparison_error in observed[0]
