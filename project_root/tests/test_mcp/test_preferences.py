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
    assert list(tmp_path.iterdir()) == [path]


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
