"""Review archives must not silently include old executables or local sessions."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from tools.package_windows import package


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    app = tmp_path / 'app'
    app.mkdir()
    (app / 'SORTH.exe').write_bytes(b'MZ-test-only')
    (app / '_internal').mkdir()
    (app / '_internal' / 'library.dll').write_bytes(b'test')
    manual = tmp_path / 'manual.pdf'
    manual.write_bytes(b'%PDF-test-only')
    monkeypatch.setattr(subprocess, 'check_output', lambda *a, **k: 'pytest==9.1.1\n')
    return app, manual, tmp_path / 'out'


def test_archive_has_current_manual_commit_and_hash(inputs):
    app, manual, out = inputs
    archive = package(app, manual, out, 'a' * 40)
    with zipfile.ZipFile(archive) as zf:
        assert 'SORTH/SORTH.exe' in zf.namelist()
        assert b'GNU GENERAL PUBLIC LICENSE' in zf.read('SORTH/LICENSE')
        assert b'GPL-3.0-only' in zf.read('SORTH/LICENSING.md')
        assert 'SORTH/third_party/wheel-inventory.json' in zf.namelist()
        assert 'SORTH/third_party/licenses/pyqt6.txt' in zf.namelist()
        assert 'SORTH/third_party/licenses/cpython-3.12.10.txt' in zf.namelist()
        assert 'SORTH/third_party/licenses/dejavu-font.txt' in zf.namelist()
        assert 'SORTH/docs/SOURCE_AVAILABILITY.md' in zf.namelist()
        assert zf.read('SORTH/MANUAL_USUARIO.pdf') == manual.read_bytes()
        info = json.loads(zf.read('SORTH/build-info.json'))
        assert info['source_commit'] == 'a' * 40
        assert info['signed'] is False
    assert (out / 'SHA256SUMS.txt').read_text().split()[0] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert (out / 'SHA256SUMS.txt').read_bytes().endswith(b'\n')
    with pytest.raises(ValueError, match='already exists'):
        package(app, manual, out, 'a' * 40)


@pytest.mark.parametrize('name', ['session.db', 'session.sqlite', 'cache.pyc'])
def test_archive_refuses_user_data(inputs, name):
    app, manual, out = inputs
    (app / name).write_bytes(b'private')
    with pytest.raises(ValueError, match='local session/cache'):
        package(app, manual, out, 'a' * 40)
    assert not out.exists()


def test_source_smoke_runs_isolated_and_exports(tmp_path):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / 'smoke'
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    result = subprocess.run([sys.executable, str(root / 'gui_app.py'), '--smoke-test',
                             '--smoke-output', str(output)], env=env,
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr
    report = json.loads((output / 'smoke-result.json').read_text(encoding='utf-8'))
    assert report['ok'] and not report['frozen']
    assert report['assigned'] == report['groups'] > 0
    assert set(report['stages']) == {'bundled_excel_import', 'background_schedule',
                                     'excel_csv_export', 'sqlite_roundtrip', 'qt_render', 'language_switch_es_en'}
    assert (output / 'schedule.png').is_file()
