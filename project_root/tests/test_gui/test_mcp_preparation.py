"""Preparation is an explicit transaction, separate from feature permission."""
import ast
import json
from pathlib import Path
import sys
from threading import Event
import time

import pytest
from PyQt6.QtCore import QProcess, QSettings, Qt
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox

from src.application import mcp_component
from src.application.mcp_preferences import enabled
from src.gui.i18n import language_manager
from src.gui.locales import LANGUAGES
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


def wait_until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(.005)
    assert predicate()


@pytest.fixture
def bundle(monkeypatch, tmp_path):
    manifest = {'component': 'sorth-mcp', 'version': '1.2.3', 'build_id': 'test',
                'sdk_version': '1.30.0', 'source_commit': 'a' * 40}
    destination = tmp_path / 'components' / 'test'
    command = [str(destination / 'SORTH-MCP.exe'), '--serve']
    monkeypatch.setattr(mcp_component, 'bundle_info', lambda: dict(manifest))
    monkeypatch.setattr(mcp_component, 'component_install_path', lambda: destination)
    return {'manifest': manifest, 'path': str(destination), 'command': command,
            'already_prepared': False}


def test_preparation_requires_explicit_confirmation(window, monkeypatch, bundle):
    dialog = SettingsDialog(window)
    approvals = []
    monkeypatch.setattr(dialog, '_confirm_mcp_preparation', lambda *args: approvals.append(args) or False)
    monkeypatch.setattr(mcp_component, 'prepare_component', lambda **kwargs: pytest.fail('No confirmed preparation'))
    dialog._prepare_mcp()
    assert len(approvals) == 1
    assert not dialog.mcp_preparation.active
    assert not enabled(window._features.path)
    dialog.reject()


def test_confirmation_is_plain_text_default_cancel(window, monkeypatch, bundle):
    from src.gui.i18n_widgets import QMessageBox as LocalMessageBox
    seen = []
    def inspect(self):
        seen.append(self.text())
        assert self.textFormat() == Qt.TextFormat.PlainText
        assert self.defaultButton() == self.button(QMessageBox.StandardButton.Cancel)
        return QMessageBox.StandardButton.Cancel
    monkeypatch.setattr(LocalMessageBox, 'exec', inspect)
    dialog = SettingsDialog(window)
    assert not dialog._confirm_mcp_preparation(bundle['manifest'], Path(bundle['path']))
    assert bundle['path'] in seen[0] and '1.2.3' in seen[0]
    dialog.reject()


def test_preparation_persists_without_enabling_when_settings_cancelled(window, monkeypatch, bundle):
    dialog = SettingsDialog(window)
    monkeypatch.setattr(dialog, '_confirm_mcp_preparation', lambda *args: True)
    destination = Path(bundle['path'])
    def prepare(**kwargs):
        destination.mkdir(parents=True, exist_ok=True)
        (destination / 'installed').write_text('verified')
        kwargs['progress']('checking')
        return bundle
    monkeypatch.setattr(mcp_component, 'prepare_component', prepare)
    dialog._prepare_mcp()
    wait_until(lambda: not dialog.mcp_preparation.active)
    assert dialog.mcp_status == 'available'
    assert dialog.mcp_command == bundle['command']
    assert not dialog.controls['mcp_server'].isChecked()
    assert not enabled(window._features.path)
    dialog.reject()
    assert (destination / 'installed').read_text() == 'verified'
    assert not enabled(window._features.path)


@pytest.mark.parametrize('close', ['reject', 'close', 'cancel_preparation'])
def test_close_cancel_and_repeated_clicks_are_safe(window, monkeypatch, bundle, close):
    started = Event()
    completed = Event()
    approvals = []
    calls = []
    def prepare(cancelled, progress):
        calls.append(True)
        started.set()
        while not cancelled():
            time.sleep(.005)
        time.sleep(.04)  # allow the GUI to show safe cancellation without blocking
        completed.set()
        raise mcp_component.ComponentError('cancelled')
    monkeypatch.setattr(mcp_component, 'prepare_component', prepare)
    dialog = SettingsDialog(window)
    dialog.show()
    monkeypatch.setattr(dialog, '_confirm_mcp_preparation', lambda *args: approvals.append(True) or True)
    dialog._prepare_mcp()
    wait_until(started.is_set)
    dialog._prepare_mcp()
    dialog.accept()  # no preference write while preparing, even programmatically
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    assert len(calls) == len(approvals) == 1 and not window._features.path.exists()
    if close == 'cancel_preparation':
        dialog._cancel_mcp_preparation()
    else:
        getattr(dialog, close)()
        assert dialog.isVisible() and dialog._pending_close is not None
    wait_until(lambda: not dialog.mcp_preparation.active)
    assert completed.is_set() and not enabled(window._features.path)
    if close == 'cancel_preparation':
        assert dialog.isVisible() and dialog.mcp_status == 'cancelled'
        dialog.reject()
    else:
        assert not dialog.isVisible()


