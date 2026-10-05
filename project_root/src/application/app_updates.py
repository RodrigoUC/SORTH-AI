"""Opt-in, bounded checks of the one official release feed; never execute code.

GitHub's asset digest checks transfer integrity against metadata obtained over
HTTPS. It is NOT a publisher signature, malware scan, or approval of an unsigned
release. No account, cookies, tokens, session data, or automatic checks are used.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import http.client
import json
import os
from pathlib import Path
import queue
import re
import socket
import ssl
import stat
import sys
import tempfile
import threading
import time
import unicodedata
from urllib.parse import quote, urlsplit

REPOSITORY = 'RodrigoUC/SORTH-AI'
RELEASES_URL = f'https://github.com/{REPOSITORY}/releases'
API_URL = f'https://api.github.com/repos/{REPOSITORY}/releases'
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_INSTALLER_BYTES = 512 * 1024 * 1024
MAX_RELEASE_PAGES = 5
RELEASES_PER_PAGE = 100
NETWORK_TIMEOUT = 10.0
CHECK_DEADLINE = 45.0
DOWNLOAD_DEADLINE = 15 * 60.0
CHUNK_BYTES = 64 * 1024
MAX_REDIRECTS = 3
_STAGE_PREFIX = 'sorth-update-'
_INSTALLER_NAME = 'SORTH-setup.exe'
_VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?')
_INSTALLER = re.compile(r'SORTH-([0-9]+\.[0-9]+\.[0-9]+)-([0-9a-f]{12})-windows-x64-unsigned-setup\.exe')
_DOWNLOADS: dict[Path, tuple['DownloadResult', int, int]] = {}
_DOWNLOADS_LOCK = threading.Lock()


class UpdateError(Exception):
    """Fixed, localizable code; never surface URLs, tokens, or raw OS errors."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class AppIdentity:
    version: str
    build_id: str | None = None
    source_commit: str | None = None


@dataclass(frozen=True)
class InstallerAsset:
    name: str
    url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    title: str
    body: str
    page_url: str
    installer: InstallerAsset | None = None
    installer_issue: str | None = None


@dataclass(frozen=True)
class UpdateResult:
    state: str
    current_version: str
    release: Release | None = None


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    release: Release


def _version(value, code='invalid_version'):
    if not isinstance(value, str) or len(value) > 128:
        raise UpdateError(code)
    match = _VERSION.fullmatch(value)
    if not match:
        raise UpdateError(code)
    return tuple(int(part) for part in match.group(1, 2, 3))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def _json(raw, code):
    def reject_constant(_):
        raise ValueError('non-finite JSON value')

    try:
        return json.loads(raw, object_pairs_hook=_unique_object,
                          parse_constant=reject_constant)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise UpdateError(code) from None


def current_identity():
    """Read the packaged identity, or VERSION in source; never guess a fallback."""
    try:
        if getattr(sys, 'frozen', False):
            root = Path(sys._MEIPASS)
            with (root / 'build-identity.json').open('rb') as source:
                raw = source.read(8193)
            if len(raw) > 8192:
                raise UpdateError('invalid_identity')
            data = _json(raw, 'invalid_identity')
            version = data['version']
            _version(version, 'invalid_identity')
            commit = data['source_commit']
            if (not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit)
                    or data['build_id'] != f'{version}-{commit[:12]}'):
                raise UpdateError('invalid_identity')
            return AppIdentity(version, data['build_id'], commit)
        with (Path(__file__).resolve().parents[2] / 'VERSION').open('rb') as source:
            raw = source.read(129)
        if len(raw) > 128:
            raise UpdateError('invalid_identity')
        version = raw.decode('ascii').strip()
        _version(version, 'invalid_identity')
        return AppIdentity(version)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise UpdateError('invalid_identity') from None


def current_app_version():
    return current_identity().version


def _check(cancelled, deadline):
    if cancelled():
        raise UpdateError('cancelled')
    if time.monotonic() >= deadline:
        raise UpdateError('timeout')


