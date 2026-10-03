"""Companion entry dispatch preserves source and frozen worker semantics."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

import mcp_app
from src.mcp_adapter import availability


def test_worker_dispatch_is_sdk_free(monkeypatch):
    from src.mcp_adapter import worker
    called = []
    monkeypatch.setattr(worker, 'main', lambda: called.append('worker'))
    assert mcp_app.main(['--worker']) == 0
    assert called == ['worker']


def test_companion_requires_explicit_mode():
    for args in ([], ['--serve', '--worker'], ['-m', 'arbitrary'], ['--worker', '--preferences', 'anything']):
        with pytest.raises(SystemExit) as caught:
            mcp_app.main(args)
        assert caught.value.code == 2


def test_probe_does_not_require_or_write_permission(monkeypatch, capsys):
    monkeypatch.setattr(availability, 'check', lambda **_: 'available')
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    assert mcp_app.main(['--probe']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {'status': 'available', 'component': 'sorth-mcp',
                      'sdk_version': '1.30.0', 'frozen': False}


def test_frozen_probe_requires_build_identity(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(availability, 'check', lambda **_: 'available')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    assert mcp_app.main(['--probe']) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'runtime_error'
    identity = {'version': '2.0.0', 'source_commit': 'a' * 40, 'build_id': '2.0.0-' + 'a' * 12}
    (tmp_path / 'build-identity.json').write_text(json.dumps(identity))
    assert mcp_app.main(['--probe']) == 0
    assert json.loads(capsys.readouterr().out)['build_id'] == identity['build_id']


def test_disabled_companion_exits_before_sdk_import(tmp_path):
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run([sys.executable, '-B', '-S', str(root / 'mcp_app.py'),
                             '--serve', '--preferences', str(tmp_path / 'missing.json')],
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 3
    assert not result.stdout
    assert list(tmp_path.iterdir()) == []


def test_frozen_worker_command_has_explicit_dispatch(monkeypatch):
    pytest.importorskip('mcp')
    from src.mcp_adapter.execution import PreviewExecutor
    from src.application.preview_contract import ContractError
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    assert PreviewExecutor(packaged=True).worker_command() == [sys.executable, '--worker']
    with pytest.raises(ContractError):
        PreviewExecutor().worker_command()
    monkeypatch.setattr(sys, 'frozen', False)
    assert PreviewExecutor(packaged=True).worker_command() == [sys.executable, '-B', '-m', 'src.mcp_adapter.worker']
