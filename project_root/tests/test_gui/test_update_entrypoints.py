"""Opt-in boundaries, transactional Settings and safe update close ownership."""
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import time

import pytest
from PyQt6.QtCore import QObject, QSettings, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from src.application import app_updates, update_launch
from src.application.scenario_comparison import session_fingerprint
from src.gui import update_startup, update_dialog
from src.gui.main_window import MainWindow
from src.gui.settings_dialog import SettingsDialog
from src.gui.i18n import msg
from src.gui.i18n_widgets import QMessageBox
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def window(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    owner = MainWindow(SessionRepository(str(tmp_path / 'session.db')),
                       restore_session=False, feature_settings=settings)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.StandardButton.Cancel)
    yield owner
    owner._pending_update_installer = None
    owner._unsaved = owner._busy = owner._restore_failed = owner._loading = False
    owner.close()


class FakeOperation(QObject):
    finished = pyqtSignal(str, object)

    def __init__(self, parent):
        super().__init__(parent)
        self.active = False
        self.calls = []
        self.cancelled = False

    def start(self, kind, argument=None):
        self.calls.append((kind, argument))
        self.active = True
        return True

    def cancel(self):
        self.cancelled = True

    def complete(self, status='check', state='available'):
        self.active = False
        self.finished.emit(status, SimpleNamespace(state=state,
                           release=SimpleNamespace(version='2.1.0')))


def enable_notice(window):
    window._features.save({**window._features.values(), 'auto_update_check': True})


def test_construction_and_unsaved_opt_in_remain_offline(window, monkeypatch):
    monkeypatch.setattr(update_startup, 'UpdateOperation',
                        lambda *args: pytest.fail('No committed network opt-in'))
    assert not hasattr(window, '_update_startup')
    assert not window._features.enabled('auto_update_check')
    dialog = SettingsDialog(window)
    assert 'auto_update_check' in dialog.section_features['general']
    dialog.controls['auto_update_check'].setChecked(True)
    assert update_startup.start_update_notice(window) is None
    dialog.reject()
    assert not window._features.path.exists()


def test_committed_opt_in_checks_once_and_only_notifies(window, monkeypatch):
    enable_notice(window)
    monkeypatch.setattr(update_startup, 'UpdateOperation', FakeOperation)
    controller = update_startup.start_update_notice(window)
    assert update_startup.start_update_notice(window) is controller
    assert controller.operation.calls == [('check', None)]
    controller.operation.complete()
    assert window.status_bar.currentMessage() == str(msg(
        'SORTH {version} está disponible. Abre Configuración → Buscar actualizaciones para revisarlo.',
        version='2.1.0'))
    assert window._pending_update_installer is None


@pytest.mark.parametrize('guard', ['_busy', '_restore_failed', '_save_error', '_scenario_comparison_error'])
def test_startup_notice_does_not_replace_work_or_recovery(window, monkeypatch, guard):
    enable_notice(window)
    monkeypatch.setattr(update_startup, 'UpdateOperation', FakeOperation)
    controller = update_startup.start_update_notice(window)
    window.status_bar.showMessage('Existing important status')
    setattr(window, guard, True)
    controller.operation.complete()
    assert window.status_bar.currentMessage() == 'Existing important status'
    assert controller._notice_timer.isActive()
    setattr(window, guard, False)
    controller._show_when_idle()
    assert '2.1.0' in window.status_bar.currentMessage()
    assert not controller._notice_timer.isActive()


def test_startup_suppresses_late_result_after_opt_out(window, monkeypatch):
    enable_notice(window)
    monkeypatch.setattr(update_startup, 'UpdateOperation', FakeOperation)
    controller = update_startup.start_update_notice(window)
    window._features.save({**window._features.values(), 'auto_update_check': False})
    window.status_bar.showMessage('Unchanged')
    controller.operation.complete()
    assert window.status_bar.currentMessage() == 'Unchanged'


@pytest.mark.parametrize('status,state', [('network_error', 'available'), ('check', 'current'),
                                         ('check', 'no_releases')])
