"""Prepare an offline, release-bound MCP companion without changing permission.

Only an identity compiled into the frozen GUI authorizes a payload. This module
does not download software, discover interpreters, edit clients or start a server.
"""
from dataclasses import dataclass
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from zipfile import BadZipFile, ZipFile

from .mcp_preferences import preferences_lock

MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_EXPANDED_BYTES = 1024 * 1024 * 1024
MAX_FILES = 8192
MARKER = '.sorth-component.json'
PROBE_TIMEOUT = 10
PROBE_MAX_OUTPUT = 4096


class ComponentError(Exception):
    """A fixed, localizable failure code; never expose raw dependency diagnostics."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ComponentContext:
    manifest: dict
    bundle_dir: Path
    components_root: Path


def _relative(value):
    if (not isinstance(value, str) or not value or len(value) > 240
            or any(c in value for c in '\\:*?"<>|') or any(ord(c) < 32 for c in value)):
        raise ComponentError('invalid_manifest')
    path = PurePosixPath(value)
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                *(f'LPT{i}' for i in range(1, 10))}
    if (path.is_absolute() or str(path) != value or any(
            part in {'.', '..'} or part.endswith((' ', '.'))
            or part.split('.')[0].upper() in reserved for part in path.parts)):
        raise ComponentError('invalid_manifest')
    return path


def _valid_manifest(manifest):
    try:
        # Copy to prevent a caller changing the trust anchor during verification.
        manifest = json.loads(json.dumps(manifest, allow_nan=False))
        if (manifest['schema_version'] != 1 or type(manifest['schema_version']) is not int
                or manifest['component'] != 'sorth-mcp'
                or manifest['platform'] != 'windows-x64'
                or manifest['entrypoint'] != 'SORTH-MCP.exe'
                or manifest['sdk_version'] != '1.30.0'
                or manifest['archive'] != 'optional/mcp-component.zip'
                or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', manifest['version'])
                or not re.fullmatch(r'[0-9a-f]{40}', manifest['source_commit'])
                or manifest['build_id'] != manifest['version'] + '-' + manifest['source_commit'][:12]
                or not re.fullmatch(r'[0-9a-f]{64}', manifest['archive_sha256'])
                or type(manifest['archive_size']) is not int
                or not 0 < manifest['archive_size'] <= MAX_ARCHIVE_BYTES
                or not isinstance(manifest['files'], list)
                or not 1 <= len(manifest['files']) <= MAX_FILES):
            raise ComponentError('invalid_manifest')
        paths = set()
        total = 0
        for item in manifest['files']:
            path = str(_relative(item['path']))
            if (path.casefold() in paths or path.casefold() == MARKER.casefold()
                    or type(item['size']) is not int or item['size'] < 0
                    or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])):
                raise ComponentError('invalid_manifest')
            paths.add(path.casefold())
            total += item['size']
        # A file must never also be a parent directory of a different member.
        if (manifest['entrypoint'].casefold() not in paths or total > MAX_EXPANDED_BYTES
                or any(str(parent).casefold() in paths for item in manifest['files']
                       for parent in PurePosixPath(item['path']).parents if str(parent) != '.')):
            raise ComponentError('invalid_manifest')
        return manifest
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        raise ComponentError('invalid_manifest') from None


def _load_context():
    if not getattr(sys, 'frozen', False):
        raise ComponentError('missing_bundle')
    if sys.platform != 'win32':
        raise ComponentError('unsupported_platform')
    try:
        identity = importlib.import_module('_sorth_mcp_bundle')
    except ImportError:
        raise ComponentError('missing_bundle') from None
    root = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
    if not root.is_absolute():
        root = Path.home() / 'AppData' / 'Local'
    return ComponentContext(_valid_manifest(getattr(identity, 'MANIFEST', None)), Path(sys._MEIPASS),
                            root / 'SORTH' / 'components' / 'mcp')


def _context(context):
    found = context if context is not None else _load_context()
    result = ComponentContext(_valid_manifest(found.manifest), Path(found.bundle_dir),
                              Path(found.components_root))
    if not result.bundle_dir.is_absolute() or not result.components_root.is_absolute():
        raise ComponentError('invalid_manifest')
    return result


def bundle_info(*, context=None):
    return _context(context).manifest


def component_install_path(*, context=None):
    context = _context(context)
    return context.components_root / context.manifest['build_id']


def _cancelled(cancelled):
    if cancelled():
        raise ComponentError('cancelled')


def _no_links(path):
    """Reject symlinks and Windows junction/reparse points, including parents."""
    path = Path(path)
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ComponentError('integrity_error')


def _digest(path, expected_size, cancelled):
    _no_links(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != expected_size:
        raise ComponentError('integrity_error')
    digest = hashlib.sha256()
    with path.open('rb') as source:
        total = 0
        while chunk := source.read(1024 * 1024):
            _cancelled(cancelled)
            total += len(chunk)
            if total > expected_size:
                raise ComponentError('integrity_error')
            digest.update(chunk)
    if total != expected_size:
        raise ComponentError('integrity_error')
    return digest.hexdigest()


def _verify_files(directory, manifest, cancelled, *, marker=True):
    _no_links(directory)
    expected = {item['path'] for item in manifest['files']}
    if marker:
        expected.add(MARKER)
    actual = set()
    for path in directory.rglob('*'):
        _cancelled(cancelled)
        _no_links(path)
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
        elif not path.is_dir():
            raise ComponentError('integrity_error')
    if actual != expected:
        raise ComponentError('integrity_error')
    for item in manifest['files']:
        if _digest(directory / item['path'], item['size'], cancelled) != item['sha256']:
            raise ComponentError('integrity_error')
    if marker:
        with (directory / MARKER).open('rb') as source:
            record = source.read(4 * 1024 * 1024 + 1)
        if len(record) > 4 * 1024 * 1024 or json.loads(record) != manifest:
            raise ComponentError('incompatible_component')


def installed_command(*, context=None, cancelled=lambda: False):
    context = _context(context)
    directory = component_install_path(context=context)
    if not directory.exists():
        raise ComponentError('missing_component')
    try:
        _verify_files(directory, context.manifest, cancelled)
    except (OSError, ValueError, TypeError):
        raise ComponentError('integrity_error') from None
    return [str(directory / context.manifest['entrypoint']), '--serve']


def component_status(*, context=None):
    try:
        installed_command(context=context)
        return 'available'
    except ComponentError as error:
        return error.code


def _extract(archive, stage, manifest, cancelled):
    expected = {item['path']: item for item in manifest['files']}
    with ZipFile(archive) as bundle:
        infos = bundle.infolist()
        if len(infos) != len(expected):
            raise ComponentError('integrity_error')
        seen = set()
        for info in infos:
            name = str(_relative(info.filename))
            mode = info.external_attr >> 16
            if (name not in expected or name.casefold() in seen or info.is_dir()
                    or info.flag_bits & 1 or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                    or info.file_size != expected[name]['size']):
                raise ComponentError('integrity_error')
            seen.add(name.casefold())
        for info in infos:
            _cancelled(cancelled)
            destination = stage / info.filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            _no_links(destination)
            total = 0
            with bundle.open(info) as source, destination.open('xb') as output:
                while chunk := source.read(1024 * 1024):
                    _cancelled(cancelled)
                    total += len(chunk)
                    if total > expected[info.filename]['size']:
                        raise ComponentError('integrity_error')
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())


def probe_matches(value, manifest):
    return (isinstance(value, dict) and value.get('status') == 'available'
            and value.get('frozen') is True and value.get('component') == 'sorth-mcp'
            and all(value.get(key) == manifest[key] for key in
                    ('version', 'source_commit', 'build_id', 'sdk_version')))


def _probe(directory, manifest, cancelled):
    """A fixed local health command, with bounded output and cancellable lifetime."""
    environment = {key: value for key, value in os.environ.items()
                   if key not in {'PYTHONHOME', 'PYTHONPATH'}}
    environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    command = [str(directory / manifest['entrypoint']), '--probe']
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, env=environment,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    output = bytearray()
    overflow = threading.Event()

    def read():
        data = process.stdout.read(PROBE_MAX_OUTPUT + 1)
        output.extend(data)
        if len(data) > PROBE_MAX_OUTPUT:
            overflow.set()

    reader = threading.Thread(target=read, daemon=True, name='sorth-mcp-probe')
    reader.start()
    deadline = time.monotonic() + PROBE_TIMEOUT
    try:
        while process.poll() is None:
            _cancelled(cancelled)
            if overflow.is_set() or time.monotonic() >= deadline:
                raise ComponentError('probe_failed')
            time.sleep(0.02)
        reader.join(timeout=1)
        _cancelled(cancelled)
        if (reader.is_alive() or overflow.is_set() or process.returncode != 0
                or not probe_matches(json.loads(output), manifest)):
            raise ComponentError('probe_failed')
    except (ValueError, TypeError):
        raise ComponentError('probe_failed') from None
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        reader.join(timeout=1)
        process.stdout.close()


def prepare_component(*, cancelled=lambda: False, progress=lambda state: None, context=None):
    """Verify, stage, probe, then atomically commit a new immutable version.

    The rename is the commit point. Cancellation before it removes only this
    operation's stage. An existing installed version is never overwritten.
    """
    context = _context(context)
    manifest = context.manifest
    destination = component_install_path(context=context)
    stage = None
    try:
        _cancelled(cancelled)
        _no_links(context.components_root)
        _no_links(destination)
        context.components_root.mkdir(parents=True, exist_ok=True)
        _no_links(context.components_root / 'installation.lock')
        try:
            lock = preferences_lock(context.components_root / 'installation')
            lock.__enter__()
        except OSError:
            raise ComponentError('busy') from None
        try:
            if destination.exists():
                progress('verifying')
                command = installed_command(context=context, cancelled=cancelled)
                progress('checking')
                _probe(destination, manifest, cancelled)
                return {'path': str(destination), 'command': command,
                        'manifest': manifest, 'already_prepared': True}
            archive = context.bundle_dir / manifest['archive']
            if not archive.is_file():
                raise ComponentError('missing_bundle')
            progress('verifying')
            if _digest(archive, manifest['archive_size'], cancelled) != manifest['archive_sha256']:
                raise ComponentError('integrity_error')
            stage = Path(tempfile.mkdtemp(prefix='.prepare-', dir=context.components_root))
            progress('extracting')
            _extract(archive, stage, manifest, cancelled)
            _verify_files(stage, manifest, cancelled, marker=False)
            progress('checking')
            _probe(stage, manifest, cancelled)
            _verify_files(stage, manifest, cancelled, marker=False)
            _cancelled(cancelled)
            with (stage / MARKER).open('xb') as output:
                output.write((json.dumps(manifest, sort_keys=True) + '\n').encode('utf-8'))
                output.flush()
                os.fsync(output.fileno())
            progress('committing')
            _cancelled(cancelled)
            _no_links(destination)
            if destination.exists():
                raise ComponentError('busy')
            stage.rename(destination)
            stage = None
            return {'path': str(destination),
                    'command': [str(destination / manifest['entrypoint']), '--serve'],
                    'manifest': manifest, 'already_prepared': False}
        finally:
            lock.__exit__(None, None, None)
    except ComponentError:
        raise
    except (BadZipFile, ValueError, TypeError):
        raise ComponentError('integrity_error') from None
    except OSError:
        raise ComponentError('io_error') from None
    finally:
        if stage is not None:
            # Only the unique directory created by this operation is removed.
            # A failed cleanup is reported rather than claiming full rollback.
            try:
                _no_links(stage)
                shutil.rmtree(stage)
            except OSError:
                raise ComponentError('cleanup_failed') from None
