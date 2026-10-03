import json
from pathlib import Path
import subprocess
import sys
import pytest
from src.application import mcp_preferences as prefs
from src.mcp_adapter import availability


def test_default_off_and_atomic_change_preserves_foreign_fields(tmp_path, monkeypatch):
    path = tmp_path / 'settings.json'
    assert not prefs.enabled(path)
    original = {'version': 1, 'features': {'future': {'x': 1}, 'pinned_sessions': True}, 'foreign': [1]}
    path.write_text(json.dumps(original))
    prefs.set_enabled(path, True)
    assert prefs.enabled(path)
    assert prefs.read_record(path)['features']['future'] == {'x': 1}
    before = path.read_bytes()
    monkeypatch.setattr(prefs.os, 'replace', lambda *args: (_ for _ in ()).throw(OSError('test')))
    with pytest.raises(OSError):
        prefs.set_enabled(path, False)
    assert path.read_bytes() == before
    assert set(tmp_path.iterdir()) == {path, Path(str(path) + '.lock')}


@pytest.mark.parametrize('raw', ['broken', '{"version":1,"features":{"mcp_server":"true"}}',
    '{"version":1,"features":{"mcp_server":true,"pinned_sessions":"true"}}',
    '{"version":1,"features":{"mcp_server":true,"mcp_server":false}}', 'x' * 65537])
def test_damaged_preferences_fail_closed_and_cannot_silently_repair(tmp_path, raw):
    path = tmp_path / 'settings.json'
    path.write_text(raw)
    assert not prefs.enabled(path)
    with pytest.raises(ValueError):
        prefs.set_enabled(path, True)
    assert path.read_text() == raw


def test_headless_cli_and_disabled_server_work_without_site_packages(tmp_path):
    root = Path(__file__).resolve().parents[2]
    path = tmp_path / 'settings.json'
    cmd = [sys.executable, '-B', '-S', '-m', 'src.application.mcp_preferences', '--preferences', str(path)]
    for action, expected in [('--enable', 'enabled'), ('--disable', 'disabled')]:
        result = subprocess.run(cmd + [action], cwd=root, capture_output=True, text=True, timeout=5)
        assert result.returncode == 0 and result.stdout.strip() == expected
    result = subprocess.run([sys.executable, '-B', '-S', '-m', 'src.mcp_adapter.server', '--preferences', str(path)],
                            cwd=root, capture_output=True, text=True, timeout=5)
    assert result.returncode == 3 and result.stdout == '' and 'disabled' in result.stderr