def test_startup_has_no_dialog_or_status_for_empty_results(window, monkeypatch, status, state):
    enable_notice(window)
    monkeypatch.setattr(update_startup, 'UpdateOperation', FakeOperation)
    controller = update_startup.start_update_notice(window)
    window.status_bar.showMessage('Unchanged')
    controller.operation.complete(status, state)
    assert window.status_bar.currentMessage() == 'Unchanged'


def test_close_cancels_and_drains_real_startup_worker_before_retry(window, monkeypatch):
    enable_notice(window)
    entered, drained = Event(), Event()

    def check(version, *, cancelled):
        entered.set()
        deadline = time.monotonic() + 3
        while not cancelled() and time.monotonic() < deadline:
            time.sleep(.005)
        time.sleep(.02)
        drained.set()
        # Simulate a successful result racing cancellation. It must not surface.
        return SimpleNamespace(state='available', release=SimpleNamespace(version='9.0.0'))

    monkeypatch.setattr(app_updates, 'current_app_version', lambda: '2.0.0')
    monkeypatch.setattr(app_updates, 'check_updates', check)
    window.show()
    window.status_bar.showMessage('Existing status')
    controller = update_startup.start_update_notice(window)
    assert entered.wait(2)
    window.close()
    assert window.isVisible() and controller.operation.active
    deadline = time.monotonic() + 3
    while (controller.operation.active or window.isVisible()) and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(.005)
    assert drained.is_set()
    assert not controller.operation.active and not window.isVisible()
    assert window.status_bar.currentMessage() == 'Existing status'


@pytest.mark.parametrize('accepted', [False, True])
def test_settings_update_entrypoint_never_saves_pending_preferences(window, monkeypatch, accepted):
    dialog = SettingsDialog(window)
    dialog.show()
    dialog.controls['auto_update_check'].setChecked(True)
    dialog.controls['pinned_sessions'].setChecked(True)
    seen, closed = [], []
    pending = object()

    class UpdateDialog:
        def __init__(self, target, parent):
            assert target is window and parent is dialog
            seen.append(self)

        def exec(self):
            if accepted:
                window._pending_update_installer = pending
            return SettingsDialog.DialogCode.Accepted if accepted else SettingsDialog.DialogCode.Rejected

        def deleteLater(self):
            seen.append('disposed')

    monkeypatch.setattr(update_dialog, 'UpdateDialog', UpdateDialog)
    monkeypatch.setattr(window, 'close', lambda: closed.append(True))
    dialog.update_button.click()
    QApplication.processEvents()
    assert len(seen) == 2 and seen[-1] == 'disposed'
    assert not window._features.path.exists()
    assert not window._features.enabled('auto_update_check')
    assert not window._features.enabled('pinned_sessions')
    assert closed == ([True] if accepted else [])
    assert dialog.isVisible() is not accepted
    assert dialog.result() == SettingsDialog.DialogCode.Rejected
    dialog.reject()


@pytest.mark.parametrize('guard', ['_busy', '_restore_failed', '_loading'])
def test_install_close_refuses_busy_or_recovery_and_discards_download(window, monkeypatch, guard):
    discarded = []
    monkeypatch.setattr(app_updates, 'discard_download', discarded.append)
    monkeypatch.setattr(window, '_save_session', lambda: pytest.fail('Must not save during work/recovery'))
    pending = window._pending_update_installer = object()
    window.show()
    setattr(window, guard, True)
    window.close()
    assert window.isVisible()
    assert window._pending_update_installer is None and not window._update_close_accepted
    assert discarded == [pending]


def test_install_close_requires_packaged_windows(window, monkeypatch):
    monkeypatch.setattr(update_launch, 'installer_launch_supported', lambda: False)
    discarded = []
    monkeypatch.setattr(app_updates, 'discard_download', discarded.append)
    pending = window._pending_update_installer = object()
    window.show()
    window.close()
    assert window.isVisible() and discarded == [pending]
    assert not window._update_close_accepted


