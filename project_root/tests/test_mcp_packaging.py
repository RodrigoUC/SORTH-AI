"""Portable companion build contracts. Actual frozen acceptance runs on Windows CI."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from types import ModuleType, SimpleNamespace
import zipfile

import pytest

from tools.build_identity import identity
from tools import mcp_payload
from tools.security_review import validate_lock

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def payload(tmp_path):
    app = tmp_path / 'companion'
    internal = app / '_internal'
    internal.mkdir(parents=True)
    (app / 'SORTH-MCP.exe').write_bytes(b'MZ-synthetic-test-only')
    (internal / 'python312.dll').write_bytes(b'synthetic-native-runtime')
    (internal / 'build-identity.json').write_text(json.dumps(identity('a' * 40)))
    for name in ('LICENSE', 'LICENSING.md', 'third_party/licenses/cpython-3.12.10.txt'):
        target = internal / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT.parent / name, target)
    shutil.copytree(ROOT.parent / 'third_party/mcp', internal / 'third_party/mcp')
    return app, tmp_path / 'optional/mcp-component.zip', tmp_path / 'identity'


def create(payload):
    return mcp_payload.create_payload(*payload, 'a' * 40)


def test_payload_has_release_bound_inventory_and_compilable_trust_anchor(payload):
    manifest = create(payload)
    app, archive, output = payload
    assert manifest['platform'] == 'windows-x64'
    assert manifest['sdk_version'] == '1.30.0'
    assert manifest['archive_sha256'] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert manifest['archive_size'] == archive.stat().st_size
    with zipfile.ZipFile(archive) as zf:
        assert set(zf.namelist()) == {row['path'] for row in manifest['files']}
        assert 'SORTH-MCP.exe' in zf.namelist()
        assert all(not i.is_dir() and i.date_time == (1980, 1, 1, 0, 0, 0) for i in zf.infolist())
    module = ast.parse((output / '_sorth_mcp_bundle.py').read_text())
    assert ast.literal_eval(module.body[0].value) == manifest
    before = archive.read_bytes()
    assert create(payload) == manifest
    assert archive.read_bytes() == before
    assert mcp_payload.verify_payload(archive, output, 'a' * 40) == manifest


def test_payload_rejects_modified_archive_and_compiled_anchor(payload):
    create(payload)
    _, archive, output = payload
    archive.write_bytes(archive.read_bytes() + b'modified')
    with pytest.raises(ValueError, match='integrity'):
        mcp_payload.verify_payload(archive, output, 'a' * 40)
    create(payload)
    (output / '_sorth_mcp_bundle.py').write_text('MANIFEST = {}\n')
    with pytest.raises(ValueError, match='anchor'):
        mcp_payload.verify_payload(archive, output, 'a' * 40)


def test_payload_rejects_stale_source_and_incomplete_notices(payload):
    app, _, _ = payload
    (app / '_internal/build-identity.json').write_text(json.dumps(identity('b' * 40)))
    with pytest.raises(ValueError, match='identity'):
        create(payload)
    (app / '_internal/build-identity.json').write_text(json.dumps(identity('a' * 40)))
    inventory = app / '_internal/third_party/mcp/wheel-inventory.json'
    data = json.loads(inventory.read_text())
    data['packages'].pop()
    inventory.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='Incomplete'):
        create(payload)


@pytest.mark.parametrize('name', ['session.db', 'session.sqlite3', 'cache.pyc', 'openai/client.py', 'pandas/core.py'])
def test_payload_refuses_data_and_gui_model_libraries(payload, name):
    path = payload[0] / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'synthetic')
    with pytest.raises(ValueError):
        create(payload)
    assert not payload[1].exists()


@pytest.mark.parametrize('name', ['../escape', '/absolute', r'..\escape', 'C:drive', 'a//b',
                                'a/./b', 'a./b', 'CON.txt', 'a/NUL', 'a\nfile', 'a' * 241])
def test_payload_rejects_unsafe_member_names(name):
    with pytest.raises(ValueError, match='Unsafe'):
        mcp_payload.safe_name(name)


@pytest.mark.skipif(os.name == 'nt', reason='Windows symlink creation requires additional privileges')
def test_payload_refuses_linked_member(payload):
    app = payload[0]
    (app / '_internal/link').symlink_to(app / 'SORTH-MCP.exe')
    with pytest.raises(ValueError, match='Symlink'):
        create(payload)


def test_companion_license_inventory_is_complete_and_byte_verified(tmp_path):
    source = ROOT.parent / 'third_party/mcp'
    inventory = mcp_payload.verify_notices(source)
    assert len(inventory['packages']) == 38
    copied = tmp_path / 'notices'
    shutil.copytree(source, copied)
    notice = copied / inventory['packages'][0]['notice_file']
    notice.write_bytes(notice.read_bytes().replace(b'===== BEGIN ', b'===== BROKEN ', 1))
    with pytest.raises(ValueError, match='Incomplete'):
        mcp_payload.verify_notices(copied)


def test_isolated_companion_lock_matches_direct_pins_and_excludes_gui_model_tests():
    pins = validate_lock('requirements-mcp-windows.lock', ('requirements-mcp.txt', 'requirements-mcp-build.txt'))
    assert pins['mcp'] == '1.30.0'
    assert pins['pyinstaller'] == '6.22.2'
    assert {'pywin32', 'cryptography', 'cffi', 'pycparser'} <= set(pins)
    assert not ({'pytest', 'pandas', 'numpy', 'pyqt6', 'openpyxl', 'openai', 'anthropic'} & set(pins))
    assert 'mcp' not in validate_lock()


def test_console_spec_copies_sdk_metadata_and_isolates_internal_directory(monkeypatch):
    hooks = ModuleType('PyInstaller.utils.hooks')
    hooks.copy_metadata = lambda name, recursive: [(name, 'metadata')]
    hooks.collect_data_files = lambda name: [(name, name)]
    monkeypatch.setitem(sys.modules, 'PyInstaller', ModuleType('PyInstaller'))
    monkeypatch.setitem(sys.modules, 'PyInstaller.utils', ModuleType('PyInstaller.utils'))
    monkeypatch.setitem(sys.modules, 'PyInstaller.utils.hooks', hooks)
    calls = {}
    def factory(name, result=None):
        def capture(*args, **kwargs):
            calls[name] = (args, kwargs)
            return result
        return capture
    context = {'SPECPATH': str(ROOT), 'Analysis': factory('analysis', SimpleNamespace(
        pure=[], scripts=[], binaries=[], datas=[])), 'PYZ': factory('pyz'),
        'EXE': factory('exe'), 'COLLECT': factory('collect')}
    exec(compile((ROOT / 'SORTH-MCP.spec').read_text(), 'SORTH-MCP.spec', 'exec'), context)
    assert calls['exe'][1]['console'] is True
    assert calls['exe'][1]['contents_directory'] == '_internal'
    assert calls['exe'][1]['exclude_binaries'] is True
    assert calls['exe'][1]['upx'] is False
    assert ('mcp', 'metadata') in calls['analysis'][1]['datas']
    assert 'src.mcp_adapter.worker' in calls['analysis'][1]['hiddenimports']
    assert {'PyQt6', 'pandas', 'openai'} <= set(calls['analysis'][1]['excludes'])


def test_build_and_ci_use_companion_before_sdk_free_gui():
    build = (ROOT / 'build_exe.ps1').read_text()
    companion = (ROOT / 'build_mcp.ps1').read_text()
    workflow = (ROOT.parent / '.github/workflows/windows-review.yml').read_text()
    assert build.index('build_mcp.ps1') < build.index('-m PyInstaller @buildArgs')
    assert "'--hidden-import', '_sorth_mcp_bundle'" in build
    assert '[switch]$WithoutMcp' in build
    assert 'build/mcp/venv' in companion and '--require-hashes' in companion
    assert '--no-index' in companion
    assert 'tools/frozen_mcp_smoke.py' in workflow
    assert 'tools/mcp_payload.py notices' in companion
    assert 'companion-dependencies' in (ROOT.parent / '.github/workflows/security-review.yml').read_text()