def test_frozen_never_probes_sdk(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(availability.importlib.metadata, 'version', lambda _: pytest.fail('must not inspect SDK'))
    assert availability.check() == 'frozen_unsupported'


def test_missing_and_incompatible_sdk(monkeypatch):
    def missing(_):
        raise availability.importlib.metadata.PackageNotFoundError
    monkeypatch.setattr(availability.importlib.metadata, 'version', missing)
    assert availability.check() == 'missing_sdk'
    monkeypatch.setattr(availability.importlib.metadata, 'version', lambda _: '2.0.0')
    assert availability.check() == 'incompatible_sdk'


def test_compatible_and_broken_runtime(monkeypatch):
    from src.mcp_adapter import server
    monkeypatch.setattr(availability.importlib.metadata, 'version', lambda _: '1.30.0')
    monkeypatch.setattr(server, 'build_server', lambda: object())
    assert availability.check() == 'available'
    monkeypatch.setattr(server, 'build_server', lambda: (_ for _ in ()).throw(ImportError('test')))
    assert availability.check() == 'runtime_error'


def test_broken_metadata_reports_runtime_error(monkeypatch):
    monkeypatch.setattr(availability.importlib.metadata, 'version', lambda _: (_ for _ in ()).throw(ValueError('bad metadata')))
    assert availability.check() == 'runtime_error'


@pytest.mark.parametrize('generation', [None, True, 1, '', 'legacy', 'A' * 32, 'g' * 32, '0' * 31, []])
def test_invalid_generation_fails_closed_without_repair(tmp_path, generation):
    path = tmp_path / 'preferences.json'
    path.write_text(json.dumps({'version': 1, 'features': {'mcp_server': True}, 'mcp_generation': generation}))
    before = path.read_bytes()
    assert prefs.permission_generation(path) is None
    with pytest.raises(ValueError):
        prefs.set_enabled(path, True)
    assert path.read_bytes() == before


def test_permission_generation_preserved_rotated_and_legacy_migrated(tmp_path):
    path = tmp_path / 'preferences.json'
    path.write_text('{"version":1,"features":{"mcp_server":true},"future":[1]}')
    before = path.read_bytes()
    assert prefs.permission_generation(path) == 'legacy'
    assert path.read_bytes() == before  # Reads cannot silently migrate permission.
    prefs.set_enabled(path, True)
    first = prefs.permission_generation(path)
    assert first != 'legacy' and len(first) == 32
    prefs.set_enabled(path, True)
    assert prefs.permission_generation(path) == first
    prefs.set_enabled(path, False)
    disabled_generation = prefs.read_record(path)['mcp_generation']
    assert disabled_generation != first and prefs.permission_generation(path) is None
    prefs.set_enabled(path, True)
    assert prefs.permission_generation(path) not in {first, disabled_generation}
    assert prefs.read_record(path)['future'] == [1]


@pytest.mark.parametrize('foreign', ['[' * 2000 + '0' + ']' * 2000, 'NaN', 'Infinity', '-Infinity', '1e999'])
def test_adversarial_json_is_bounded_and_preserved(tmp_path, foreign):
    path = tmp_path / 'preferences.json'
    path.write_text('{"version":1,"features":{"mcp_server":true},"foreign":' + foreign + '}')
    before = path.read_bytes()
    assert not prefs.enabled(path)
    with pytest.raises(ValueError):
        prefs.set_enabled(path, True)
    assert path.read_bytes() == before


def test_parser_recursion_is_reported_as_corruption(tmp_path, monkeypatch):
    path = tmp_path / 'preferences.json'
    path.write_text('{}')
    monkeypatch.setattr(prefs.json, 'loads', lambda *args, **kwargs: (_ for _ in ()).throw(RecursionError()))
    assert not prefs.enabled(path)
    with pytest.raises(ValueError):
        prefs.read_record(path)


def test_cli_holds_lock_for_full_read_modify_write(tmp_path, monkeypatch):
    path = tmp_path / 'preferences.json'
    prefs.set_enabled(path, True)
    original = prefs.read_record
    root = Path(__file__).resolve().parents[2]
    outcomes = []
    def read_while_competing_writer_runs(value):
        result = subprocess.run([sys.executable, '-B', '-S', '-m', 'src.application.mcp_preferences',
                                 '--preferences', str(path), '--disable'], cwd=root,
                                capture_output=True, text=True, timeout=5)
        outcomes.append(result.returncode)
        return original(value)
    monkeypatch.setattr(prefs, 'read_record', read_while_competing_writer_runs)
    prefs.set_enabled(path, True)
    assert outcomes == [2]
    assert original(path)['features']['mcp_server'] is True


def test_os_lock_is_nonblocking_stable_and_released_by_process_exit(tmp_path):
    import os
    import time
    path = tmp_path / 'preferences.json'
    prefs.set_enabled(path, True)
    lock_path = Path(str(path) + '.lock')
    original_inode = lock_path.stat().st_ino
    before = path.read_bytes()
    root = Path(__file__).resolve().parents[2]
    script = '''import sys
from src.application.mcp_preferences import preferences_lock
with preferences_lock(sys.argv[1]):
    print('locked', flush=True)
    sys.stdin.readline()
'''
    process = subprocess.Popen([sys.executable, '-B', '-S', '-c', script, str(path)], cwd=root,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert process.stdout.readline() == b'locked\n'
        os.utime(lock_path, (1, 1))  # Age must never be treated as an unlock signal.
        start = time.monotonic()
        with pytest.raises(OSError):
            prefs.set_enabled(path, False)
        assert time.monotonic() - start < 1
        assert path.read_bytes() == before
        assert lock_path.stat().st_ino == original_inode
        process.kill()
        process.wait(timeout=5)
        prefs.set_enabled(path, False)
        assert not prefs.enabled(path)
        assert lock_path.exists() and lock_path.stat().st_ino == original_inode
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)
