import json
import sys
import time
import pytest
from PyQt6.QtCore import QSettings, QStandardPaths, QProcess
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.application.mcp_preferences import enabled, default_path
from src.gui.features import FeaturePreferences
from src.gui.main_window import MainWindow
from src.gui.settings_dialog import SettingsDialog
from src.gui.mcp_availability import McpAvailabilityProbe
from src.gui.i18n import language_manager
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


def test_same_default_path_as_qt():
    from pathlib import Path
    assert default_path() == Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericConfigLocation)) / 'SORTH' / 'optional-features.json'


def test_cancel_never_enables_and_save_rechecks_local_availability(window, monkeypatch):
    monkeypatch.setattr(McpAvailabilityProbe, 'start', lambda self: self.finished.emit('available'))
    dialog = SettingsDialog(window)
    dialog.controls['mcp_server'].setChecked(True)
    assert dialog.mcp_status == 'available' and not enabled(window._features.path)
    dialog.reject()
    assert not enabled(window._features.path)
    dialog = SettingsDialog(window)
    dialog.controls['mcp_server'].setChecked(True)
    dialog.accept()
    assert enabled(window._features.path)
    dialog = SettingsDialog(window)
    dialog.controls['mcp_server'].setChecked(False)
    dialog.accept()
    assert not enabled(window._features.path)


@pytest.mark.parametrize('status', ['missing_sdk', 'incompatible_sdk', 'frozen_unsupported', 'runtime_error', 'timeout',
                                        'missing_bundle', 'missing_component', 'integrity_error', 'incompatible_component'])
def test_unavailable_cannot_be_enabled(window, monkeypatch, status):
    monkeypatch.setattr(McpAvailabilityProbe, 'start', lambda self: self.finished.emit(status))
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    dialog = SettingsDialog(window)
    dialog.controls['mcp_server'].setChecked(True)
    dialog.accept()
    assert warnings and not enabled(window._features.path)
    dialog.reject()


def test_failed_save_cannot_enable(window, monkeypatch):
    monkeypatch.setattr(McpAvailabilityProbe, 'start', lambda self: self.finished.emit('available'))
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: None)
    window._features.save(window._features.values())
    original = window._features.path.read_bytes()
    dialog = SettingsDialog(window)
    dialog.controls['mcp_server'].setChecked(True)
    monkeypatch.setattr(window._features, '_write_atomic', lambda *args: (_ for _ in ()).throw(OSError('test')))
    dialog.accept()
    assert not enabled(window._features.path)
    assert window._features.path.read_bytes() == original
    dialog.reject()


