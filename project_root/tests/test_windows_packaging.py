"""Portable configuration checks; these do not replace a Windows smoke test."""
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def test_spec_builds_portable_onedir_without_upx():
    calls = {}

    def capture(name, result=None):
        def factory(*args, **kwargs):
            calls[name] = (args, kwargs)
            return result
        return factory

    analysis = SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])
    context = {
        "SPECPATH": str(ROOT),
        "Analysis": capture("Analysis", analysis),
        "PYZ": capture("PYZ"),
        "EXE": capture("EXE"),
        "COLLECT": capture("COLLECT"),
    }
    exec(compile((ROOT / "SORTH.spec").read_text(), "SORTH.spec", "exec"), context)
    args, kwargs = calls["Analysis"]
    assert Path(args[0][0]).is_file()
    assert all(Path(source).exists() for source, _ in kwargs["datas"])
    names = {Path(source).name for source, _ in kwargs["datas"]}
    assert {"LICENSE", "LICENSING.md", "third_party"} <= names
    exe = calls["EXE"][1]
    assert exe["exclude_binaries"] is True
    assert exe["upx"] is False
    assert calls["COLLECT"][1]["upx"] is False
    assert Path(exe["icon"][0]).is_file()
    assert Path(exe["version"]).is_file()


def test_windows_version_resource_is_valid_constructor_data():
    def constructor(*args, **kwargs):
        return args, kwargs
    names = ("VSVersionInfo", "FixedFileInfo", "StringFileInfo", "StringTable",
             "StringStruct", "VarFileInfo", "VarStruct")
    resource = eval(compile((ROOT / "windows_version_info.txt").read_text(),
                            "windows_version_info.txt", "eval"),
                    {name: constructor for name in names})
    info = resource[1]["ffi"][1]
    assert len(info["filevers"]) == 4
    assert all(isinstance(part, int) and 0 <= part <= 65535
               for part in info["filevers"])


def test_build_script_does_not_silently_install_or_pack_with_upx():
    script = (ROOT / "build_exe.ps1").read_text()
    assert "[switch]$OneFile = $false" in script
    assert "'--noupx'" in script
    assert "pip install" not in script
    assert "$LASTEXITCODE -ne 0" in script
    assert "Get-FileHash" in script
    for required in ("../LICENSE", "../LICENSING.md", "../third_party"):
        assert required in script
    assert "'--specpath', 'build/spec'" in script