@pytest.mark.parametrize('kind', ['generation', 'import'])
def test_install_close_refuses_workers_with_queued_delivery(window, monkeypatch, kind):
    monkeypatch.setattr(window, '_save_session', lambda: pytest.fail('Worker still owns pending delivery'))
    owner, attribute = (window, '_worker') if kind == 'generation' else (window._import, 'worker')
    setattr(owner, attribute, object())
    window._pending_update_installer = object()
    window.show()
    try:
        window.close()
        assert window.isVisible()
        assert not window._update_close_accepted and window._pending_update_installer is None
    finally:
        setattr(owner, attribute, None)


@pytest.mark.parametrize('failure', ['save', 'backup', 'invalid_backup'])
def test_install_close_failure_keeps_window_without_discard_session_route(window, monkeypatch, tmp_path, failure):
    monkeypatch.setattr(update_launch, 'installer_launch_supported', lambda: True)
    discarded, warnings = [], []
    monkeypatch.setattr(app_updates, 'discard_download', discarded.append)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    pending = window._pending_update_installer = object()
    if failure == 'save':
        monkeypatch.setattr(window, '_save_session', lambda: False)
    elif failure == 'backup':
        monkeypatch.setattr(window._repo, 'backup_session',
                            lambda: (_ for _ in ()).throw(OSError('Synthetic failure')))
    else:
        invalid = tmp_path / 'invalid.db'
        invalid.write_bytes(b'not sqlite')
        monkeypatch.setattr(window._repo, 'backup_session', lambda: invalid)
    window.show()
    window.close()
    assert window.isVisible() and discarded == [pending]
    assert not window._update_close_accepted and window._pending_update_installer is None
    assert len(warnings) == 1 and len(warnings[0]) == 3


def test_install_close_saves_and_validates_backup_even_without_dirty_flag(window, monkeypatch):
    monkeypatch.setattr(update_launch, 'installer_launch_supported', lambda: True)
    pending = window._pending_update_installer = object()
    assert not window._unsaved and not window._repo.has_session()
    window.show()
    window.close()
    assert not window.isVisible()
    assert window._pending_update_installer is pending and window._update_close_accepted
    assert window._repo.has_session()
    backup = window._update_backup_path
    assert isinstance(backup, Path) and backup.is_file()
    reopened = SessionRepository(str(backup))
    assert reopened.has_session()
    assert reopened.load_session() == window._repo.load_session()


def test_failed_update_backup_preserves_saved_session_and_scenario_identity(window, monkeypatch):
    window._classrooms = {'ROOM': Classroom('ROOM', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('SYNTHETIC', 1, 60, 'REGULAR')])
    assert window._save_session()
    before = session_fingerprint(window._repo.load_session())
    window._scenario_name = 'Synthetic scenario'
    window._scenario_id = 'synthetic-id'
    window._scenario_baseline = before
    window._scenario_dirty = False
    monkeypatch.setattr(update_launch, 'installer_launch_supported', lambda: True)
    monkeypatch.setattr(app_updates, 'discard_download', lambda download: None)
    monkeypatch.setattr(window._repo, 'backup_session',
                        lambda: (_ for _ in ()).throw(OSError('Synthetic backup failure')))
    window._pending_update_installer = object()
    window.show()
    window.close()
    assert window.isVisible() and not window._update_close_accepted
    assert window._pending_update_installer is None
    assert session_fingerprint(window._repo.load_session()) == before
    assert window._scenario_name == 'Synthetic scenario'
    assert window._scenario_id == 'synthetic-id'
    assert window._scenario_baseline == before and not window._scenario_dirty
    assert not window._unsaved and not window._restore_failed