def _url_parts(url):
    if (not isinstance(url, str) or not url or len(url) > 8192
            or any(ord(char) <= 32 or ord(char) >= 127 for char in url)
            or '\\' in url):
        raise UpdateError('invalid_url')
    try:
        parts = urlsplit(url)
        if (parts.scheme != 'https' or parts.username is not None
                or parts.password is not None or parts.port is not None
                or parts.fragment or not parts.hostname
                or parts.netloc != parts.hostname):
            raise UpdateError('invalid_url')
        return parts
    except ValueError:
        raise UpdateError('invalid_url') from None


def _release_path(tag, suffix):
    return {f'/{REPOSITORY}/releases/{suffix}/{tag}',
            f'/{REPOSITORY}/releases/{suffix}/{quote(tag, safe="")}'}


def _validate_page(url, tag):
    parts = _url_parts(url)
    if (parts.hostname != 'github.com' or parts.query
            or parts.path not in _release_path(tag, 'tag')):
        raise UpdateError('invalid_url')


def _validate_asset(asset, tag, version):
    if not isinstance(asset, InstallerAsset):
        raise UpdateError('invalid_asset')
    match = _INSTALLER.fullmatch(asset.name) if isinstance(asset.name, str) else None
    if (not match or _version(match[1], 'invalid_asset') != _version(version, 'invalid_asset')
            or type(asset.size) is not int or not 0 < asset.size <= MAX_INSTALLER_BYTES
            or not isinstance(asset.sha256, str)
            or not re.fullmatch('[0-9a-f]{64}', asset.sha256)):
        raise UpdateError('invalid_asset')
    parts = _url_parts(asset.url)
    paths = {path + '/' + asset.name for path in _release_path(tag, 'download')}
    if parts.hostname != 'github.com' or parts.query or parts.path not in paths:
        raise UpdateError('invalid_url')


