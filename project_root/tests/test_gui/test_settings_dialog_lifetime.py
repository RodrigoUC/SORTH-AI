"""Modal settings invocations release native controls without waiting for GC."""
from pathlib import Path
from threading import Event
import time

import pytest
from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QEvent, QSettings, QTimer, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialogButtonBox

from src.gui.appearance_dialog import AppearanceDialog
from src.gui.main_window import MainWindow
from src.gui.settings_dialog import SettingsDialog
from src.infrastructure.session_repository import SessionRepository


@pytest.fixture
def window(tmp_path):
    settings = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    owner = MainWindow(SessionRepository(str(tmp_path / 'session.db')),
                       restore_session=False, feature_settings=settings)
    owner.show()
    QApplication.processEvents()
    yield owner
    owner.close()
    owner.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def flush_deletions():
    # processEvents alone does not deliver deferred deletion outside app.exec().
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()


@pytest.mark.parametrize('dismiss', ['cancel', 'escape', 'close', 'save'])
def test_settings_entry_point_releases_each_completed_dialog(window, monkeypatch, dismiss):
    native_exec = SettingsDialog.exec
    seen = []

    def run(dialog):
        # Keep Python wrappers referenced deliberately: this checks deterministic
        # native disposal, rather than an incidental cyclic-GC collection.
        seen.append(dialog)
        if dismiss == 'save':
            dialog.controls['pinned_sessions'].setChecked(True)
        if dismiss == 'escape':
            action = lambda: QTest.keyClick(dialog, Qt.Key.Key_Escape)
        elif dismiss == 'close':
            action = dialog.close
        else:
            button = (QDialogButtonBox.StandardButton.Save if dismiss == 'save'
                      else QDialogButtonBox.StandardButton.Cancel)
            action = dialog.buttons.button(button).click
        QTimer.singleShot(0, action)
        return native_exec(dialog)

    monkeypatch.setattr(SettingsDialog, 'exec', run)
    for _ in range(3):
        window._show_settings()
        flush_deletions()
        assert all(sip.isdeleted(dialog) for dialog in seen)
        assert not window.findChildren(SettingsDialog)
    assert window._features.enabled('pinned_sessions') is (dismiss == 'save')
    window._features.refresh()
    assert window._features.enabled('pinned_sessions') is (dismiss == 'save')


def test_nested_preview_cancel_releases_both_dialogs_and_preserves_state(window, monkeypatch):
    native_settings_exec = SettingsDialog.exec
    native_appearance_exec = AppearanceDialog.exec
    settings_seen, appearance_seen = [], []
    before_features = window._features.values()
    before_database = Path(window._repo._db_path).read_bytes()
    before_motion = window._motion.reduced
    before_settings = window._features.settings.allKeys()
    before_optional = window._features.path.exists()

    def run_appearance(dialog):
        appearance_seen.append(dialog)
        dialog.selector.setCurrentIndex(dialog.selector.findData('nocturno'))
        QTimer.singleShot(0, dialog.cancel_button.click)
        return native_appearance_exec(dialog)

    def run_settings(dialog):
        settings_seen.append(dialog)
        dialog.controls['pinned_sessions'].setChecked(True)
        def preview_then_cancel():
            dialog.open_appearance()
            dialog.reject()
        QTimer.singleShot(0, preview_then_cancel)
        return native_settings_exec(dialog)

    monkeypatch.setattr(AppearanceDialog, 'exec', run_appearance)
    monkeypatch.setattr(SettingsDialog, 'exec', run_settings)
    for _ in range(3):
        window._show_settings()
        flush_deletions()
        assert all(sip.isdeleted(dialog) for dialog in settings_seen + appearance_seen)
        assert not window.findChildren(SettingsDialog)
        assert not window.findChildren(AppearanceDialog)
    assert len(appearance_seen) == 3
    assert window._features.values() == before_features
    assert Path(window._repo._db_path).read_bytes() == before_database
    assert window._motion.reduced == before_motion
    assert window._features.settings.allKeys() == before_settings
    assert window._features.path.exists() == before_optional


@pytest.mark.parametrize('dismiss', ['reject', 'close'])
def test_settings_disposal_waits_for_pending_mcp_cleanup(window, monkeypatch, dismiss):
    from src.application import mcp_component
    from src.application.mcp_preferences import enabled

    cleanup_finished = Event()
    cancellation_seen = Event()
    native_exec = SettingsDialog.exec
    seen, pending, completed, destroyed = [], [], [], []

    def prepare(*, cancelled, progress):
        deadline = time.monotonic() + 3
        while not cancelled() and time.monotonic() < deadline:
            time.sleep(.005)
        if cancelled():
            cancellation_seen.set()
        # The dialog must stay owned throughout cooperative staging cleanup.
        time.sleep(.04)
        cleanup_finished.set()
        raise mcp_component.ComponentError('cancelled')

    def run(dialog):
        seen.append(dialog)
        dialog.destroyed.connect(lambda: destroyed.append(cleanup_finished.is_set()))
        def begin_and_close():
            # Exercise the real Qt thread/controller. Only the synthetic install
            # operation is replaced; no file or executable is prepared here.
            dialog.mcp_preparation.start()
            getattr(dialog, dismiss)()
            pending.append((dialog.isVisible(), dialog.mcp_preparation.active,
                            dialog._pending_close is not None))
        QTimer.singleShot(0, begin_and_close)
        result = native_exec(dialog)
        completed.append((cleanup_finished.is_set(), dialog.mcp_preparation.active,
                          dialog.mcp_status, result))
        return result

    monkeypatch.setattr(mcp_component, 'prepare_component', prepare)
    monkeypatch.setattr(SettingsDialog, 'exec', run)
    window._show_settings()
    flush_deletions()
    assert cancellation_seen.is_set()
    assert pending == [(True, True, True)]
    assert completed == [(True, False, 'cancelled', SettingsDialog.DialogCode.Rejected)]
    assert destroyed == [True]
    assert all(sip.isdeleted(dialog) for dialog in seen)
    assert not enabled(window._features.path)
    assert not window._features.path.exists()
