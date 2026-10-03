"""Stable public commands and packaged documentation survive folder changes."""
from pathlib import Path

from tools.build_manual import DEFAULT_OUTPUT, DEFAULT_SOURCE
from tools.package_windows import LEGAL_FILES

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = ROOT.parent


def test_manual_has_one_canonical_source_and_stable_build_output():
    assert DEFAULT_SOURCE == REPOSITORY / "docs/user/MANUAL_USUARIO.md"
    assert DEFAULT_SOURCE.stat().st_size > 1000
    assert DEFAULT_OUTPUT == ROOT / "build/docs/MANUAL_USUARIO.pdf"
    pointer = (ROOT / "MANUAL_USUARIO.md").read_text(encoding="utf-8")
    assert "../docs/user/MANUAL_USUARIO.md" in pointer
    assert len(pointer) < 500


def test_windows_guide_pointer_targets_the_packaged_canonical_guide():
    canonical = "docs/release/WINDOWS_DISTRIBUTION.md"
    assert canonical in LEGAL_FILES
    assert "../" + canonical in (ROOT / "WINDOWS_DISTRIBUTION.md").read_text(encoding="utf-8")


def test_every_explicit_distribution_document_exists():
    assert len(LEGAL_FILES) == len(set(LEGAL_FILES))
    assert [path for path in LEGAL_FILES if not (REPOSITORY / path).is_file()] == []


def test_public_execution_and_packaging_entrypoints_remain_stable():
    for path in ("gui_app.py", "main.py", "mcp_app.py", "build_exe.ps1", "build_mcp.ps1",
                 "SORTH.spec", "SORTH-MCP.spec", "requirements.txt", "requirements-dev.txt",
                 "requirements-windows.lock", "MCP_OPTIONAL.md", "README.md",
                 "installer/sorth.iss", "data/input/Cursos_Ejemplo.xlsx"):
        assert (ROOT / path).is_file(), path
