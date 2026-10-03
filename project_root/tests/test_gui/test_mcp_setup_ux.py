"""Native MCP setup keeps progress, permission and client steps distinct."""
import sys
import time

import pytest
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QScrollArea

from src.gui.i18n import language_manager
from src.gui.main_window import MainWindow
from src.gui.mcp_availability import McpAvailabilityProbe
from src.gui.mcp_client_help import McpClientHelp, client_configuration
from src.gui.settings_dialog import SettingsDialog
from src.infrastructure.session_repository import SessionRepository


@pytest.fixture
def window(tmp_path):
    q = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    w = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False, feature_settings=q)
    yield w
    w.close()


@pytest.fixture
def english():
    manager = language_manager()
    original = manager.language
    manager.set_language('en', persist=False)
    yield
    manager.set_language(original, persist=False)


def test_saved_and_pending_permission_are_distinct(window, monkeypatch, english):
    monkeypatch.setattr(McpAvailabilityProbe, 'start', lambda self: self.finished.emit('available'))
    dialog = SettingsDialog(window)
    assert 'Saved permission: off' in dialog.mcp_permission_label.text()
    dialog.controls['mcp_server'].setChecked(True)
    assert 'Unsaved change' in dialog.mcp_permission_label.text()
    assert not window._features.enabled('mcp_server')
    dialog.accept()
    dialog = SettingsDialog(window)
    assert 'Saved permission: on' in dialog.mcp_permission_label.text()
    dialog.controls['mcp_server'].setChecked(False)
    assert 'Permission stays on' in dialog.mcp_permission_label.text()
    assert 'pending results are discarded' in dialog.mcp_permission_label.text()
    assert window._features.enabled('mcp_server')
    dialog.reject()
    assert window._features.enabled('mcp_server')


def test_ready_state_avoids_redundant_preparation_but_can_recheck(window, english):
    dialog = SettingsDialog(window)
    dialog._show_mcp_status('prepared')
    assert not dialog.mcp_prepare_button.isEnabled()
    assert 'already available' in dialog.mcp_prepare_button.toolTip()
    assert dialog.mcp_check_button.isEnabled()
    assert dialog.mcp_help_button.isEnabled()
    assert not dialog.controls['mcp_server'].isChecked()
    dialog._show_mcp_status('missing_component')
    assert dialog.mcp_prepare_button.isEnabled()
    assert not dialog.mcp_prepare_button.toolTip()
    dialog.reject()


def test_check_can_be_cancelled_without_closing_settings(window, monkeypatch, english):
    dialog = SettingsDialog(window)
    dialog.show()
    original = dialog.mcp_probe.process.start
    monkeypatch.setattr(dialog.mcp_probe.process, 'start', lambda *args: original(sys.executable, ['-c', 'import time; time.sleep(10)']))
    dialog._check_mcp()
    assert dialog.mcp_cancel_button.isVisible()
    assert dialog.mcp_cancel_button.text() == 'Cancel MCP check'
    dialog.mcp_cancel_button.click()
    deadline = time.monotonic() + 2
    while dialog.mcp_probe.active and time.monotonic() < deadline:
        QApplication.processEvents()
    assert not dialog.mcp_probe.active
    assert dialog.isVisible() and dialog.mcp_status == 'cancelled'
    assert dialog.mcp_cancel_button.isHidden()
    assert dialog.mcp_check_button.isEnabled()
    assert not window._features.path.exists()
    dialog.reject()


@pytest.mark.parametrize('saved,pending,phrase', [(True, False, 'Saved local permission: on'),
                                                  (False, False, 'Before connecting'),
                                                  (False, True, 'unsaved permission change'),
                                                  (True, True, 'unsaved permission change')])
def test_guide_does_not_mistake_pending_permission_for_authorization(english, saved, pending, phrase):
    dialog = McpClientHelp(None, permission_enabled=saved, pending_permission=pending)
    assert phrase in dialog.permission_status.text()
    assert not dialog.copy_button.isEnabled()
    assert not dialog.configuration.toPlainText()
    dialog.reject()