def test_frozen_does_not_spawn_second_gui(window, monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    from src.application import mcp_component
    monkeypatch.setattr(mcp_component, 'bundle_info', lambda: (_ for _ in ()).throw(mcp_component.ComponentError('missing_bundle')))
    monkeypatch.setattr(QProcess, 'start', lambda *args: pytest.fail('EXE must not launch itself'))
    dialog = SettingsDialog(window)
    dialog._check_mcp()
    wait_until(lambda: dialog.mcp_status != 'checking')
    assert dialog.mcp_status == 'missing_bundle'
    dialog.reject()


def test_probe_real_process_is_bounded_and_retryable(window, monkeypatch):
    dialog = SettingsDialog(window)
    probe = dialog.mcp_probe
    original_start = probe.process.start
    monkeypatch.setattr(probe.process, 'start', lambda *args: original_start(sys.executable, ['-c', 'import time; time.sleep(10)']))
    probe.TIMEOUT_MS = 30
    dialog._check_mcp()
    wait_until(lambda: dialog.mcp_status == 'timeout')
    assert probe.process.state() == QProcess.ProcessState.NotRunning
    assert dialog.mcp_check_button.isEnabled()
    probe.TIMEOUT_MS = 5000
    dialog._check_mcp()
    dialog.reject()
    assert not probe.active and probe.process.state() == QProcess.ProcessState.NotRunning
    assert not enabled(window._features.path)


def test_real_probe_no_sdk_and_localized_status(window):
    dialog = SettingsDialog(window)
    dialog._check_mcp()
    wait_until(lambda: dialog.mcp_status != 'checking', timeout=6)
    assert dialog.mcp_status in {'missing_sdk', 'available'}
    manager = language_manager()
    original = manager.language
    try:
        manager.set_language('en', persist=False)
        assert dialog.controls['mcp_server'].text() == 'Allow local MCP server'
        assert dialog.mcp_check_button.text() == 'Check local MCP availability'
        assert 'MCP' in dialog.mcp_status_label.text()
    finally:
        manager.set_language(original, persist=False)
        dialog.reject()


def test_corrupt_non_mcp_preference_is_also_fail_closed(window):
    path = window._features.path
    path.write_text(json.dumps({'version': 1, 'features': {'mcp_server': True, 'pinned_sessions': 'bad'}}))
    assert not enabled(path)
    prefs = FeaturePreferences(path=path)
    assert prefs.load_error and not prefs.enabled('mcp_server')


def test_mcp_enable_cannot_leak_through_failed_resource_transaction(window, monkeypatch):
    monkeypatch.setattr(McpAvailabilityProbe, 'start', lambda self: self.finished.emit('available'))
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: None)
    monkeypatch.setattr(window, '_apply_resource_parameters', lambda *args: pytest.fail('No partial transaction'))
    dialog = SettingsDialog(window)
    dialog.controls['mcp_server'].setChecked(True)
    dialog.controls['teacher'].setChecked(True)
    dialog.accept()
    assert not enabled(window._features.path)
    assert not window._features.path.exists()
    dialog.reject()


@pytest.mark.parametrize('script', ["raise RuntimeError('private detail')", "print('invalid response')", "print('x' * 10000)"])
def test_probe_process_errors_are_safe_and_retryable(window, monkeypatch, script):
    dialog = SettingsDialog(window)
    probe = dialog.mcp_probe
    original_start = probe.process.start
    monkeypatch.setattr(probe.process, 'start', lambda *args: original_start(sys.executable, ['-c', script]))
    dialog._check_mcp()
    wait_until(lambda: dialog.mcp_status == 'runtime_error')
    assert 'private detail' not in dialog.mcp_status_label.text()
    assert dialog.mcp_check_button.isEnabled() and not probe.active
    dialog.reject()


def test_external_cli_disable_cannot_be_overwritten_by_unrelated_save(window, monkeypatch):
    from src.application.mcp_preferences import set_enabled
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: None)
    window._features.save({**window._features.values(), 'mcp_server': True})
    dialog = SettingsDialog(window)
    set_enabled(window._features.path, False)
    dialog.controls['placement_suggestions'].setChecked(True)
    dialog.accept()
    assert not enabled(window._features.path)
    assert not dialog.controls['mcp_server'].isChecked()
    assert not window._features.enabled('placement_suggestions')
    dialog.accept()
    assert not enabled(window._features.path)
    assert window._features.enabled('placement_suggestions')


def test_opening_and_checking_refresh_external_permission(window, monkeypatch):
    from src.application.mcp_preferences import set_enabled
    monkeypatch.setattr(McpAvailabilityProbe, 'start', lambda self: self.finished.emit('available'))
    set_enabled(window._features.path, True)
    dialog = SettingsDialog(window)
    assert dialog.controls['mcp_server'].isChecked()
    set_enabled(window._features.path, False)
    dialog._check_mcp()
    assert not dialog.controls['mcp_server'].isChecked()
    dialog.reject()


@pytest.mark.parametrize('initial', [False, True])
def test_mcp_transition_and_resource_change_are_separate_transactions(window, monkeypatch, initial):
    monkeypatch.setattr(McpAvailabilityProbe, 'start', lambda self: self.finished.emit('available'))
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    window._features.save({**window._features.values(), 'mcp_server': initial})
    before = window._features.path.read_bytes()
    dialog = SettingsDialog(window)
    dialog.controls['mcp_server'].setChecked(not initial)
    dialog.controls['teacher'].setChecked(True)
    monkeypatch.setattr(window, '_apply_resource_parameters', lambda *args: pytest.fail('No mixed transaction'))
    dialog.accept()
    assert warnings and window._features.path.read_bytes() == before
    assert enabled(window._features.path) == initial
    dialog.reject()


