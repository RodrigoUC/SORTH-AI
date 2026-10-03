import hashlib
from pathlib import Path
import zipfile

import pytest
from tools.lock_windows import make_lock


def wheel(folder, name, version='1.0', requires=''):
    path = folder / f'{name}-{version}-py3-none-any.whl'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr(f'{name}-{version}.dist-info/METADATA',
                   f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n{requires}')
    return path


def test_lock_evaluates_windows_markers_even_on_linux(tmp_path):
    wheel(tmp_path, 'app', requires='Requires-Dist: windowsdep>=1; sys_platform == "win32"\n')
    with pytest.raises(ValueError, match='Windows dependency'):
        make_lock(tmp_path, tmp_path / 'lock.txt')
    dependency = wheel(tmp_path, 'windowsdep')
    assert make_lock(tmp_path, tmp_path / 'lock.txt') == 2
    result = (tmp_path / 'lock.txt').read_text()
    assert f'windowsdep==1.0 --hash=sha256:{hashlib.sha256(dependency.read_bytes()).hexdigest()}' in result


def test_windows_lock_pins_all_entries_with_hashes():
    path = Path(__file__).resolve().parents[1] / 'requirements-windows.lock'
    lines = [line for line in path.read_text().splitlines() if line and not line.startswith('#')]
    assert len(lines) >= 25
    for line in lines:
        name, checksum = line.split(' --hash=sha256:')
        assert '==' in name and len(checksum) == 64
        int(checksum, 16)
    assert any(line.startswith('pefile==') for line in lines)
    assert any(line.startswith('pywin32-ctypes==') for line in lines)


def test_lock_refuses_wrong_python_binary_wheel(tmp_path):
    original = wheel(tmp_path, 'binary')
    original.rename(tmp_path / 'binary-1.0-cp311-cp311-win_amd64.whl')
    with pytest.raises(ValueError, match='Incompatible CPython'):
        make_lock(tmp_path, tmp_path / 'lock.txt')


def test_review_workflow_does_not_publish_or_use_write_tokens():
    root = Path(__file__).resolve().parents[2]
    workflow = (root / '.github/workflows/windows-review.yml').read_text()
    assert 'contents: read' in workflow
    assert 'persist-credentials: false' in workflow
    assert 'pull_request_target' not in workflow
    assert 'secrets.' not in workflow
    assert '--require-hashes' in workflow
    assert '--smoke-test' in workflow
    assert 'source_commit' in (root / 'project_root/tools/package_windows.py').read_text()

def test_windows_lock_follows_requested_transitive_extras(tmp_path):
    def wheel(name, requirements=''):
        with zipfile.ZipFile(tmp_path / f'{name}-1.0-py3-none-any.whl', 'w') as zf:
            zf.writestr(f'{name}-1.0.dist-info/METADATA',
                        f'Name: {name}\nVersion: 1.0\n{requirements}')
    wheel('app', 'Requires-Dist: token[crypto]>=1\n')
    wheel('token', 'Requires-Dist: crypto>=1; extra == "crypto"\n')
    with pytest.raises(ValueError, match='Windows dependency'):
        make_lock(tmp_path, tmp_path / 'lock')
    wheel('crypto')
    assert make_lock(tmp_path, tmp_path / 'lock') == 3