@pytest.mark.parametrize('locale', ['es', 'en'])
def test_guide_small_window_keeps_close_accessible_and_code_tabbable(locale):
    manager = language_manager()
    original = manager.language
    manager.set_language(locale, persist=False)
    command = [r'C:\Users\Renée Name\SORTH\SORTH-MCP.exe', '--serve']
    dialog = McpClientHelp(command, permission_enabled=True)
    try:
        dialog.resize(460, 420)
        dialog.show()
        QApplication.processEvents()
        assert dialog.size().width() <= 460
        assert dialog.size().height() <= 420
        close = dialog.buttons.button(QDialogButtonBox.StandardButton.Close)
        assert dialog.rect().contains(close.mapTo(dialog, close.rect().center()))
        assert dialog.scroll.verticalScrollBar().maximum() > 0
        assert dialog.scroll.horizontalScrollBar().maximum() == 0
        dialog.scroll.ensureWidgetVisible(dialog.configuration)
        dialog.configuration.setFocus()
        QTest.keyClick(dialog.configuration, Qt.Key.Key_Tab)
        assert QApplication.focusWidget() == dialog.copy_button
        QTest.keyClick(dialog.copy_button, Qt.Key.Key_Space)
        assert QApplication.clipboard().text() == client_configuration('opencode', command)
        assert dialog.copy_status.text()
        dialog.client.setCurrentIndex(2)
        assert dialog.configuration.isHidden() and dialog.copy_button.isHidden()
        assert 'HTTPS' in dialog.instructions.text()
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        assert not dialog.isVisible()
    finally:
        dialog.reject()
        manager.set_language(original, persist=False)


def test_settings_small_window_reaches_guide_and_keeps_save_visible(window):
    dialog = SettingsDialog(window)
    dialog.resize(460, 420)
    dialog.show()
    QApplication.processEvents()
    assert dialog.width() <= 460 and dialog.height() <= 420
    scroll = dialog.findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum() == 0
    scroll.ensureWidgetVisible(dialog.mcp_help_button)
    assert scroll.viewport().rect().contains(dialog.mcp_help_button.mapTo(scroll.viewport(), dialog.mcp_help_button.rect().center()))
    save = dialog.buttons.button(QDialogButtonBox.StandardButton.Save)
    assert dialog.rect().contains(save.mapTo(dialog, save.rect().center()))
    dialog.reject()


def test_enter_on_check_runs_check_without_saving_or_closing(window, monkeypatch):
    calls = []
    def check(probe):
        calls.append(True)
        probe.finished.emit('available')
    monkeypatch.setattr(McpAvailabilityProbe, 'start', check)
    dialog = SettingsDialog(window)
    dialog.show()
    QApplication.processEvents()
    dialog.mcp_check_button.setFocus()
    QTest.keyClick(dialog.mcp_check_button, Qt.Key.Key_Return)
    assert calls == [True]
    assert dialog.isVisible()
    assert not window._features.path.exists()
    dialog.reject()


def test_external_revocation_before_guide_preserves_save_conflict_and_other_edits(window, monkeypatch, english):
    from src.application.mcp_preferences import enabled, set_enabled
    from src.gui import settings_dialog
    from PyQt6.QtWidgets import QMessageBox
    values = window._features.values()
    values['mcp_server'] = True
    window._features.save(values)
    dialog = SettingsDialog(window)
    dialog.controls['import_diff_preview'].setChecked(True)
    original_record = window._features._record.copy()
    set_enabled(window._features.path, False)
    seen = []
    class Guide:
        def __init__(self, command, parent, **kwargs):
            seen.append(kwargs)
        def exec(self):
            return 0
    monkeypatch.setattr(settings_dialog, 'McpClientHelp', Guide)
    dialog._show_mcp_help()
    assert seen == [{'permission_enabled': False, 'pending_permission': True}]
    assert window._features._record == original_record
    assert dialog.controls['mcp_server'].isChecked()
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    dialog.accept()
    assert warnings and not enabled(window._features.path)
    assert not dialog.controls['mcp_server'].isChecked()
    assert dialog.controls['import_diff_preview'].isChecked()
    assert 'Saved permission: off' in dialog.mcp_permission_label.text()
    dialog.accept()
    assert not enabled(window._features.path)
    assert window._features.enabled('import_diff_preview')


def test_enable_save_waits_for_check_but_disabling_never_requires_success(window, monkeypatch, english):
    from src.application.mcp_preferences import enabled
    from PyQt6.QtWidgets import QMessageBox
    dialog = SettingsDialog(window)
    original = dialog.mcp_probe.process.start
    monkeypatch.setattr(dialog.mcp_probe.process, 'start', lambda *args: original(sys.executable, ['-c', 'import time; time.sleep(10)']))
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    dialog._show_mcp_status('prepared')
    dialog.controls['mcp_server'].setChecked(True)
    save = dialog.buttons.button(QDialogButtonBox.StandardButton.Save)
    assert dialog.mcp_status == 'checking' and not save.isEnabled()
    assert 'Wait for the MCP check' in save.toolTip()
    save.click()
    dialog.accept()
    assert not warnings and not enabled(window._features.path)
    dialog.controls['mcp_server'].setChecked(False)
    assert save.isEnabled()  # OFF does not depend on a successful health check.
    dialog.accept()
    assert not enabled(window._features.path)
    assert not dialog.mcp_probe.active