def test_gui_lock_covers_read_and_commit_against_cli(window, monkeypatch):
    import subprocess
    from pathlib import Path
    from src.application.mcp_preferences import permission_generation, set_enabled
    window._features.save({**window._features.values(), 'mcp_server': True})
    generation = permission_generation(window._features.path)
    root = Path(__file__).resolve().parents[2]
    outcomes = []
    def compete():
        result = subprocess.run([sys.executable, '-B', '-S', '-m', 'src.application.mcp_preferences',
                                 '--preferences', str(window._features.path), '--disable'], cwd=root,
                                capture_output=True, text=True, timeout=5)
        outcomes.append(result.returncode)
    original_read, original_write = window._features._read, window._features._write_atomic
    def read():
        compete()
        return original_read()
    def write(record):
        compete()
        return original_write(record)
    monkeypatch.setattr(window._features, '_read', read)
    monkeypatch.setattr(window._features, '_write_atomic', write)
    window._features.save({**window._features.values(), 'placement_suggestions': True})
    assert outcomes == [2, 2]
    assert permission_generation(window._features.path) == generation
    monkeypatch.setattr(window._features, '_read', original_read)
    monkeypatch.setattr(window._features, '_write_atomic', original_write)
    set_enabled(window._features.path, False)
    from src.gui.features import McpPreferenceConflict
    with pytest.raises(McpPreferenceConflict):
        window._features.save(window._features.values())
    assert not enabled(window._features.path)


def test_cli_lock_blocks_gui_save_and_recovery_without_changing_files(window):
    import subprocess
    from pathlib import Path
    window._features.save({**window._features.values(), 'mcp_server': True})
    before = window._features.path.read_bytes()
    original_generation = window._features._record['mcp_generation']
    root = Path(__file__).resolve().parents[2]
    # Pause a real CLI writer inside its atomic replace while the OS lock is held.
    script = '''import sys
from src.application import mcp_preferences as prefs
original = prefs._write_atomic
def pause(path, record):
    print('locked', flush=True)
    sys.stdin.readline()
    original(path, record)
prefs._write_atomic = pause
prefs.set_enabled(sys.argv[1], False)
'''
    process = subprocess.Popen([sys.executable, '-B', '-S', '-c', script, str(window._features.path)],
                               cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert process.stdout.readline().rstrip(b'\r\n') == b'locked'
        with pytest.raises(OSError):
            window._features.save({**window._features.values(), 'placement_suggestions': True})
        with pytest.raises(OSError):
            window._features.recover_defaults()
        assert window._features.path.read_bytes() == before
        assert window._features._record['mcp_generation'] == original_generation
        assert not list(window._features.path.parent.glob('*.preserved-*.bak'))
        stdout, stderr = process.communicate(b'continue\n', timeout=5)
        assert process.returncode == 0, stderr
        assert not enabled(window._features.path)
        assert Path(str(window._features.path) + '.lock').exists()
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)


def test_off_on_cli_sequence_conflicts_with_stale_gui_snapshot(window):
    from src.application.mcp_preferences import set_enabled
    from src.gui.features import McpPreferenceConflict
    window._features.save({**window._features.values(), 'mcp_server': True})
    set_enabled(window._features.path, False)
    set_enabled(window._features.path, True)
    with pytest.raises(McpPreferenceConflict):
        window._features.save({**window._features.values(), 'placement_suggestions': True})
    assert not window._features.enabled('placement_suggestions')


@pytest.mark.parametrize('value', ['', 'relative-config-directory'])
def test_empty_or_relative_xdg_config_matches_qt_fallback(monkeypatch, value):
    from pathlib import Path
    if sys.platform in {'win32', 'darwin'}:
        pytest.skip('XDG fallback is a Linux/Unix configuration convention')
    monkeypatch.setenv('XDG_CONFIG_HOME', value)
    assert default_path().is_absolute()
    assert default_path() == Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericConfigLocation)) / 'SORTH' / 'optional-features.json'
