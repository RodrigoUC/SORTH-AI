"""Synthetic HTTP/installer fixtures only: no network, executables, or user data."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import ssl
import sys
import threading
import time

import pytest

from src.application import app_updates as updates

PAYLOAD = b'MZ\x00SORTH synthetic installer, never executed\x00'
SHA256 = hashlib.sha256(PAYLOAD).hexdigest()
CDN_URL = 'https://release-assets.githubusercontent.com/github-production-release-asset/123/abcdef-1234?token=synthetic'


def metadata(version='2.1.0', **changes):
    tag = 'v' + version
    name = f'SORTH-{version}-abcdef123456-windows-x64-unsigned-setup.exe'
    record = {'tag_name': tag, 'name': 'Synthetic release ' + version, 'body': 'Synthetic release notes',
              'html_url': updates.RELEASES_URL + '/tag/' + tag,
              'draft': False, 'prerelease': False,
              'assets': [{'name': name, 'size': len(PAYLOAD), 'digest': 'sha256:' + SHA256,
                          'state': 'uploaded', 'browser_download_url':
                          updates.RELEASES_URL + '/download/' + tag + '/' + name}]}
    record.update(changes)
    return record


def release():
    return updates._parse_release(metadata())


class Response:
    def __init__(self, data=b'', *, status=200, headers=None, content_type='application/json',
                 chunks=None, read_hook=None):
        self.status, self.data = status, data
        self.headers = [('Content-Type', content_type)] if content_type else []
        self.headers += list(headers or [])
        self.chunks = list(chunks) if chunks is not None else None
        self.read_hook = read_hook

    def getheaders(self):
        return self.headers

    def read1(self, size):
        if self.read_hook:
            self.read_hook()
        if self.chunks is not None:
            return self.chunks.pop(0) if self.chunks else b''
        result, self.data = self.data[:size], self.data[size:]
        return result


def json_response(value, **kwargs):
    return Response(json.dumps(value).encode('utf-8'), **kwargs)


@pytest.fixture
def network(monkeypatch, tmp_path):
    """Every socket is synthetic; preserve the full real validation pipeline."""
    responses, requests, connections, hooks = [], [], [], {}

    class Socket:
        def settimeout(self, timeout):
            assert 0 < timeout <= updates.NETWORK_TIMEOUT

        def shutdown(self, how):
            assert how == socket.SHUT_RDWR
            hooks.get('shutdown', lambda: None)()

    class Connection:
        def __init__(self, host, *, timeout, context):
            assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
            self.host, self.timeout, self.sock, self.closed = host, timeout, Socket(), False
            connections.append(self)

        def connect(self):
            hooks.get('connect', lambda: None)()

        def request(self, method, path, *, headers):
            requests.append((self.host, method, path, headers.copy()))

        def getresponse(self):
            hooks.get('headers', lambda: None)()
            if not responses:
                raise AssertionError('Unexpected HTTP request')
            value = responses.pop(0)
            if isinstance(value, Exception):
                raise value
            return value

        def close(self):
            self.closed = True

    monkeypatch.setattr(updates.http.client, 'HTTPSConnection', Connection)
    monkeypatch.setattr(updates.tempfile, 'gettempdir', lambda: str(tmp_path))
    yield responses, requests, connections, hooks
    for record in list(updates._DOWNLOADS.values()):
        updates.discard_download(record[0])


def test_source_identity_uses_version_file_without_network(network):
    value = updates.current_identity()
    assert value.version == (Path(updates.__file__).resolve().parents[2] / 'VERSION').read_text().strip()
    assert value.build_id is None and value.source_commit is None
    assert updates.current_app_version() == value.version
    assert not network[1]


def test_frozen_identity_includes_exact_build(tmp_path, monkeypatch):
    info = {'version': '2.0.0', 'source_commit': 'a' * 40, 'build_id': '2.0.0-' + 'a' * 12}
    (tmp_path / 'build-identity.json').write_text(json.dumps(info))
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    assert updates.current_identity() == updates.AppIdentity('2.0.0', info['build_id'], info['source_commit'])


@pytest.mark.parametrize('raw', [b'{}', b'[]', b'invalid', b'x' * 8193,
    b'{"version":"2.0.0","version":"3.0.0"}',
    json.dumps({'version': '2.0.0', 'source_commit': 'b' * 40, 'build_id': '2.0.0-' + 'a' * 12}).encode(),
    json.dumps({'version': 'bad', 'source_commit': 'a' * 40, 'build_id': 'bad-' + 'a' * 12}).encode(),
    json.dumps({'version': '2.0.0', 'source_commit': None, 'build_id': '2.0.0'}).encode()])
def test_corrupt_frozen_identity_never_guesses_source_version(raw, tmp_path, monkeypatch):
    (tmp_path / 'build-identity.json').write_bytes(raw)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    with pytest.raises(updates.UpdateError, match='invalid_identity'):
        updates.current_identity()


def test_missing_frozen_identity_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    with pytest.raises(updates.UpdateError, match='invalid_identity'):
        updates.current_identity()


@pytest.mark.parametrize('current', ['2.0.0', '2.0.0+build.7'])
def test_empty_releases_truthful_and_no_credentials_sent(network, monkeypatch, current):
    monkeypatch.setenv('GITHUB_TOKEN', 'must-never-leak')
    monkeypatch.setenv('HTTPS_PROXY', 'https://must-not-be-used.invalid')
    network[0].append(json_response([]))
    assert updates.check_updates(current) == updates.UpdateResult('no_releases', current)
    assert len(network[1]) == 1
    host, method, path, headers = network[1][0]
    assert (host, method, path) == ('api.github.com', 'GET', '/repos/RodrigoUC/SORTH-AI/releases?per_page=100&page=1')
    assert headers == {'User-Agent': 'SORTH-update-check', 'Accept-Encoding': 'identity',
                       'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    assert all(connection.closed for connection in network[2])


@pytest.mark.parametrize('value', ['2.0', 'v2.0.0', '2.0.0-dev', '2.0.0-abcdef123456', '02.0.0',
                                 '2.0.0+', '2.0.0+bad..id', '2.0.0\n', '', None, 2, '9' * 129])
def test_invalid_current_version_fails_before_network(network, value):
    with pytest.raises(updates.UpdateError, match='invalid_version'):
        updates.check_updates(value)
    assert not network[1]


def test_numeric_semantic_order_beats_lexical_and_api_order(network):
    network[0].append(json_response([metadata('2.9.0'), metadata('2.10.0'), metadata('2.3.0')]))
    result = updates.check_updates('2.8.0')
    assert result.state == 'available' and result.release.version == '2.10.0'
    assert result.release.installer.sha256 == SHA256


@pytest.mark.parametrize('current', ['2.1.0', '2.2.0', '2.1.0+local.123'])
def test_equal_and_older_are_never_offered(network, current):
    network[0].append(json_response([metadata()]))
    assert updates.check_updates(current).state == 'current'


@pytest.mark.parametrize('record', [metadata('3.0.0', draft=True), metadata('3.0.0', prerelease=True),
                                    metadata('3.0.0-rc.1'), metadata('preview'), metadata('03.0.0')])
def test_drafts_prereleases_and_nonsemantic_tags_are_ignored(network, record):
    network[0].append(json_response([record]))
    assert updates.check_updates('2.0.0').state == 'no_releases'


def test_build_metadata_does_not_change_version_precedence(network):
    value = metadata('2.0.0+release.7', assets=[])
    network[0].append(json_response([value]))
    assert updates.check_updates('2.0.0+local.2').state == 'current'


def test_pagination_checks_every_page_including_out_of_order_older_publication(network):
    network[0].extend([json_response([metadata('2.0.0') for _ in range(100)]), json_response([metadata('3.0.0')])])
    assert updates.check_updates('2.0.0').release.version == '3.0.0'
    assert len(network[1]) == 2 and network[1][-1][2].endswith('page=2')


def test_full_bounded_scan_is_not_falsely_reported_current(network):
    network[0].extend(json_response([metadata('2.0.0') for _ in range(100)]) for _ in range(5))
    with pytest.raises(updates.UpdateError, match='metadata_limit'):
        updates.check_updates('2.0.0')
    assert len(network[1]) == 5


@pytest.mark.parametrize('raw', [b'{}', b'null', b'NaN', b'[] trailing', b'\xff',
    b'[{"draft":false,"draft":true}]', b'[' * 2000 + b']' * 2000,
    json.dumps([metadata(draft='false')]).encode(), json.dumps([metadata(prerelease=0)]).encode(),
    json.dumps([metadata(assets={})]).encode(), json.dumps([None]).encode(),
    json.dumps([metadata('2.0.0') for _ in range(101)]).encode()])
def test_malformed_metadata_is_not_treated_as_no_updates(network, raw):
    network[0].append(Response(raw))
    with pytest.raises(updates.UpdateError, match='invalid_metadata'):
        updates.check_updates('2.0.0')


@pytest.mark.parametrize('url', [
    'http://github.com/RodrigoUC/SORTH-AI/releases/tag/v2.1.0',
    'https://github.com.evil.invalid/RodrigoUC/SORTH-AI/releases/tag/v2.1.0',
    'https://github.com@evil.invalid/RodrigoUC/SORTH-AI/releases/tag/v2.1.0',
    'https://github.com:443/RodrigoUC/SORTH-AI/releases/tag/v2.1.0',
    'https://github.com/attacker/SORTH-AI/releases/tag/v2.1.0',
    'https://github.com/RodrigoUC/SORTH-AI/releases/tag/v2.1.0?extra=1',
    'https://github.com/RodrigoUC/SORTH-AI/releases/tag/v2.1.0#fragment',
    'https://github.com/RodrigoUC/SORTH-AI/releases/tag/%2e%2e',
    'https://github.com\\@evil.invalid/path', '//github.com/path', 'https://github.com/\npath', None,
])
def test_malicious_release_page_never_reaches_ui(network, url):
    network[0].append(json_response([metadata(html_url=url)]))
    with pytest.raises(updates.UpdateError, match='invalid_url'):
        updates.check_updates('2.0.0')


def test_release_notes_are_bounded_text(network):
    network[0].append(json_response([metadata(name='<b>HTML</b>\x00\u202e' + 'x' * 400,
                                            body='<script>no execution</script>\x01\u2066\n' + 'x' * 20000)]))
    value = updates.check_updates('2.0.0').release
    assert len(value.title) <= 200 and '\x00' not in value.title and '\u202e' not in value.title
    assert len(value.body) <= 16000 and '\x01' not in value.body and '\u2066' not in value.body
    assert '<script>' in value.body and '\n' in value.body  # UI must render plain text


@pytest.mark.parametrize(('changes', 'issue'), [
    ({'digest': None}, 'missing_digest'), ({'digest': 'sha256:' + 'z' * 64}, 'missing_digest'),
    ({'digest': 'md5:' + 'a' * 32}, 'missing_digest'), ({'digest': 'SHA256:' + SHA256}, 'missing_digest'),
    ({'size': 0}, 'invalid_asset'), ({'size': -1}, 'invalid_asset'), ({'size': True}, 'invalid_asset'),
    ({'size': updates.MAX_INSTALLER_BYTES + 1}, 'invalid_asset'), ({'size': '12'}, 'invalid_asset'),
    ({'state': 'new'}, 'invalid_asset'), ({'browser_download_url': 'https://evil.invalid/x.exe'}, 'invalid_asset'),
    ({'name': 'SORTH-2.2.0-abcdef123456-windows-x64-unsigned-setup.exe'}, 'invalid_asset'),
])
def test_unverifiable_asset_preserves_release_but_disables_download(network, changes, issue):
    value = metadata()
    value['assets'][0].update(changes)
    network[0].append(json_response([value]))
    result = updates.check_updates('2.0.0')
    assert result.state == 'available' and result.release.installer is None
    assert result.release.installer_issue == issue
    with pytest.raises(updates.UpdateError, match='installer_unavailable'):
        updates.download_installer(result.release)
    assert len(network[1]) == 1


@pytest.mark.parametrize('filename', ['setup.exe', '../setup.exe', 'C:\\setup.exe',
    'SORTH-2.1.0-abcdef123456-windows-x64-unsigned-setup.exe.zip',
    'SORTH-2.1.0-abcdef123456-windows-arm64-unsigned-setup.exe',
    'SORTH-2.1.0-abcdef123456-windows-x64-unsigned-setup.exe:evil'])
def test_only_exact_packaging_filename_is_accepted(network, filename):
    value = metadata()
    value['assets'][0]['name'] = filename
    network[0].append(json_response([value]))
    assert updates.check_updates('2.0.0').release.installer_issue == 'missing_installer'


def test_multiple_installers_are_ambiguous_without_guessing(network):
    value = metadata()
    value['assets'] += value['assets']
    network[0].append(json_response([value]))
    assert updates.check_updates('2.0.0').release.installer_issue == 'ambiguous_installer'


@pytest.mark.parametrize('status,code', [(403, 'rate_limited'), (429, 'rate_limited'),
                                      (404, 'network_error'), (500, 'network_error'), (206, 'network_error')])
def test_http_errors_have_safe_fixed_codes(network, status, code):
    network[0].append(Response(b'private error diagnostics', status=status))
    with pytest.raises(updates.UpdateError, match=code):
        updates.check_updates('2.0.0')


def test_metadata_redirect_rejected_even_to_github(network):
    network[0].append(Response(status=302, headers=[('Location', updates.API_URL + '?per_page=100&page=2')]))
    with pytest.raises(updates.UpdateError, match='invalid_url'):
        updates.check_updates('2.0.0')
    assert len(network[1]) == 1


@pytest.mark.parametrize('headers', [[('Content-Length', '999999999')],
    [('Content-Length', '3'), ('Content-Length', '3')], [('Content-Length', '-1')], [('Content-Encoding', 'gzip')]])
def test_invalid_or_oversize_response_headers_fail_closed(network, headers):
    network[0].append(Response(b'[]', headers=headers))
    with pytest.raises(updates.UpdateError, match='size_limit|invalid_response'):
        updates.check_updates('2.0.0')


def test_html_metadata_is_not_accepted(network):
    network[0].append(Response(b'[]', content_type='text/html'))
    with pytest.raises(updates.UpdateError, match='invalid_response'):
        updates.check_updates('2.0.0')


def test_metadata_limit_applies_to_chunked_response(network, monkeypatch):
    monkeypatch.setattr(updates, 'MAX_METADATA_BYTES', 10)
    network[0].append(Response(chunks=[b' ' * 6, b' ' * 6]))
    with pytest.raises(updates.UpdateError, match='size_limit'):
        updates.check_updates('2.0.0')


def test_truncated_content_length_fails(network):
    network[0].append(Response(b'[]', headers=[('Content-Length', '10')]))
    with pytest.raises(updates.UpdateError, match='integrity_error'):
        updates.check_updates('2.0.0')


@pytest.mark.parametrize('error,code', [(OSError('secret'), 'network_error'), (TimeoutError('secret'), 'timeout')])
def test_network_errors_do_not_expose_raw_messages(network, error, code):
    network[0].append(error)
    with pytest.raises(updates.UpdateError) as found:
        updates.check_updates('2.0.0')
    assert str(found.value) == code


@pytest.mark.parametrize('operation', ['check', 'download'])
def test_cancel_before_start_sends_nothing_and_writes_nothing(network, tmp_path, operation):
    with pytest.raises(updates.UpdateError, match='cancelled'):
        if operation == 'check':
            updates.check_updates('2.0.0', cancelled=lambda: True)
        else:
            updates.download_installer(release(), cancelled=lambda: True)
    assert not network[1] and not list(tmp_path.iterdir())


@pytest.mark.parametrize('blocked_step', ['connect', 'headers', 'body'])
def test_absolute_deadline_bounds_dns_headers_and_body(network, monkeypatch, blocked_step):
    gate, finished = threading.Event(), threading.Event()
    def stalled():
        gate.wait(3)
        finished.set()
    if blocked_step == 'body':
        network[0].append(Response(b'[]', read_hook=stalled))
    else:
        network[3][blocked_step] = stalled
        network[0].append(Response(b'[]'))
    monkeypatch.setattr(updates, 'CHECK_DEADLINE', .06)
    started = time.monotonic()
    try:
        with pytest.raises(updates.UpdateError, match='timeout'):
            updates.check_updates('2.0.0')
        assert time.monotonic() - started < 1
    finally:
        gate.set()
        assert finished.wait(1)
    if blocked_step == 'connect':
        time.sleep(.03)
        assert not network[1]


def test_cancel_interrupts_stalled_body_without_waiting_for_network_timeout(network):
    started, gate, cancelled = threading.Event(), threading.Event(), threading.Event()
    def stalled():
        started.set()
        gate.wait(3)
    network[0].append(Response(b'[]', read_hook=stalled))
    def cancel():
        started.wait(1)
        cancelled.set()
    timer = threading.Thread(target=cancel)
    timer.start()
    before = time.monotonic()
    try:
        with pytest.raises(updates.UpdateError, match='cancelled'):
            updates.check_updates('2.0.0', cancelled=cancelled.is_set)
        assert time.monotonic() - before < 1
    finally:
        gate.set()
        timer.join(1)


def test_verified_download_is_atomic_private_fixed_path_and_rehashable(network, tmp_path):
    network[0].extend([Response(status=302, headers=[('Location', CDN_URL), ('Set-Cookie', 'secret=never-forward')]),
                       Response(PAYLOAD, content_type='application/octet-stream',
                                headers=[('Content-Length', str(len(PAYLOAD)))])])
    observations = []
    def progress(count, total):
        observations.append((count, total))
        assert not list(tmp_path.rglob('SORTH-setup.exe'))
    result = updates.download_installer(release(), progress=progress)
    assert result.path.name == 'SORTH-setup.exe' and result.path.parent.parent == tmp_path
    assert result.path.parent.name.startswith('sorth-update-') and result.path.read_bytes() == PAYLOAD
    assert not list(tmp_path.rglob('*.part'))
    assert observations == [(0, len(PAYLOAD)), (len(PAYLOAD), len(PAYLOAD))]
    assert updates.verify_download(result) == result.path
    assert [call[0] for call in network[1]] == ['github.com', 'release-assets.githubusercontent.com']
    assert all('Cookie' not in call[3] and 'Authorization' not in call[3] for call in network[1])
    updates.discard_download(result)
    assert not result.path.parent.exists()
    updates.discard_download(result)


@pytest.mark.parametrize('location', ['http://release-assets.githubusercontent.com/github-production-release-asset/1/a',
    'https://evil.invalid/setup.exe', 'https://github.com/attacker/repo/releases/download/v2.1.0/setup.exe',
    'https://release-assets.githubusercontent.com.evil.invalid/github-production-release-asset/1/a',
    'https://release-assets.githubusercontent.com@evil.invalid/github-production-release-asset/1/a',
    'https://release-assets.githubusercontent.com:443/github-production-release-asset/1/a',
    'https://release-assets.githubusercontent.com/github-production-release-asset/../a',
    'https://release-assets.githubusercontent.com/arbitrary/path',
    'https://raw.githubusercontent.com/attacker/repo/setup.exe', '//evil.invalid/setup.exe',
    'file:///tmp/setup.exe', 'https://127.0.0.1/setup.exe', 'https://[::1]/setup.exe',
    '/relative-redirect', 'https://release-assets.githubusercontent.com/github-production-release-asset/1/a#fragment'])
def test_malicious_redirect_never_contacted_and_stage_removed(network, tmp_path, location):
    network[0].append(Response(status=302, headers=[('Location', location)]))
    with pytest.raises(updates.UpdateError, match='invalid_url'):
        updates.download_installer(release())
    assert len(network[1]) == 1 and not list(tmp_path.iterdir())


def test_redirect_chain_is_bounded(network, tmp_path):
    network[0].extend(Response(status=302, headers=[('Location', CDN_URL)]) for _ in range(5))
    with pytest.raises(updates.UpdateError, match='invalid_url'):
        updates.download_installer(release())
    assert len(network[1]) == updates.MAX_REDIRECTS + 1 and not list(tmp_path.iterdir())


@pytest.mark.parametrize('payload', [PAYLOAD[:-1], PAYLOAD + b'extra', b'x' * len(PAYLOAD)])
def test_wrong_size_or_digest_never_leaves_executable(network, tmp_path, payload):
    network[0].append(Response(payload, content_type='application/octet-stream'))
    with pytest.raises(updates.UpdateError, match='integrity_error|size_limit'):
        updates.download_installer(release())
    assert not list(tmp_path.iterdir())


def test_installer_size_checked_from_header_before_body(network, tmp_path):
    def must_not_read():
        pytest.fail('bad size must be rejected before reading body')
    network[0].append(Response(PAYLOAD, headers=[('Content-Length', '1')], read_hook=must_not_read))
    with pytest.raises(updates.UpdateError, match='integrity_error'):
        updates.download_installer(release())
    assert not list(tmp_path.iterdir())


def test_cancel_after_download_data_removes_partial_stage(network, tmp_path):
    network[0].append(Response(PAYLOAD))
    cancelled = False
    def progress(count, total):
        nonlocal cancelled
        cancelled = count > 0
    with pytest.raises(updates.UpdateError, match='cancelled'):
        updates.download_installer(release(), cancelled=lambda: cancelled, progress=progress)
    assert not list(tmp_path.iterdir())


def test_network_error_during_download_removes_stage(network, tmp_path):
    network[0].append(OSError('failure'))
    with pytest.raises(updates.UpdateError, match='network_error'):
        updates.download_installer(release())
    assert not list(tmp_path.iterdir())


def test_disk_failure_removes_stage_and_preserves_unrelated_files(network, tmp_path, monkeypatch):
    retained = tmp_path / 'retained-user-data.db'
    retained.write_bytes(b'must stay unchanged')
    network[0].append(Response(PAYLOAD))
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(updates.os, 'replace', fail)
    with pytest.raises(updates.UpdateError, match='storage_error'):
        updates.download_installer(release())
    assert list(tmp_path.iterdir()) == [retained] and retained.read_bytes() == b'must stay unchanged'


@pytest.mark.parametrize('change', ['content', 'missing', 'symlink', 'hardlink'])
def test_reverification_rejects_substitution_and_preserves_external_target(network, tmp_path, change):
    network[0].append(Response(PAYLOAD))
    result = updates.download_installer(release())
    external = tmp_path / 'external.exe'
    external.write_bytes(PAYLOAD)
    if change == 'content':
        result.path.write_bytes(b'x' * len(PAYLOAD))
    else:
        result.path.unlink()
        if change == 'symlink':
            try:
                result.path.symlink_to(external)
            except OSError:
                pytest.skip('symlinks unavailable')
        elif change == 'hardlink':
            result.path.hardlink_to(external)
    with pytest.raises(updates.UpdateError, match='integrity_error'):
        updates.verify_download(result)
    updates.discard_download(result)
    assert external.read_bytes() == PAYLOAD


def test_unregistered_download_cannot_verify_or_delete_arbitrary_paths(network, tmp_path):
    target = tmp_path / 'SORTH-setup.exe'
    target.write_bytes(PAYLOAD)
    forged = updates.DownloadResult(target, release())
    with pytest.raises(updates.UpdateError, match='integrity_error'):
        updates.verify_download(forged)
    updates.discard_download(forged)
    assert target.read_bytes() == PAYLOAD


def test_changed_release_cannot_rebind_an_existing_download(network):
    network[0].append(Response(PAYLOAD))
    result = updates.download_installer(release())
    forged = replace(result, release=replace(result.release, version='9.0.0'))
    with pytest.raises(updates.UpdateError, match='integrity_error'):
        updates.verify_download(forged)
    updates.discard_download(forged)
    assert result.path.exists()


def test_reverification_cancellable(network):
    network[0].append(Response(PAYLOAD))
    result = updates.download_installer(release())
    with pytest.raises(updates.UpdateError, match='cancelled'):
        updates.verify_download(result, cancelled=lambda: True)


@pytest.mark.parametrize('asset', [updates.InstallerAsset('../evil.exe', 'https://evil.invalid', len(PAYLOAD), SHA256),
    updates.InstallerAsset('SORTH-2.1.0-abcdef123456-windows-x64-unsigned-setup.exe',
                          'https://evil.invalid', len(PAYLOAD), SHA256)])
def test_download_revalidates_caller_supplied_release(network, asset):
    with pytest.raises(updates.UpdateError, match='invalid_asset|invalid_url'):
        updates.download_installer(replace(release(), installer=asset))
    assert not network[1]


def test_discard_refuses_replaced_directory_and_never_recurses(network, tmp_path):
    network[0].append(Response(PAYLOAD))
    result = updates.download_installer(release())
    original, moved = result.path.parent, tmp_path / 'saved-directory'
    original.rename(moved)
    original.mkdir()
    unrelated = original / 'SORTH-setup.exe'
    unrelated.write_bytes(b'must not delete')
    updates.discard_download(result)
    assert unrelated.read_bytes() == b'must not delete' and (moved / 'SORTH-setup.exe').read_bytes() == PAYLOAD


def test_progress_is_throttled_to_changing_percentages(network):
    payload = b'MZ' + b'x' * 11998
    candidate = release()
    candidate = replace(candidate, installer=replace(candidate.installer, size=len(payload),
                        sha256=hashlib.sha256(payload).hexdigest()))
    network[0].append(Response(chunks=[payload[start:start + 10] for start in range(0, len(payload), 10)]))
    progress = []
    result = updates.download_installer(candidate, progress=lambda received, total: progress.append((received, total)))
    assert len(progress) == 101
    assert [received * 100 // total for received, total in progress] == list(range(101))
    assert updates.verify_download(result).read_bytes() == payload


def test_http_client_cannot_reconnect_automatically_after_cancellation(network):
    network[0].append(json_response([]))
    updates.check_updates('2.0.0')
    assert all(connection.auto_open == 0 for connection in network[2])


def test_staged_file_tamper_before_final_verification_never_returns_download(network, tmp_path, monkeypatch):
    network[0].append(Response(PAYLOAD))
    original = updates.verify_download
    def tamper(download, **kwargs):
        download.path.write_bytes(b'x' * len(PAYLOAD))
        return original(download, **kwargs)
    monkeypatch.setattr(updates, 'verify_download', tamper)
    with pytest.raises(updates.UpdateError, match='integrity_error'):
        updates.download_installer(release())
    assert not list(tmp_path.iterdir()) and not updates._DOWNLOADS


def test_download_deadline_cleans_stage_even_when_headers_stall(network, tmp_path, monkeypatch):
    gate, started, finished = threading.Event(), threading.Event(), threading.Event()
    def stalled():
        started.set()
        gate.wait(3)
        finished.set()
    network[3]['headers'] = stalled
    network[0].append(Response(PAYLOAD))
    monkeypatch.setattr(updates, 'DOWNLOAD_DEADLINE', .06)
    try:
        with pytest.raises(updates.UpdateError, match='timeout'):
            updates.download_installer(release())
        assert started.is_set() and not list(tmp_path.iterdir())
    finally:
        gate.set()
        assert finished.wait(1)


def test_owned_cleanup_never_recursively_removes_unexpected_content(network):
    network[0].append(Response(PAYLOAD))
    result = updates.download_installer(release())
    unrelated = result.path.parent / 'unrelated.txt'
    unrelated.write_bytes(b'retain me')
    updates.discard_download(result)
    assert not result.path.exists() and unrelated.read_bytes() == b'retain me'


def test_no_network_or_writes_when_module_is_imported(network):
    # All network entry points are called by explicit functions, never imports.
    import ast
    tree = ast.parse(Path(updates.__file__).read_text())
    assert not any(isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                   for node in tree.body)
    assert not network[1]


@pytest.mark.parametrize('raw', [b'2.0.0' + b' ' * 130 + b'bad', b'wrong', b'\xff'])
def test_source_identity_rejects_corrupt_or_truncated_version(tmp_path, monkeypatch, raw):
    package = tmp_path / 'src' / 'application' / 'app_updates.py'
    package.parent.mkdir(parents=True)
    package.write_text('')
    (tmp_path / 'VERSION').write_bytes(raw)
    monkeypatch.setattr(updates, '__file__', str(package))
    with pytest.raises(updates.UpdateError, match='invalid_identity'):
        updates.current_identity()


@pytest.mark.parametrize('headers', [[('Transfer-Encoding', 'compress')],
    [('Transfer-Encoding', 'chunked'), ('Content-Length', '2')],
    [('Transfer-Encoding', 'chunked'), ('Transfer-Encoding', 'chunked')]])
def test_ambiguous_framing_is_rejected(network, headers):
    network[0].append(Response(b'[]', headers=headers))
    with pytest.raises(updates.UpdateError, match='invalid_response'):
        updates.check_updates('2.0.0')


def test_valid_chunked_metadata_without_content_length(network):
    network[0].append(Response(b'[]', headers=[('Transfer-Encoding', 'chunked')]))
    assert updates.check_updates('2.0.0').state == 'no_releases'


def test_detached_connection_close_socket_still_shutdown_on_cancel(network, monkeypatch):
    gate, started, stopped = threading.Event(), threading.Event(), threading.Event()
    def stalled():
        # http.client may detach the socket before returning a response marked
        # Connection: close; cancellation must retain its original socket handle.
        network[2][-1].sock = None
        started.set()
        gate.wait(3)
    network[0].append(Response(b'[]', read_hook=stalled))
    network[3]['shutdown'] = stopped.set
    monkeypatch.setattr(updates, 'CHECK_DEADLINE', .06)
    try:
        with pytest.raises(updates.UpdateError, match='timeout'):
            updates.check_updates('2.0.0')
        assert started.is_set() and stopped.is_set()
    finally:
        gate.set()
