"""Portable safety contracts and native PowerShell resolver regression tests."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_lifecycle_uses_registered_build_and_native_paths():
    script = (ROOT / 'tools/test_installer.ps1').read_text()
    assert 'SORTH-$($info.build_id)_is1' in script
    assert "if (Test-Path -LiteralPath $uninstallKey) { throw" in script
    assert '(Get-Item -LiteralPath $exe -ErrorAction Stop).FullName' in script
    assert '$destination/unins000.exe' not in script
    assert "Uninstall-TestBuild 'first'" in script
    assert "Uninstall-TestBuild 'recovery'" in script
    assert "throw 'Uninstall left the registered build.'" in script
    assert "throw 'Uninstall left the installed executable.'" in script
    for stage in ['install-$attempt', 'before-smoke', 'after-smoke']:
        assert stage in script
    assert 'Get-FileHash -LiteralPath $_.FullName' in script
    assert 'Get-WinEvent' in script


def test_resolver_never_executes_registry_commands_or_guesses():
    script = (ROOT / 'tools/installer_test_helpers.ps1').read_text()
    assert 'Invoke-Expression' not in script
    assert 'Start-Process' not in script
    assert 'Get-ChildItem' not in script
    assert 'InstallLocation' in script and 'UninstallString' in script
    assert 'IsPathFullyQualified' in script
    assert 'GetDirectoryName($exe) -ine $expected' in script
    assert 'ReparsePoint' in script
    assert "ChangeExtension($exe, '.dat')" in script


@pytest.mark.skipif(os.name != 'nt' or not shutil.which('pwsh'), reason='Native Windows PowerShell path validation')
@pytest.mark.parametrize('case', ['valid', 'log', 'numbered', 'wrong_location', 'sibling',
                                 'relative', 'other_exe', 'extra_args', 'missing_exe', 'missing_dat'])
def test_native_registered_uninstaller_validation(tmp_path, case):
    app = tmp_path / 'application with spaces'
    app.mkdir()
    exe = app / ('unins001.exe' if case == 'numbered' else 'unins000.exe')
    exe.write_bytes(b'test only; never executed')
    exe.with_suffix('.dat').write_bytes(b'test')
    location = str(app)
    command = f'"{exe}"'
    if case == 'log':
        command += ' /LOG'
    elif case == 'wrong_location':
        location = str(tmp_path)
    elif case == 'sibling':
        command = f'"{tmp_path / "application with spaces-other" / exe.name}"'
    elif case == 'relative':
        command = '"unins000.exe"'
    elif case == 'other_exe':
        command = f'"{app / "SORTH.exe"}"'
    elif case == 'extra_args':
        command += ' /SILENT & calc.exe'
    elif case == 'missing_exe':
        exe.unlink()
    elif case == 'missing_dat':
        exe.with_suffix('.dat').unlink()
    def ps_quote(value):
        return "'" + str(value).replace("'", "''") + "'"
    helper = ROOT / 'tools/installer_test_helpers.ps1'
    script = (f"$ErrorActionPreference = 'Stop'; . {ps_quote(helper)}; "
              f"$record = [pscustomobject]@{{InstallLocation={ps_quote(location)}; "
              f"UninstallString={ps_quote(command)}}}; "
              f"Resolve-TestUninstaller $record {ps_quote(app)}")
    result = subprocess.run(['pwsh', '-NoProfile', '-NonInteractive', '-Command', script],
                            capture_output=True, text=True, timeout=30)
    if case in {'valid', 'log', 'numbered'}:
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == str(exe)
    else:
        assert result.returncode != 0, result.stdout