@pytest.mark.parametrize('accepted,launch_fails', [(False, False), (True, False), (True, True)])
def test_main_launches_only_after_safe_close_event_loop_and_session_unlock(
        window, monkeypatch, accepted, launch_fails):
    import gui_app
    from src.infrastructure import gui_session_lock

    app = QApplication.instance()
    events, warnings, discarded = [], [], []
    pending = window._pending_update_installer = object()
    monkeypatch.setattr(gui_app.sys, 'argv', ['gui_app.py'])
    monkeypatch.setattr(gui_app, 'QApplication', lambda args: app)
    monkeypatch.setattr(gui_app, 'MainWindow', lambda: window)
    monkeypatch.setattr(gui_session_lock, 'acquire_gui_session_lock',
                        lambda path: SimpleNamespace(unlock=lambda: events.append('unlock')))
    monkeypatch.setattr(update_launch, 'installer_launch_supported', lambda: True)

    def event_loop():
        events.append('event-loop')
        if accepted:
            window.close()
            assert window._update_close_accepted
            assert window._update_backup_path.exists()
        events.append('event-loop-ended')
        return 0

    def launch(download):
        assert download is pending
        assert events[-1] == 'unlock'
        events.append('launch')
        if launch_fails:
            raise app_updates.UpdateError('launch_failed')

    monkeypatch.setattr(app, 'exec', event_loop)
    monkeypatch.setattr(update_launch, 'launch_pending_update', launch)
    monkeypatch.setattr(app_updates, 'discard_download', discarded.append)
    monkeypatch.setattr(gui_app.QMessageBox, 'warning', lambda *args: warnings.append(args))
    with pytest.raises(SystemExit) as caught:
        gui_app.main()
    assert caught.value.code == 0
    assert events == ['event-loop', 'event-loop-ended', 'unlock'] + (['launch'] if accepted else [])
    assert len(warnings) == int(launch_fails)
    assert discarded == ([pending] if launch_fails else [])


def test_main_starts_saved_opt_in_only_after_window_show(window, monkeypatch):
    import gui_app
    from src.infrastructure import gui_session_lock

    enable_notice(window)
    app = QApplication.instance()
    events = []
    monkeypatch.setattr(gui_app.sys, 'argv', ['gui_app.py'])
    monkeypatch.setattr(gui_app, 'QApplication', lambda args: app)
    monkeypatch.setattr(gui_app, 'MainWindow', lambda: window)
    monkeypatch.setattr(gui_session_lock, 'acquire_gui_session_lock',
                        lambda path: SimpleNamespace(unlock=lambda: events.append('unlock')))

    def start(owner):
        assert owner is window and window.isVisible()
        events.append('check')

    monkeypatch.setattr(update_startup, 'start_update_notice', start)
    monkeypatch.setattr(app, 'exec', lambda: events.append('event-loop') or 0)
    with pytest.raises(SystemExit):
        gui_app.main()
    assert events == ['check', 'event-loop', 'unlock']


@pytest.mark.parametrize('active', [False, True], ids=['downloaded-idle', 'checking'])
def test_main_close_rejects_manual_dialog_and_drains_before_owner_deletion(window, monkeypatch, active):
    entered, drained = Event(), Event()
    discarded, completed = [], []
    pending = object()
    settings = SettingsDialog(window)
    native_exec = update_dialog.UpdateDialog.exec

    def check(version, *, cancelled):
        entered.set()
        deadline = time.monotonic() + 3
        while not cancelled() and time.monotonic() < deadline:
            time.sleep(.005)
        time.sleep(.03)
        drained.set()
        return app_updates.UpdateResult('no_releases', version)

    def run(dialog):
        if active:
            dialog.check()
            assert entered.wait(2)
        else:
            dialog.download = pending
        QTimer.singleShot(20, window.close)
        result = native_exec(dialog)
        completed.append((result, dialog.operation.active, drained.is_set()))
        return result

    monkeypatch.setattr(app_updates, 'check_updates', check)
    monkeypatch.setattr(app_updates, 'discard_download', discarded.append)
    monkeypatch.setattr(update_dialog.UpdateDialog, 'exec', run)
    window.show()
    settings.show()
    settings.open_updates()
    QApplication.processEvents()
    assert completed == [(SettingsDialog.DialogCode.Rejected, False, active)]
    assert not window.isVisible() and not settings.isVisible()
    assert window._active_update_dialog is None and not window._close_after_update_dialog
    assert window._pending_update_installer is None and not window._update_close_accepted
    assert discarded == ([] if active else [pending])
