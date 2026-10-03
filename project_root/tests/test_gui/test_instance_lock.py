"""Real GUI entry-point subprocesses; all session/settings paths are synthetic."""
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from src.infrastructure.gui_session_lock import acquire_gui_session_lock, SessionInUseError

ROOT = Path(__file__).resolve().parents[2]
WORKER = r'''
import sys
from pathlib import Path
from PyQt6.QtCore import QTimer, QSettings
from PyQt6.QtWidgets import QApplication
import gui_app
from src.infrastructure.session_repository import SessionRepository
root, control = map(Path, sys.argv[1:])
# Patch only destinations and the blocking error dialog; use the real launcher,
# MainWindow, default repository constructor and event loop.
SessionRepository.default_path = staticmethod(lambda: root / 'session.db')
SessionRepository.legacy_path = staticmethod(lambda: root / 'absent-legacy.db')
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(root / 'settings'))
gui_app.QMessageBox.warning = lambda *a: (control.with_suffix('.refused').write_text(str(a[2]), encoding='utf-8'), 0)[1]
app = QApplication([])
gui_app.QApplication = lambda argv: app
def ready():
    control.with_suffix('.ready').write_text('ready')
def stop():
    if control.with_suffix('.stop').exists():
        app.quit()
timer = QTimer()
timer.timeout.connect(stop)
timer.start(20)
QTimer.singleShot(0, ready)
gui_app.main()
'''


def launch(tmp_path, name, data=None):
    data = data or tmp_path / 'data'
    control = tmp_path / name
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', XDG_CONFIG_HOME=str(tmp_path / 'config'),
               XDG_DATA_HOME=str(tmp_path / 'xdg'), XDG_CACHE_HOME=str(tmp_path / 'cache'))
    process = subprocess.Popen([sys.executable, '-c', WORKER, str(data), str(control)],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return process, control


def await_ready(process, control):
    deadline = time.monotonic() + 15
    while not control.with_suffix('.ready').exists():
        if process.poll() is not None:
            raise AssertionError(process.communicate(timeout=1))
        if time.monotonic() >= deadline:
            process.kill()
            raise AssertionError(process.communicate(timeout=5))
        time.sleep(.01)


def stop(process, control):
    if process.poll() is None:
        control.with_suffix('.stop').touch()
    try:
        _, err = process.communicate(timeout=15)
        assert process.returncode == 0, err
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)


def test_live_owner_refuses_second_gui_before_database_mutation(tmp_path):
    owner, control = launch(tmp_path, 'owner')
    try:
        await_ready(owner, control)
        db = tmp_path / 'data/session.db'
        before = db.read_bytes()
        lock = Path(str(db) + '.gui.lock')
        lock_before = lock.read_bytes()
        # A very old timestamp must not age out a live desktop owner.
        os.utime(lock, (1, 1))
        contender, other = launch(tmp_path, 'other')
        _, err = contender.communicate(timeout=15)
        assert contender.returncode == 1, err
        assert other.with_suffix('.refused').exists()
        assert not other.with_suffix('.ready').exists()
        assert db.read_bytes() == before
        assert lock.read_bytes() == lock_before
        assert owner.poll() is None
    finally:
        stop(owner, control)
    assert not lock.exists()
    reopened, control = launch(tmp_path, 'reopened')
    try:
        await_ready(reopened, control)
    finally:
        stop(reopened, control)


def test_crashed_owner_recovers_without_force_unlock(tmp_path):
    owner, control = launch(tmp_path, 'owner')
    try:
        await_ready(owner, control)
        lock = tmp_path / 'data/session.db.gui.lock'
        assert lock.exists()
        owner.kill()
        owner.communicate(timeout=15)
        assert lock.exists()  # Crash did not execute the launcher's finally.
        restarted, control = launch(tmp_path, 'restart')
        try:
            await_ready(restarted, control)
            assert lock.exists()
        finally:
            stop(restarted, control)
        assert not lock.exists()
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.communicate(timeout=5)


@pytest.mark.parametrize('contents', [b'not a lock\n', b'123456789\nSORTH\nforeign-host.invalid\nforeign-machine\nforeign-boot\n'])
def test_malformed_and_foreign_lock_fail_closed_without_creating_database(tmp_path, contents):
    data = tmp_path / 'data'
    data.mkdir()
    lock = data / 'session.db.gui.lock'
    lock.write_bytes(contents)
    os.utime(lock, (1, 1))
    process, control = launch(tmp_path, 'blocked')
    _, err = process.communicate(timeout=15)
    assert process.returncode == 1, err
    assert control.with_suffix('.refused').exists()
    assert not (data / 'session.db').exists()
    assert lock.read_bytes() == contents