def test_read_only_status_observes_external_permission_without_changing_baseline(window, english):
    from src.application.mcp_preferences import set_enabled
    values = window._features.values()
    values['mcp_server'] = True
    window._features.save(values)
    dialog = SettingsDialog(window)
    baseline = window._features._record.copy()
    set_enabled(window._features.path, False)
    dialog._refresh_mcp_permission()
    assert 'Unsaved change' in dialog.mcp_permission_label.text()
    assert window._features._record == baseline
    dialog.reject()


def test_saved_permission_can_be_revoked_while_health_check_is_running(window, monkeypatch):
    from src.application.mcp_preferences import enabled
    values = window._features.values()
    values['mcp_server'] = True
    window._features.save(values)
    dialog = SettingsDialog(window)
    original = dialog.mcp_probe.process.start
    monkeypatch.setattr(dialog.mcp_probe.process, 'start', lambda *args: original(sys.executable, ['-c', 'import time; time.sleep(10)']))
    dialog._check_mcp()
    assert dialog.mcp_probe.active and enabled(window._features.path)
    dialog.controls['mcp_server'].setChecked(False)
    assert dialog.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    dialog.accept()
    assert not enabled(window._features.path)
    assert not dialog.mcp_probe.active


@pytest.mark.parametrize('style_name', [None, 'Fusion', 'Windows'], ids=['native-default', 'Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('expanded_metrics', [False, True], ids=['normal-font', 'expanded-font'])
def test_settings_native_action_labels_reflow_without_horizontal_overflow(window, style_name, locale, expanded_metrics):
    from PyQt6.QtWidgets import QStyleFactory
    from src.gui.i18n import msg
    app = QApplication.instance()
    original_style = app.style().objectName()
    manager = language_manager()
    original_language = manager.language
    if style_name is not None and style_name not in QStyleFactory.keys():
        pytest.skip(f'{style_name} is unavailable')
    if style_name is not None:
        app.setStyle(style_name)
    manager.set_language(locale, persist=False)
    dialog = SettingsDialog(window)
    try:
        # Exercise wider native font metrics without depending on a CI machine's
        # installed fonts or DPI. The application itself never shrinks its text.
        if expanded_metrics:
            dialog.setStyleSheet('QPushButton, QCheckBox { font-size: 20pt; }')
        dialog.recovery_label.show()
        dialog.recover_button.show()
        dialog.mcp_cancel_button.setText(msg('Cancelar verificación MCP'))
        dialog.mcp_cancel_button.show()
        dialog.resize(460, 420)
        dialog.show()
        QApplication.processEvents()
        scroll = dialog.findChild(QScrollArea)
        controls = dialog._responsive_actions.controls

        def inspect_geometry():
            assert dialog.width() == 460 and dialog.height() == 420
            widths = {button.accessibleName(): button.minimumSizeHint().width() for button in controls}
            assert scroll.horizontalScrollBar().maximum() == 0, widths
            for button in controls:
                source = button._messages['setText'][1][0]
                assert ' '.join(button.text().split()) == str(source.render())
                assert button.accessibleName() == source.render()
                assert button.width() >= button.minimumSizeHint().width()
                assert button.height() >= button.minimumSizeHint().height()
            save = dialog.buttons.button(QDialogButtonBox.StandardButton.Save)
            assert dialog.rect().contains(save.mapTo(dialog, save.rect().center()))

        inspect_geometry()
        if expanded_metrics:
            assert '\n' in dialog.calendar_button.text()
        checkbox = dialog.controls['project_scenarios']
        checkbox.setFocus()
        QTest.keyClick(checkbox, Qt.Key.Key_Space)
        assert checkbox.isChecked()
        # Retranslation keeps the original Message, checked state and focus.
        manager.set_language('en' if locale == 'es' else 'es', persist=False)
        QApplication.processEvents()
        inspect_geometry()
        assert checkbox.isChecked() and checkbox.hasFocus()
        dialog.resize(900, 420)
        QApplication.processEvents()
        assert '\n' not in dialog.calendar_button.text()
        assert dialog.calendar_button.text() == dialog.calendar_button._messages['setText'][1][0].render()
        dialog.resize(460, 420)
        QApplication.processEvents()
        inspect_geometry()
    finally:
        dialog.reject()
        app.setStyle(original_style)
        manager.set_language(original_language, persist=False)
