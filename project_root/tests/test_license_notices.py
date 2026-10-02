"""Evidence and packaging checks, not a legal compliance certification."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from tools.collect_license_notices import collect, lock_digest

ROOT = Path(__file__).resolve().parents[2]


def test_committed_inventory_matches_lock_and_has_all_notice_files():
    inventory = json.loads((ROOT / 'third_party/wheel-inventory.json').read_text())
    lock = ROOT / 'project_root/requirements-windows.lock'
    assert inventory['lock_sha256'] == lock_digest(lock)
    lines = [line for line in lock.read_text().splitlines() if line and not line.startswith('#')]
    assert len(inventory['packages']) == len(lines)
    for row in inventory['packages']:
        assert row['sha256'] in lock.read_text()
        path = ROOT / 'third_party' / row['notice_file']
        text = path.read_text(encoding='utf-8')
        assert row['wheel'] in text
        assert row['upstream_notice_files']
        for notice in row['upstream_notice_files']:
            assert 'BEGIN ' + notice['path'] in text
    assert 'Version 3, 29 June 2007' in (ROOT / 'LICENSE').read_text()
    assert 'GPL-3.0-only' in (ROOT / 'LICENSING.md').read_text()


def make_wheel(tmp_path):
    wheels = tmp_path / 'wheels'
    wheels.mkdir()
    wheel = wheels / 'example-1.0-py3-none-any.whl'
    with ZipFile(wheel, 'w') as archive:
        archive.writestr('example-1.0.dist-info/METADATA', 'Name: example\nVersion: 1.0\nLicense-Expression: MIT\n')
        archive.writestr('example-1.0.dist-info/licenses/LICENSE', 'Original notice\r\nKeep this text.\n')
    lock = tmp_path / 'requirements.lock'
    lock.write_text('example==1.0 --hash=sha256:' + hashlib.sha256(wheel.read_bytes()).hexdigest() + '\n')
    return wheels, wheel, lock


def test_collector_preserves_original_text_and_hashes(tmp_path):
    wheels, wheel, lock = make_wheel(tmp_path)
    output = tmp_path / 'output'
    assert collect(wheels, lock, output) == 1
    assert b'Original notice\r\nKeep this text.\n' in (output / 'licenses/example.txt').read_bytes()
    data = json.loads((output / 'wheel-inventory.json').read_text())
    assert data['packages'][0]['sha256'] == hashlib.sha256(wheel.read_bytes()).hexdigest()


def test_collector_rejects_modified_or_missing_wheel_before_writing(tmp_path):
    wheels, wheel, lock = make_wheel(tmp_path)
    wheel.write_bytes(wheel.read_bytes() + b'modified')
    output = tmp_path / 'output'
    with pytest.raises(ValueError, match='Unmatched'):
        collect(wheels, lock, output)
    assert not output.exists()
    wheel.unlink()
    with pytest.raises(ValueError, match='Missing'):
        collect(wheels, lock, output)
    assert not output.exists()


def test_lock_identity_is_stable_across_git_line_endings(tmp_path):
    lf = tmp_path / 'lf.lock'
    crlf = tmp_path / 'crlf.lock'
    content = '# Locked wheels\nexample==1.0 --hash=sha256:' + 'a' * 64 + '\n'
    lf.write_bytes(content.encode('utf-8'))
    crlf.write_bytes(content.replace('\n', '\r\n').encode('utf-8'))
    assert lock_digest(lf) == lock_digest(crlf)
    crlf.write_bytes(content.replace('1.0', '1.1').encode('utf-8'))
    assert lock_digest(lf) != lock_digest(crlf)


def test_committed_upstream_notice_bytes_match_inventory_hashes():
    inventory = json.loads((ROOT / 'third_party/wheel-inventory.json').read_text())
    for package in inventory['packages']:
        content = (ROOT / 'third_party' / package['notice_file']).read_bytes()
        for notice in package['upstream_notice_files']:
            start = ('\n===== BEGIN ' + notice['path'] + ' =====\n').encode('utf-8')
            end = ('\n===== END ' + notice['path'] + ' =====\n').encode('utf-8')
            assert content.count(start) == 1
            assert content.count(end) == 1
            original = content.split(start, 1)[1].split(end, 1)[0]
            assert hashlib.sha256(original).hexdigest() == notice['sha256']
