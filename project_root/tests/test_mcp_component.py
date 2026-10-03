"""Offline preparation is an independent, fail-closed local transaction."""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
from zipfile import ZipFile, ZipInfo

import pytest

from src.application import mcp_component as component

REAL_PROBE = component._probe


def digest(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    root = tmp_path / 'bundle'
    (root / 'optional').mkdir(parents=True)
    contents = {'SORTH-MCP.exe': b'verified-companion-fixture',
                '_internal/build-identity.json': b'{}',
                'licenses/LICENSE.txt': b'synthetic test notice'}
    archive = root / 'optional/mcp-component.zip'
    with ZipFile(archive, 'w') as output:
        for name, data in contents.items():
            output.writestr(name, data)
    raw = archive.read_bytes()
    manifest = {'schema_version': 1, 'component': 'sorth-mcp', 'version': '2.0.0',
                'source_commit': 'a' * 40, 'build_id': '2.0.0-' + 'a' * 12,
                'platform': 'windows-x64', 'sdk_version': '1.30.0',
                'entrypoint': 'SORTH-MCP.exe', 'archive': 'optional/mcp-component.zip',
                'archive_sha256': digest(raw), 'archive_size': len(raw),
                'files': [{'path': path, 'sha256': digest(data), 'size': len(data)}
                          for path, data in contents.items()]}
    monkeypatch.setattr(component, '_probe', lambda *args: None)
    return component.ComponentContext(manifest, root, tmp_path / 'components')


def test_prepare_is_offline_verified_and_idempotent(bundle, tmp_path):
    preferences = tmp_path / 'optional-features.json'
    original = b'{"version":1,"features":{"mcp_server":false}}'
    preferences.write_bytes(original)
    states = []
    result = component.prepare_component(context=bundle, progress=states.append)
    assert not result['already_prepared']
    assert states == ['verifying', 'extracting', 'checking', 'committing']
    assert component.component_status(context=bundle) == 'available'
    assert result['command'] == component.installed_command(context=bundle)
    before = {p.relative_to(bundle.components_root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
              for p in bundle.components_root.rglob('*') if p.is_file()}
    assert component.prepare_component(context=bundle)['already_prepared']
    assert before == {p.relative_to(bundle.components_root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                      for p in bundle.components_root.rglob('*') if p.is_file()}
    assert preferences.read_bytes() == original
    assert result['command'][1:] == ['--serve']


@pytest.mark.parametrize('state', ['verifying', 'extracting', 'checking', 'committing'])
def test_cancel_rolls_back_only_own_stage(bundle, state):
    retained = bundle.components_root / '2.0.0-previous'
    retained.mkdir(parents=True)
    (retained / 'keep').write_bytes(b'previous')
    cancelled = False
    def progress(value):
        nonlocal cancelled
        cancelled = value == state
    with pytest.raises(component.ComponentError, match='cancelled'):
        component.prepare_component(context=bundle, progress=progress, cancelled=lambda: cancelled)
    assert not component.component_install_path(context=bundle).exists()
    assert not list(bundle.components_root.glob('.prepare-*'))
    assert (retained / 'keep').read_bytes() == b'previous'


def test_cancel_before_start_writes_nothing(bundle):
    with pytest.raises(component.ComponentError, match='cancelled'):
        component.prepare_component(context=bundle, cancelled=lambda: True)
    assert not bundle.components_root.exists()


def test_probe_failure_preserves_permission_and_previous_version(bundle, monkeypatch):
    def fail(*args):
        raise component.ComponentError('probe_failed')
    monkeypatch.setattr(component, '_probe', fail)
    with pytest.raises(component.ComponentError, match='probe_failed'):
        component.prepare_component(context=bundle)
    assert not component.component_install_path(context=bundle).exists()
    assert not list(bundle.components_root.glob('.prepare-*'))


def test_probe_cannot_change_verified_payload(bundle, monkeypatch):
    monkeypatch.setattr(component, '_probe',
                        lambda directory, *_: (directory / 'SORTH-MCP.exe').write_bytes(b'changed'))
    with pytest.raises(component.ComponentError, match='integrity_error'):
        component.prepare_component(context=bundle)
    assert not component.component_install_path(context=bundle).exists()


def test_existing_probe_modification_never_reports_success(bundle, monkeypatch):
    component.prepare_component(context=bundle)
    executable = component.component_install_path(context=bundle) / 'SORTH-MCP.exe'
    monkeypatch.setattr(component, '_probe', lambda *_: executable.write_bytes(b'changed'))
    with pytest.raises(component.ComponentError, match='integrity_error'):
        component.prepare_component(context=bundle)
    assert executable.read_bytes() == b'changed'
    assert component.component_status(context=bundle) == 'integrity_error'


def test_archive_modified_or_missing_never_executes(bundle, monkeypatch):
    monkeypatch.setattr(component, '_probe', lambda *_: pytest.fail('must not execute'))
    archive = bundle.bundle_dir / bundle.manifest['archive']
    archive.write_bytes(b'changed archive')
    with pytest.raises(component.ComponentError, match='integrity_error'):
        component.prepare_component(context=bundle)
    archive.unlink()
    with pytest.raises(component.ComponentError, match='missing_bundle'):
        component.prepare_component(context=bundle)


def test_existing_modified_component_is_never_overwritten(bundle):
    component.prepare_component(context=bundle)
    executable = component.component_install_path(context=bundle) / 'SORTH-MCP.exe'
    executable.write_bytes(b'changed executable')
    assert component.component_status(context=bundle) == 'integrity_error'
    with pytest.raises(component.ComponentError, match='integrity_error'):
        component.prepare_component(context=bundle)
    assert executable.read_bytes() == b'changed executable'


def test_extra_installed_file_and_mismatched_marker_fail_closed(bundle):
    component.prepare_component(context=bundle)
    directory = component.component_install_path(context=bundle)
    extra = directory / 'extra.dll'
    extra.write_bytes(b'unknown')
    assert component.component_status(context=bundle) == 'integrity_error'
    extra.unlink()
    (directory / component.MARKER).write_text('{}')
    assert component.component_status(context=bundle) == 'incompatible_component'


@pytest.mark.parametrize('name', ['../escape.exe', '/absolute.exe', 'C:/absolute.exe',
                                 'a\\b.exe', 'a//b.exe', 'a/./b.exe', 'a/../b.exe',
                                 'NUL.txt', 'COM1', 'a./file', 'a /file', 'file:ads',
                                 'bad?.dll', 'SORTH-MCP.exe'])
def test_manifest_rejects_unsafe_or_duplicate_paths(bundle, name):
    bundle.manifest['files'].append({'path': name, 'sha256': 'a' * 64, 'size': 1})
    with pytest.raises(component.ComponentError, match='invalid_manifest'):
        component.prepare_component(context=bundle)
    assert not bundle.components_root.exists()


def test_manifest_rejects_case_alias_and_file_directory_collision(bundle):
    bundle.manifest['files'].append({'path': 'sorth-mcp.EXE', 'sha256': 'a' * 64, 'size': 1})
    with pytest.raises(component.ComponentError):
        component.bundle_info(context=bundle)
    bundle.manifest['files'][-1]['path'] = 'licenses'
    with pytest.raises(component.ComponentError):
        component.bundle_info(context=bundle)


@pytest.mark.parametrize(('key', 'value'), [('schema_version', True), ('sdk_version', '2.0.0'),
                                           ('entrypoint', 'other.exe'), ('archive_size', True),
                                           ('archive', '../elsewhere.zip'), ('source_commit', 'main'),
                                           ('build_id', '../escape'), ('platform', 'linux')])
def test_manifest_identity_is_strict(bundle, key, value):
    bundle.manifest[key] = value
    with pytest.raises(component.ComponentError, match='invalid_manifest'):
        component.bundle_info(context=bundle)


def test_trusted_zip_with_symlink_is_rejected(bundle):
    archive = bundle.bundle_dir / bundle.manifest['archive']
    with ZipFile(archive, 'w') as output:
        for item in bundle.manifest['files']:
            info = ZipInfo(item['path'])
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            output.writestr(info, b'x' * item['size'])
    raw = archive.read_bytes()
    bundle.manifest.update(archive_sha256=digest(raw), archive_size=len(raw))
    with pytest.raises(component.ComponentError, match='integrity_error'):
        component.prepare_component(context=bundle)


def test_links_in_install_root_or_lock_are_rejected(bundle, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    try:
        bundle.components_root.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Creating symlinks requires platform permission')
    with pytest.raises(component.ComponentError, match='integrity_error'):
        component.prepare_component(context=bundle)
    bundle.components_root.unlink()
    bundle.components_root.mkdir()
    (outside / 'lock').write_bytes(b'unchanged')
    (bundle.components_root / 'installation.lock').symlink_to(outside / 'lock')
    with pytest.raises(component.ComponentError, match='integrity_error'):
        component.prepare_component(context=bundle)
    assert (outside / 'lock').read_bytes() == b'unchanged'


def test_compiled_trust_anchor_is_required(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    assert component.component_status() == 'missing_bundle'
    monkeypatch.setattr(sys, 'frozen', True)
    monkeypatch.setattr(sys, 'platform', 'win32')
    def missing(_):
        raise ImportError
    monkeypatch.setattr(component.importlib, 'import_module', missing)
    assert component.component_status() == 'missing_bundle'


def test_probe_identity_requires_exact_frozen_release(bundle):
    manifest = bundle.manifest
    report = {'status': 'available', 'frozen': True, 'component': 'sorth-mcp',
              **{key: manifest[key] for key in ('version', 'source_commit', 'build_id', 'sdk_version')}}
    assert component.probe_matches(report, manifest)
    for key in report:
        altered = copy.deepcopy(report)
        altered[key] = None
        assert not component.probe_matches(altered, manifest)


def test_rename_failure_removes_stage_and_never_reports_success(bundle, monkeypatch):
    def fail(*args):
        raise PermissionError
    monkeypatch.setattr(Path, 'rename', fail)
    with pytest.raises(component.ComponentError, match='io_error'):
        component.prepare_component(context=bundle)
    assert not component.component_install_path(context=bundle).exists()
    assert not list(bundle.components_root.glob('.prepare-*'))


def test_cleanup_failure_is_explicit(bundle, monkeypatch):
    def fail(*args, **kwargs):
        raise PermissionError
    monkeypatch.setattr(component.shutil, 'rmtree', fail)
    cancelled = False
    def progress(state):
        nonlocal cancelled
        cancelled = state == 'extracting'
    with pytest.raises(component.ComponentError, match='cleanup_failed'):
        component.prepare_component(context=bundle, cancelled=lambda: cancelled, progress=progress)
    assert list(bundle.components_root.glob('.prepare-*'))


def test_same_version_concurrent_prepare_is_busy(bundle):
    bundle.components_root.mkdir()
    with component.preferences_lock(bundle.components_root / 'installation'):
        with pytest.raises(component.ComponentError, match='busy'):
            component.prepare_component(context=bundle)


def test_mutable_bundle_info_cannot_change_context(bundle):
    copied = component.bundle_info(context=bundle)
    copied['files'].clear()
    assert bundle.manifest['files']


@pytest.mark.skipif(os.name == 'nt', reason='Synthetic shebang fixture; real EXE probe is Windows CI')
@pytest.mark.parametrize('behavior', ['valid', 'mismatch', 'overflow', 'timeout', 'cancel', 'descendant', 'exit_race'])
def test_probe_output_lifetime_and_cancellation_are_bounded(bundle, monkeypatch, tmp_path, behavior):
    directory = tmp_path / 'probe'
    directory.mkdir()
    report = {'status': 'available', 'component': 'sorth-mcp', 'frozen': True,
              **{key: bundle.manifest[key] for key in ('version', 'source_commit', 'build_id', 'sdk_version')}}
    if behavior == 'mismatch':
        report['source_commit'] = 'b' * 40
    program = 'import json, sys, time\n'
    if behavior == 'overflow':
        program += 'sys.stdout.write("X" * 10000); sys.stdout.flush(); time.sleep(10)\n'
    elif behavior == 'descendant':
        program += ('import subprocess\nsubprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])\n'
                    'time.sleep(30)\n')
    elif behavior in ('timeout', 'cancel'):
        program += 'time.sleep(10)\n'
    else:
        if behavior == 'exit_race':
            program += 'time.sleep(0.02)\n'
        program += 'print(' + repr(json.dumps(report)) + ')\n'
    executable = directory / 'SORTH-MCP.exe'
    executable.write_text('#!' + sys.executable + '\n' + program)
    executable.chmod(0o700)
    monkeypatch.setattr(component, 'PROBE_TIMEOUT', 2 if behavior in ('valid', 'mismatch', 'exit_race') else 0.15)
    if behavior == 'exit_race':
        read = component.read_available
        paused = False
        def read_during_exit(*args):
            nonlocal paused
            data = read(*args)
            if not data and not paused:
                paused = True
                time.sleep(0.15)  # Child prints and exits after this empty read.
            return data
        monkeypatch.setattr(component, 'read_available', read_during_exit)
    started = time.monotonic()
    cancelled = lambda: behavior == 'cancel' and time.monotonic() - started > 0.06
    if behavior in ('valid', 'exit_race'):
        REAL_PROBE(directory, bundle.manifest, cancelled)
    else:
        with pytest.raises(component.ComponentError, match='cancelled' if behavior == 'cancel' else 'probe_failed'):
            REAL_PROBE(directory, bundle.manifest, cancelled)
    assert time.monotonic() - started < 3