def _validate_request(url, *, metadata, initial_url):
    parts = _url_parts(url)
    if metadata:
        # API redirects are not followed, including repository transfers.
        if url != initial_url or not re.fullmatch(
                re.escape(API_URL) + r'\?per_page=100&page=[1-5]', url):
            raise UpdateError('invalid_url')
    elif url != initial_url:
        # Only official GitHub asset storage, never arbitrary *.githubusercontent
        # or attacker-owned GitHub pages/repos. Signed CDN queries stay in memory.
        if (parts.hostname not in {'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
                or not re.fullmatch(r'/github-production-release-asset(?:-2e65be)?/[0-9]+/[0-9a-fA-F-]+', parts.path)):
            raise UpdateError('invalid_url')
    elif parts.hostname != 'github.com':
        raise UpdateError('invalid_url')
    return parts


def _header(response, name):
    values = [value for key, value in response.getheaders() if key.lower() == name.lower()]
    if len(values) > 1:
        raise UpdateError('invalid_response')
    return values[0] if values else None


def _pump(url, metadata, limit, deadline, stopped, events, connection):
    """Transport-only daemon: never touches disk or user state.

    The caller bounds DNS, TLS, response headers and slow-drip reads together.
    Cancellation closes the active socket. A platform DNS lookup that cannot be
    interrupted may finish later, but the stopped flag prevents a later request.
    """
    def put(kind, value=None):
        while not stopped.is_set():
            try:
                events.put((kind, value), timeout=.05)
                return
            except queue.Full:
                continue

    initial_url = url
    try:
        for hop in range(MAX_REDIRECTS + 1):
            _check(stopped.is_set, deadline)
            parts = _validate_request(url, metadata=metadata, initial_url=initial_url)
            conn = http.client.HTTPSConnection(parts.hostname,
                timeout=min(NETWORK_TIMEOUT, max(.001, deadline - time.monotonic())),
                context=ssl.create_default_context())
            try:
                conn.connect()
                # Keep the socket even if HTTPConnection detaches it for a
                # Connection: close response. Only this worker owns close().
                connection.append(conn.sock)
                _check(stopped.is_set, deadline)
                # Once cancelled/closed, http.client must not reopen a socket
                # from request() and send a late request automatically.
                conn.auto_open = 0
                headers = {'User-Agent': 'SORTH-update-check', 'Accept-Encoding': 'identity',
                           'Accept': 'application/vnd.github+json' if metadata else 'application/octet-stream'}
                if metadata:
                    headers['X-GitHub-Api-Version'] = '2022-11-28'
                target = parts.path + ('?' + parts.query if parts.query else '')
                conn.request('GET', target, headers=headers)
                response = conn.getresponse()
                _check(stopped.is_set, deadline)
                if response.status in {301, 302, 303, 307, 308}:
                    location = _header(response, 'Location')
                    if metadata or hop == MAX_REDIRECTS or not location:
                        raise UpdateError('invalid_url')
                    _validate_request(location, metadata=False, initial_url=initial_url)
                    url = location
                    continue
                if response.status in {403, 429}:
                    raise UpdateError('rate_limited')
                if response.status != 200:
                    raise UpdateError('network_error')
                encoding = _header(response, 'Content-Encoding')
                if encoding not in {None, 'identity'}:
                    raise UpdateError('invalid_response')
                length = _header(response, 'Content-Length')
                transfer = _header(response, 'Transfer-Encoding')
                if transfer not in {None, 'chunked'} or (transfer is not None and length is not None):
                    raise UpdateError('invalid_response')
                if length is not None:
                    if not re.fullmatch('[0-9]{1,12}', length):
                        raise UpdateError('invalid_response')
                    length = int(length)
                    if length > limit:
                        raise UpdateError('size_limit')
                    if not metadata and length != limit:
                        raise UpdateError('integrity_error')
                if metadata:
                    content_type = _header(response, 'Content-Type') or ''
                    if content_type.split(';', 1)[0].strip() not in {
                            'application/json', 'application/vnd.github+json'}:
                        raise UpdateError('invalid_response')
                total = 0
                while True:
                    _check(stopped.is_set, deadline)
                    connection[-1].settimeout(min(NETWORK_TIMEOUT, max(.001, deadline - time.monotonic())))
                    chunk = response.read1(min(CHUNK_BYTES, limit - total + 1))
                    _check(stopped.is_set, deadline)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > limit:
                        raise UpdateError('size_limit')
                    put('data', chunk)
                if length is not None and total != length:
                    raise UpdateError('integrity_error')
                put('done')
                return
            finally:
                conn.close()
    except UpdateError as error:
        put('error', error)
    except (TimeoutError, socket.timeout):
        put('error', UpdateError('timeout'))
    except (OSError, http.client.HTTPException, ValueError, AttributeError):
        put('error', UpdateError('network_error'))


def _stream(url, *, metadata, limit, cancelled, deadline):
    _check(cancelled, deadline)
    _validate_request(url, metadata=metadata, initial_url=url)
    events = queue.Queue(maxsize=4)
    stopped = threading.Event()
    connection = []
    worker = threading.Thread(target=_pump,
        args=(url, metadata, limit, deadline, stopped, events, connection), daemon=True,
        name='sorth-update-transport')
    worker.start()
    try:
        while True:
            _check(cancelled, deadline)
            try:
                kind, value = events.get(timeout=min(.05, max(.001, deadline - time.monotonic())))
            except queue.Empty:
                continue
            _check(cancelled, deadline)
            if kind == 'error':
                raise value
            if kind == 'done':
                return
            yield value
    finally:
        stopped.set()
        # shutdown interrupts blocked TLS/header/body reads without waiting for
        # their per-read timeout; never join an uninterruptible OS DNS operation.
        for sock in connection:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                continue


def _text(value, *, maximum, default=''):
    if value is None:
        return default
    if not isinstance(value, str):
        raise UpdateError('invalid_metadata')
    # UI must still use plain-text rendering. Retain line breaks, not controls.
    return ''.join(char for char in value[:maximum]
                   if not unicodedata.category(char).startswith('C') or char in '\n\t')


def _parse_release(data):
    if not isinstance(data, dict) or type(data.get('draft')) is not bool or type(data.get('prerelease')) is not bool:
        raise UpdateError('invalid_metadata')
    if data['draft'] or data['prerelease']:
        return None
    tag = data.get('tag_name')
    if not isinstance(tag, str):
        raise UpdateError('invalid_metadata')
    version = tag[1:] if tag.startswith('v') else tag
    try:
        _version(version)
    except UpdateError:
        # Non-semantic tags and semantic prereleases are never update candidates.
        return None
    page = data.get('html_url')
    _validate_page(page, tag)
    assets = data.get('assets')
    if not isinstance(assets, list) or len(assets) > 100:
        raise UpdateError('invalid_metadata')
    candidates = [item for item in assets if isinstance(item, dict)
                  and isinstance(item.get('name'), str) and _INSTALLER.fullmatch(item['name'])]
    installer = None
    issue = 'missing_installer'
    if len(candidates) > 1:
        issue = 'ambiguous_installer'
    elif len(candidates) == 1:
        item = candidates[0]
        digest = item.get('digest')
        if not isinstance(digest, str) or not re.fullmatch('sha256:[0-9a-f]{64}', digest):
            issue = 'missing_digest'
        else:
            asset = InstallerAsset(item['name'], item.get('browser_download_url'), item.get('size'), digest[7:])
            try:
                if item.get('state') != 'uploaded':
                    raise UpdateError('invalid_asset')
                _validate_asset(asset, tag, version)
                installer, issue = asset, None
            except UpdateError:
                issue = 'invalid_asset'
    return Release(version, tag, _text(data.get('name'), maximum=200, default=tag),
                   _text(data.get('body'), maximum=16000), page, installer, issue)


def check_updates(current_version, *, cancelled=lambda: False):
    """Check all bounded public pages; empty/no-stable is not 'up to date'."""
    current = _version(current_version)
    deadline = time.monotonic() + CHECK_DEADLINE
    latest = None
    for page in range(1, MAX_RELEASE_PAGES + 1):
        raw = b''.join(_stream(f'{API_URL}?per_page=100&page={page}', metadata=True,
                              limit=MAX_METADATA_BYTES, cancelled=cancelled, deadline=deadline))
        data = _json(raw, 'invalid_metadata')
        if not isinstance(data, list) or len(data) > RELEASES_PER_PAGE:
            raise UpdateError('invalid_metadata')
        for item in data:
            _check(cancelled, deadline)
            release = _parse_release(item)
            if release and (latest is None or _version(release.version) > _version(latest.version)):
                latest = release
        if len(data) < RELEASES_PER_PAGE:
            break
    else:
        # Do not misreport a partial feed as current when the bounded scan fills.
        raise UpdateError('metadata_limit')
    _check(cancelled, deadline)
    if latest is None:
        return UpdateResult('no_releases', current_version)
    return UpdateResult('available' if _version(latest.version) > current else 'current', current_version, latest)


def _no_links(path):
    for candidate in (path, *path.parents):
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise UpdateError('integrity_error')


def _release_asset(release):
    if not isinstance(release, Release) or release.installer is None:
        raise UpdateError('installer_unavailable')
    if not isinstance(release.tag, str):
        raise UpdateError('invalid_asset')
    version = release.tag[1:] if release.tag.startswith('v') else release.tag
    if version != release.version:
        raise UpdateError('invalid_asset')
    _validate_page(release.page_url, release.tag)
    _validate_asset(release.installer, release.tag, release.version)
    return release.installer


def _remove_stage(stage, identity):
    """Only the two fixed filenames in this exact owned directory; no recursion."""
    try:
        _no_links(stage)
        info = stage.stat()
        if (info.st_dev, info.st_ino) != identity:
            return
        for name in (_INSTALLER_NAME, _INSTALLER_NAME + '.part'):
            path = stage / name
            # unlink removes a replaced symlink itself, never its target.
            try:
                path.unlink()
            except FileNotFoundError:
                continue
        stage.rmdir()
    except (OSError, UpdateError):
        return


def download_installer(release, *, cancelled=lambda: False, progress=lambda received, total: None):
    """Stage an exact-size, digest-verified executable, without launching it."""
    asset = _release_asset(release)
    deadline = time.monotonic() + DOWNLOAD_DEADLINE
    _check(cancelled, deadline)
    stage = None
    identity = None
    try:
        root = Path(tempfile.gettempdir()).resolve()
        _no_links(root)
        stage = Path(tempfile.mkdtemp(prefix=_STAGE_PREFIX, dir=root))
        _no_links(stage)
        info = stage.stat()
        identity = info.st_dev, info.st_ino
        part, final = stage / (_INSTALLER_NAME + '.part'), stage / _INSTALLER_NAME
        digest, total, last_percent = hashlib.sha256(), 0, 0
        progress(0, asset.size)
        with part.open('xb') as output:
            for chunk in _stream(asset.url, metadata=False, limit=asset.size,
                                 cancelled=cancelled, deadline=deadline):
                _check(cancelled, deadline)
                total += len(chunk)
                if total > asset.size:
                    raise UpdateError('size_limit')
                digest.update(chunk)
                output.write(chunk)
                percent = total * 100 // asset.size
                if percent != last_percent:
                    progress(total, asset.size)
                    last_percent = percent
            output.flush()
            os.fsync(output.fileno())
        _check(cancelled, deadline)
        if total != asset.size or digest.hexdigest() != asset.sha256:
            raise UpdateError('integrity_error')
        _no_links(part)
        if part.stat().st_nlink != 1:
            raise UpdateError('integrity_error')
        os.replace(part, final)
        result = DownloadResult(final, release)
        with _DOWNLOADS_LOCK:
            _DOWNLOADS[final] = (result, *identity)
        try:
            verify_download(result, cancelled=cancelled)
        except BaseException:
            discard_download(result)
            raise
        return result
    except OSError:
        raise UpdateError('storage_error') from None
    finally:
        if stage is not None and identity is not None:
            with _DOWNLOADS_LOCK:
                registered = stage / _INSTALLER_NAME in _DOWNLOADS
            if not registered:
                _remove_stage(stage, identity)


def _registered(download):
    if not isinstance(download, DownloadResult) or not isinstance(download.path, Path):
        raise UpdateError('integrity_error')
    with _DOWNLOADS_LOCK:
        record = _DOWNLOADS.get(download.path)
    if record is None or record[0] != download:
        raise UpdateError('integrity_error')
    return record[1:]


def verify_download(download, *, cancelled=lambda: False):
    """Rehash this process's staged file immediately before a separate launch."""
    identity = _registered(download)
    asset = _release_asset(download.release)
    deadline = time.monotonic() + CHECK_DEADLINE
    _check(cancelled, deadline)
    try:
        path = download.path
        _no_links(path)
        parent = path.parent.stat()
        info = path.stat()
        if ((parent.st_dev, parent.st_ino) != identity or not stat.S_ISREG(info.st_mode)
                or info.st_size != asset.size or info.st_nlink != 1):
            raise UpdateError('integrity_error')
        digest, total = hashlib.sha256(), 0
        with path.open('rb') as source:
            opened = os.fstat(source.fileno())
            if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                raise UpdateError('integrity_error')
            while chunk := source.read(CHUNK_BYTES):
                _check(cancelled, deadline)
                total += len(chunk)
                if total > asset.size:
                    raise UpdateError('integrity_error')
                digest.update(chunk)
        _check(cancelled, deadline)
        _no_links(path)
        after = path.stat()
        if (total != asset.size or digest.hexdigest() != asset.sha256
                or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)):
            raise UpdateError('integrity_error')
        return path
    except OSError:
        raise UpdateError('integrity_error') from None


def discard_download(download):
    """Forget and best-effort remove only an exact download owned by this process."""
    try:
        identity = _registered(download)
    except UpdateError:
        return
    with _DOWNLOADS_LOCK:
        _DOWNLOADS.pop(download.path, None)
    _remove_stage(download.path.parent, identity)
