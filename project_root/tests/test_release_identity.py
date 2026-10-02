"""Portable release contracts; native installer execution remains Windows CI."""
import json
from pathlib import Path
import pytest
from tools.build_identity import identity, generate
ROOT = Path(__file__).resolve().parents[1]


def test_identity_is_exact_and_resource_matches(tmp_path):
    info = generate('b' * 40, tmp_path)
    assert info['version'] == (ROOT / 'VERSION').read_text().strip()
    assert info['build_id'] == info['version'] + '-' + 'b' * 12
    assert json.loads((tmp_path / 'build-identity.json').read_text()) == info
    assert info['build_id'] in (tmp_path / 'windows_version_info.txt').read_text()
    assert not info['signed']


@pytest.mark.parametrize('commit', ['main', 'b'*7, 'B'*40, '../'+'b'*37, 'b'*41])
def test_identity_rejects_ambiguous_or_unsafe_commit(commit):
    with pytest.raises(ValueError):
        identity(commit)


def test_installer_is_per_user_versioned_and_never_deletes_data():
    script = (ROOT / 'installer/sorth.iss').read_text()
    assert 'PrivilegesRequired=lowest' in script
    assert 'AppId=SORTH-{#BuildId}' in script
    assert 'DefaultDirName={localappdata}\\Programs\\SORTH\\{#BuildId}' in script
    for section in ['[UninstallDelete]', '[InstallDelete]', '[Registry]', '[Run]']:
        assert section not in script
    assert 'sorth_session' not in script


def test_compiler_provenance_is_pinned_and_checked():
    script = (ROOT / 'tools/build_installer.ps1').read_text()
    assert 'is-6_7_3/innosetup-6.7.3.exe' in script
    assert '9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732' in script
    assert 'Get-AuthenticodeSignature' in script
    assert "-ne 'Valid'" in script
    assert 'Pyrsys B.V.' in script


def test_installer_test_refuses_real_profile_and_preserves_data():
    script = (ROOT / 'tools/test_installer.ps1').read_text()
    assert "$env:GITHUB_ACTIONS -ne 'true'" in script
    assert "if (Test-Path $dataDir) { throw" in script
    assert "cross_version_rollback='NOT TESTED'" in script
    assert "clean_pc_without_python='NOT TESTED'" in script