def test_separate_data_directories_can_run_together(tmp_path):
    first, first_control = launch(tmp_path, 'first', tmp_path / 'one')
    second, second_control = launch(tmp_path, 'second', tmp_path / 'two')
    try:
        await_ready(first, first_control)
        await_ready(second, second_control)
    finally:
        stop(first, first_control)
        stop(second, second_control)


def test_canonical_directory_alias_uses_same_lock(tmp_path):
    directory = tmp_path / 'real'
    directory.mkdir()
    alias = tmp_path / 'alias'
    try:
        alias.symlink_to(directory, target_is_directory=True)
    except OSError:
        pytest.skip('Directory symlinks unavailable to this user')
    lock = acquire_gui_session_lock(directory / 'session.db')
    try:
        with pytest.raises(SessionInUseError):
            acquire_gui_session_lock(alias / 'session.db')
    finally:
        lock.unlock()


def test_lock_errors_do_not_construct_repository(tmp_path, monkeypatch):
    import gui_app
    from src.infrastructure import gui_session_lock
    from src.infrastructure.session_repository import SessionRepository
    from PyQt6.QtWidgets import QApplication
    monkeypatch.setattr(sys, 'argv', ['gui_app.py'])
    monkeypatch.setattr(gui_app, 'QApplication', lambda argv: QApplication.instance())
    monkeypatch.setattr(SessionRepository, 'default_path', staticmethod(lambda: tmp_path / 'session.db'))
    monkeypatch.setattr(gui_session_lock, 'acquire_gui_session_lock', lambda p: (_ for _ in ()).throw(PermissionError('denied')))
    monkeypatch.setattr(gui_app, 'MainWindow', lambda: pytest.fail('Repository must not be opened'))
    messages = []
    monkeypatch.setattr(gui_app.QMessageBox, 'warning', lambda *args: messages.append(args))
    with pytest.raises(SystemExit) as error:
        gui_app.main()
    assert error.value.code == 1 and len(messages) == 1
    assert not (tmp_path / 'session.db').exists()


def test_startup_exception_releases_lock(tmp_path, monkeypatch):
    import gui_app
    from src.infrastructure.session_repository import SessionRepository
    from PyQt6.QtWidgets import QApplication
    monkeypatch.setattr(sys, 'argv', ['gui_app.py'])
    monkeypatch.setattr(gui_app, 'QApplication', lambda argv: QApplication.instance())
    path = tmp_path / 'session.db'
    monkeypatch.setattr(SessionRepository, 'default_path', staticmethod(lambda: path))
    monkeypatch.setattr(gui_app, 'MainWindow', lambda: (_ for _ in ()).throw(RuntimeError('startup failed')))
    with pytest.raises(RuntimeError, match='startup failed'):
        gui_app.main()
    lock = acquire_gui_session_lock(path)
    lock.unlock()


def test_recovery_entry_point_does_not_take_default_session_lock(monkeypatch):
    import gui_app
    from src.application import recovery_command
    from src.infrastructure import gui_session_lock
    monkeypatch.setattr(sys, 'argv', ['gui_app.py', '--recover-session'])
    monkeypatch.setattr(gui_session_lock, 'acquire_gui_session_lock', lambda p: pytest.fail('Recovery must not lock default session'))
    monkeypatch.setattr(recovery_command, 'run', lambda argv: 0)
    with pytest.raises(SystemExit) as error:
        gui_app.main()
    assert error.value.code == 0


def test_refusal_is_localized_and_plain_text(tmp_path, monkeypatch):
    import gui_app
    from src.gui.i18n import language_manager
    from src.infrastructure import gui_session_lock
    from PyQt6.QtWidgets import QApplication
    monkeypatch.setattr(sys, 'argv', ['gui_app.py'])
    monkeypatch.setattr(gui_app, 'QApplication', lambda argv: QApplication.instance())
    monkeypatch.setattr(gui_session_lock, 'acquire_gui_session_lock', lambda p: (_ for _ in ()).throw(SessionInUseError()))
    messages = []
    monkeypatch.setattr(gui_app.QMessageBox, 'warning', lambda *args: messages.append(args))
    manager = language_manager()
    previous = manager.language
    try:
        manager.set_language('en', persist=False)
        with pytest.raises(SystemExit):
            gui_app.main()
        assert 'Close the other SORTH window' in messages[0][2]
        assert 'Do not delete lock files' in messages[0][2]
    finally:
        manager.set_language(previous, persist=False)
