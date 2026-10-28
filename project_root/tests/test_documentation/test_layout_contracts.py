"""Stable public commands and packaged documentation survive folder changes."""
from pathlib import Path
import re

from tools.build_manual import DEFAULT_OUTPUT, DEFAULT_SOURCE
from tools.package_windows import LEGAL_FILES

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = ROOT.parent


def test_operational_guides_reference_existing_repository_tools():
    """Release instructions must not advertise deleted commands or build specs."""
    guides = [REPOSITORY / 'docs' / name for name in (
        'WINDOWS_RELEASE_ACCEPTANCE.md', 'WINDOWS_ACCEPTANCE_RECORD.md',
        'SECURITY_CHECKS.md', 'release/WINDOWS_DISTRIBUTION.md',
        'release/FIRST_RELEASE_PIPELINE.md',
    )]
    missing = []
    for guide in guides:
        text = guide.read_text(encoding='utf-8').replace('\\', '/')
        tools = re.findall(r'(?<![A-Za-z0-9_])(?:project_root/)?(tools/[A-Za-z0-9_]+\.(?:py|ps1))', text)
        specs = re.findall(r'`([A-Z][A-Z-]*\.spec)`', text)
        missing.extend((guide.name, name) for name in set(tools + specs) if not (ROOT / name).is_file())
    assert missing == []


def test_manual_has_one_canonical_source_and_stable_build_output():
    assert DEFAULT_SOURCE == REPOSITORY / "docs/user/MANUAL_USUARIO.md"
    assert DEFAULT_SOURCE.stat().st_size > 1000
    assert DEFAULT_OUTPUT == ROOT / "build/docs/MANUAL_USUARIO.pdf"



def test_packaged_windows_guide_has_one_canonical_source():
    canonical = "docs/release/WINDOWS_DISTRIBUTION.md"
    assert canonical in LEGAL_FILES
    assert (REPOSITORY / canonical).stat().st_size > 1000


def test_every_explicit_distribution_document_exists():
    assert len(LEGAL_FILES) == len(set(LEGAL_FILES))
    assert [path for path in LEGAL_FILES if not (REPOSITORY / path).is_file()] == []


def test_public_execution_and_packaging_entrypoints_remain_stable():
    for path in ("gui_app.py", "main.py", "mcp_app.py", "build_exe.ps1", "build_mcp.ps1",
                 "SORTH-MCP.spec", "requirements.txt", "requirements-dev.txt",
                 "requirements-windows.lock", "MCP_OPTIONAL.md", "README.md",
                 "installer/sorth.iss", "data/input/Cursos_Ejemplo.xlsx"):
        assert (ROOT / path).is_file(), path
