"""Availability is published only after the companion remains verified."""
import hashlib
import json
from pathlib import Path
import sys
from threading import Event
import time

import pytest
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QApplication

from src.application import mcp_component
from src.gui.mcp_availability import McpAvailabilityProbe


def wait_until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(.005)
    assert predicate()


@pytest.fixture
def installed_bundle(tmp_path, monkeypatch):
    payload = b'verified executable fixture'
    manifest = {
        'schema_version': 1, 'component': 'sorth-mcp', 'version': '2.0.0',
        'source_commit': 'a' * 40, 'build_id': '2.0.0-' + 'a' * 12,
        'platform': 'windows-x64', 'sdk_version': '1.30.0',
        'entrypoint': 'SORTH-MCP.exe', 'archive': 'optional/mcp-component.zip',
        'archive_sha256': 'b' * 64, 'archive_size': 1,
        'files': [{'path': 'SORTH-MCP.exe', 'size': len(payload),
                   'sha256': hashlib.sha256(payload).hexdigest()}],
    }
    context = mcp_component.ComponentContext(manifest, tmp_path / 'bundle', tmp_path / 'components')
    directory = mcp_component.component_install_path(context=context)
    directory.mkdir(parents=True)
    executable = directory / manifest['entrypoint']
    executable.write_bytes(payload)
    (directory / mcp_component.MARKER).write_text(json.dumps(manifest))
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(mcp_component, '_load_context', lambda: context)
    report = dict(manifest, status='available', frozen=True)
    return context, executable, report


def launch_report(probe, monkeypatch, report, before_report=''):
    start = probe.process.start
    launched = []

    def launch(program, arguments):
        launched.append((program, arguments))
        start(sys.executable, ['-c', before_report + '\nprint(' + repr(json.dumps(report)) + ')'])

    monkeypatch.setattr(probe.process, 'start', launch)
    return launched


@pytest.mark.parametrize('change', ['overwrite', 'remove', 'extra_file', 'marker'])
def test_files_changed_during_probe_never_publish_available(installed_bundle, monkeypatch, change):
    context, executable, report = installed_bundle
    target = executable
    if change == 'overwrite':
        operation = '.write_bytes(b"changed fixture")'
    elif change == 'remove':
        operation = '.unlink()'
    elif change == 'extra_file':
        target = executable.parent / 'unexpected.dll'
        operation = '.write_bytes(b"unexpected fixture")'
    else:
        target = executable.parent / mcp_component.MARKER
        operation = '.write_text("{}")'
    probe = McpAvailabilityProbe()
    finished = []
    probe.finished.connect(finished.append)
    launched = launch_report(probe, monkeypatch, report,
                             'from pathlib import Path; Path(' + repr(str(target)) + ')' + operation)
    probe.start()
    wait_until(lambda: not probe.active)
    assert finished == ['incompatible_component' if change == 'marker' else 'integrity_error']
    assert probe.command is None
    assert launched == [(str(executable), ['--probe'])]
    assert probe.process.state() == QProcess.ProcessState.NotRunning


def test_postprobe_verification_is_cancellable_and_retryable(installed_bundle, monkeypatch):
    context, executable, report = installed_bundle
    original_command = mcp_component.installed_command
    calls = []
    postprobe = Event()

    def command(*, cancelled):
        calls.append(True)
        if len(calls) == 2:
            postprobe.set()
            while not cancelled():
                time.sleep(.005)
            raise mcp_component.ComponentError('cancelled')
        return original_command(cancelled=cancelled)

    monkeypatch.setattr(mcp_component, 'installed_command', command)
    probe = McpAvailabilityProbe()
    finished = []
    probe.finished.connect(finished.append)
    launched = launch_report(probe, monkeypatch, report)
    probe.start()
    try:
        wait_until(postprobe.is_set)
        assert probe.active and not finished
    finally:
        probe.cancel()
        wait_until(lambda: not probe.active)
    assert finished == ['cancelled'] and probe.command is None
    probe.start()
    wait_until(lambda: not probe.active)
    assert finished == ['cancelled', 'available']
    assert probe.command == [str(executable), '--serve']
    assert len(calls) == 4 and len(launched) == 2


def test_unchanged_frozen_probe_publishes_once_after_reverification(installed_bundle, monkeypatch):
    context, executable, report = installed_bundle
    original_command = mcp_component.installed_command
    calls = []

    def command(*, cancelled):
        calls.append(True)
        return original_command(cancelled=cancelled)

    monkeypatch.setattr(mcp_component, 'installed_command', command)
    probe = McpAvailabilityProbe()
    finished = []
    probe.finished.connect(lambda status: finished.append((status, len(calls))))
    launch_report(probe, monkeypatch, report)
    probe.start()
    wait_until(lambda: not probe.active)
    assert finished == [('available', 2)]
    assert probe.command == [str(executable), '--serve']


@pytest.fixture
def window(tmp_path):
    from PyQt6.QtCore import QSettings
    from src.gui.main_window import MainWindow
    from src.infrastructure.session_repository import SessionRepository
    settings = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    owner = MainWindow(SessionRepository(str(tmp_path / 'session.db')),
                       restore_session=False, feature_settings=settings)
    yield owner
    owner.close()


def test_dialog_close_retains_postprobe_verification_owner(window, installed_bundle, monkeypatch):
    from src.application.mcp_preferences import enabled
    from src.gui.settings_dialog import SettingsDialog
    context, executable, report = installed_bundle
    original_command = mcp_component.installed_command
    calls = []
    postprobe = Event()
    cleaned_up = Event()

    def command(*, cancelled):
        calls.append(True)
        if len(calls) == 2:
            postprobe.set()
            while not cancelled():
                time.sleep(.005)
            time.sleep(.04)
            cleaned_up.set()
            raise mcp_component.ComponentError('cancelled')
        return original_command(cancelled=cancelled)

    monkeypatch.setattr(mcp_component, 'installed_command', command)
    dialog = SettingsDialog(window)
    dialog.show()
    launch_report(dialog.mcp_probe, monkeypatch, report)
    dialog._check_mcp()
    try:
        wait_until(postprobe.is_set)
        dialog.close()
        assert dialog.isVisible() and dialog._pending_close is not None
        assert not cleaned_up.is_set()
    finally:
        dialog.reject()
        wait_until(lambda: not dialog.mcp_probe.active)
    assert cleaned_up.is_set() and not dialog.isVisible()
    assert dialog.mcp_status == 'cancelled' and dialog.mcp_command is None
    assert not enabled(window._features.path)