@pytest.mark.parametrize('code', ['missing_bundle', 'unsupported_platform', 'invalid_manifest',
                                  'integrity_error', 'busy', 'io_error', 'probe_failed',
                                  'incompatible_component', 'cleanup_failed'])
def test_preparation_errors_never_enable_and_retry_controls_return(window, monkeypatch, bundle, code):
    dialog = SettingsDialog(window)
    monkeypatch.setattr(dialog, '_confirm_mcp_preparation', lambda *args: True)
    def fail(**kwargs):
        raise mcp_component.ComponentError(code)
    monkeypatch.setattr(mcp_component, 'prepare_component', fail)
    dialog._prepare_mcp()
    wait_until(lambda: not dialog.mcp_preparation.active)
    assert dialog.mcp_status == code
    assert dialog.mcp_prepare_button.isEnabled()
    assert dialog.mcp_check_button.isEnabled()
    assert not enabled(window._features.path) and dialog.mcp_command is None
    dialog.reject()


def test_absent_bundle_does_not_claim_prepared_or_ask_confirmation(window, monkeypatch):
    dialog = SettingsDialog(window)
    def missing():
        raise mcp_component.ComponentError('missing_bundle')
    monkeypatch.setattr(mcp_component, 'bundle_info', missing)
    monkeypatch.setattr(dialog, '_confirm_mcp_preparation', lambda *args: pytest.fail('No bundle to prepare'))
    dialog._prepare_mcp()
    assert dialog.mcp_status == 'missing_bundle'
    assert not dialog.mcp_preparation.active and not enabled(window._features.path)
    dialog.reject()


def test_commit_wins_late_cancel_without_fake_rollback(window, monkeypatch, bundle):
    committed = Event()
    finish = Event()
    def prepare(**kwargs):
        committed.set()
        finish.wait(2)
        return bundle
    monkeypatch.setattr(mcp_component, 'prepare_component', prepare)
    dialog = SettingsDialog(window)
    monkeypatch.setattr(dialog, '_confirm_mcp_preparation', lambda *args: True)
    dialog._prepare_mcp()
    wait_until(committed.is_set)
    dialog._cancel_mcp_preparation()
    finish.set()
    wait_until(lambda: not dialog.mcp_preparation.active)
    assert dialog.mcp_status == 'available'
    assert not enabled(window._features.path)
    dialog.reject()


@pytest.mark.parametrize('changed', [None, 'build_id', 'component', 'version', 'source_commit', 'sdk_version', 'frozen'])
def test_frozen_probe_uses_companion_and_checks_identity(window, monkeypatch, bundle, changed):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(mcp_component, 'installed_command', lambda **kwargs: bundle['command'])
    report = {**bundle['manifest'], 'status': 'available', 'frozen': True}
    if changed:
        report[changed] = 'different'
    dialog = SettingsDialog(window)
    original = dialog.mcp_probe.process.start
    observed = []
    def start(program, args):
        observed.append((program, args))
        dialog.mcp_probe.process.setWorkingDirectory(str(Path(__file__).resolve().parents[2]))
        original(sys.executable, ['-c', 'print(' + repr(json.dumps(report)) + ')'])
    monkeypatch.setattr(dialog.mcp_probe.process, 'start', start)
    dialog._check_mcp()
    wait_until(lambda: dialog.mcp_status != 'checking')
    assert observed == [(bundle['command'][0], ['--probe'])]
    assert dialog.mcp_status == ('incompatible_component' if changed else 'available')
    assert dialog.mcp_command == (None if changed else bundle['command'])
    dialog.reject()


