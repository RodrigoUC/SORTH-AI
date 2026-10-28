"""Portable configuration checks; these do not replace a Windows smoke test."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_desktop_build_has_one_canonical_entrypoint():
    assert not (ROOT / 'SORTH.spec').exists()
    script = (ROOT / 'build_exe.ps1').read_text(encoding='utf-8')
    assert "'--onedir', '--windowed'" in script
    assert "'--version-file'" in script and 'build/identity/windows_version_info.txt' in script
    assert 'tools/build_identity.py' in script


def test_windows_version_resource_is_valid_constructor_data(tmp_path):
    from tools.build_identity import generate
    generate("a" * 40, tmp_path)
    def constructor(*args, **kwargs):
        return args, kwargs
    names = ("VSVersionInfo", "FixedFileInfo", "StringFileInfo", "StringTable",
             "StringStruct", "VarFileInfo", "VarStruct")
    resource = eval(compile((tmp_path / "windows_version_info.txt").read_text(encoding='utf-8'),
                            "windows_version_info.txt", "eval"),
                    {name: constructor for name in names})
    info = resource[1]["ffi"][1]
    assert len(info["filevers"]) == 4
    assert all(isinstance(part, int) and 0 <= part <= 65535
               for part in info["filevers"])


def test_build_script_does_not_silently_install_or_pack_with_upx():
    script = (ROOT / "build_exe.ps1").read_text(encoding='utf-8')
    assert "[switch]$OneFile = $false" in script
    assert "'--noupx'" in script
    assert "pip install" not in script
    assert "$LASTEXITCODE -ne 0" in script
    assert "Get-FileHash" in script
    for required in ("../LICENSE", "../LICENSING.md", "../third_party"):
        assert required in script
    assert "'--specpath', 'build/spec'" in script
