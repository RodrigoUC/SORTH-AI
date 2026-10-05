"""Portable wiring contracts; real shell/version-resource checks run on Windows CI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'tools/test_installer.ps1').read_text()


def test_identity_is_read_from_installed_native_surfaces():
    for required in (
        '(Get-Item -LiteralPath $exe).VersionInfo',
        '$installer.VersionInfo',
        "$appVersion.ProductName -cne 'SORTH-AI'",
        "$appVersion.FileDescription -cne 'SORTH-AI - Sistema de Organizacion de Horarios'",
        "$setupVersion.ProductName.TrimEnd(' ') -cne 'SORTH-AI'",
        '$record.DisplayName -cne "SORTH-AI $($info.build_id) (unsigned review)"',
        'Check-IconPath $record.DisplayIcon $exe',
        'New-Object -ComObject WScript.Shell',
        'New-Object -ComObject Shell.Application',
        "$item.ExtendedProperty('System.AppUserModel.ID')",
        "$evidence.app_user_model_id -cne 'SORTH.App'",
        '$evidence.target -ine $exe',
        '$evidence.working_directory -ine $destination',
        'Check-IconPath $evidence.icon $exe',
    ):
        assert required in SCRIPT


def test_native_evidence_precedes_assertions_and_covers_reinstall():
    assert SCRIPT.index('native-identity-$stage.json') < SCRIPT.index("throw 'Installed EXE product identity mismatch.'")
    assert 'Check-NativeIdentity "install-$attempt"' in SCRIPT
    assert "Check-NativeIdentity 'recovery' $true" in SCRIPT
    assert 'native-cleanup-$stage.json' in SCRIPT
    assert 'sentinel_sha256=(Get-FileHash -LiteralPath $sentinel).Hash' in SCRIPT


def test_desktop_is_opt_in_and_build_owned_shortcuts_are_guarded():
    assert '$shortcutName = "SORTH-AI $($info.build_id).lnk"' in SCRIPT
    assert "GetFolderPath('Programs')" in SCRIPT
    assert "GetFolderPath('DesktopDirectory')" in SCRIPT
    assert "throw 'Refusing to replace an existing shortcut.'" in SCRIPT
    assert "elseif ($desktop.exists) { throw 'Default installation unexpectedly created a desktop shortcut.' }" in SCRIPT
    assert SCRIPT.count('/TASKS="desktopicon"') == 1
    assert SCRIPT.index('/TASKS="desktopicon"') > SCRIPT.index("Uninstall-TestBuild 'first'")
    assert "throw 'Uninstall left a build-owned shortcut.'" in SCRIPT
    assert "Remove-Item -LiteralPath $sentinel" in SCRIPT
    assert 'Remove-Item -LiteralPath $startShortcut' not in SCRIPT
    assert 'Remove-Item -LiteralPath $desktopShortcut' not in SCRIPT