def test_close_cancels_async_hash_verification_before_process(window, monkeypatch, bundle):
    started = Event()
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    def command(cancelled):
        started.set()
        while not cancelled():
            time.sleep(.005)
        raise mcp_component.ComponentError('cancelled')
    monkeypatch.setattr(mcp_component, 'installed_command', command)
    monkeypatch.setattr(QProcess, 'start', lambda *args: pytest.fail('Cancelled before execution'))
    dialog = SettingsDialog(window)
    dialog.show()
    dialog._check_mcp()
    wait_until(started.is_set)
    dialog.reject()
    wait_until(lambda: not dialog.mcp_probe.active)
    assert not dialog.isVisible() and dialog.mcp_status == 'cancelled'


def test_client_configs_copy_exact_paths_and_never_use_shell(monkeypatch):
    command = [r'C:\Users\Renée Name\SORTH\SORTH-MCP.exe', '--serve']
    opencode = json.loads(client_configuration('opencode', command))
    assert opencode['mcp']['servers']['sorth-preview'] == {
        'type': 'local', 'command': command, 'disabled': True, 'protocol': 'legacy'}
    claude = json.loads(client_configuration('claude', command))
    assert claude['mcpServers']['sorth-preview'] == {'command': command[0], 'args': ['--serve']}
    dialog = McpClientHelp(command)
    dialog._copy()
    assert QApplication.clipboard().text() == client_configuration('opencode', command)
    dialog.client.setCurrentIndex(2)
    assert not dialog.copy_button.isEnabled()
    assert dialog.configuration.isHidden()
    assert 'HTTPS' in dialog.instructions.text() and 'Secure MCP Tunnel' in dialog.instructions.text()
    dialog.reject()


def test_new_controls_live_translate_without_changing_configuration(window, bundle):
    manager = language_manager()
    original = manager.language
    dialog = SettingsDialog(window)
    help_dialog = McpClientHelp(bundle['command'], dialog)
    before = help_dialog.configuration.toPlainText()
    try:
        manager.set_language('en', persist=False)
        assert dialog.mcp_prepare_button.text() == 'Prepare MCP add-on'
        assert help_dialog.copy_button.text() == 'Copy configuration'
        assert help_dialog.configuration.accessibleName() == 'Client configuration to copy'
        assert help_dialog.configuration.toPlainText() == before
        assert not enabled(window._features.path)
    finally:
        manager.set_language(original, persist=False)
        help_dialog.reject()
        dialog.reject()


def test_new_ui_catalog_coverage_including_status_mappings():
    root = Path(__file__).parents[2] / 'src' / 'gui'
    for filename in ['mcp_client_help.py', 'settings_dialog.py']:
        tree = ast.parse((root / filename).read_text())
        strings = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'msg':
                if node.args and isinstance(node.args[0], ast.Constant):
                    strings.add(node.args[0].value)
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in {'messages', 'instructions'} for target in node.targets) and isinstance(node.value, ast.Dict):
                strings.update(value.value for value in node.value.values if isinstance(value, ast.Constant))
        for language in LANGUAGES.values():
            assert strings <= language.messages.keys(), (filename, language.code, strings - language.messages.keys())


@pytest.mark.parametrize('command', [None, ['relative.exe', '--serve'],
                                      ['/absolute.exe', '--probe'], ['one'], 'sh'])
def test_client_configuration_rejects_unverified_shape(command):
    with pytest.raises(ValueError):
        client_configuration('opencode', command)


def test_repeated_preparation_remains_separate_from_permission(window, monkeypatch, bundle):
    calls = []
    def prepare(**kwargs):
        calls.append(True)
        return {**bundle, 'already_prepared': len(calls) > 1}
    monkeypatch.setattr(mcp_component, 'prepare_component', prepare)
    dialog = SettingsDialog(window)
    monkeypatch.setattr(dialog, '_confirm_mcp_preparation', lambda *args: True)
    for _ in range(2):
        dialog._prepare_mcp()
        wait_until(lambda: not dialog.mcp_preparation.active)
        assert dialog.mcp_status == 'available'
        assert not dialog.controls['mcp_server'].isChecked()
        assert not enabled(window._features.path)
    assert len(calls) == 2
    dialog.reject()
