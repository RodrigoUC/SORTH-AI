"""Frozen-output identity gate: read real PDF pages and reject stale evidence."""
import json
from pathlib import Path
import subprocess
import sys

import pytest
from reportlab.pdfgen.canvas import Canvas

from tools.verify_pdf_export_identity import verify_exports


def write_pdf(path, versions):
    """Build controlled multi-page output independently of the validator."""
    canvas = Canvas(str(path))
    for version in versions:
        canvas.drawString(30, 800, f'SORTH {version} | Timetable')
        canvas.showPage()
    canvas.save()


@pytest.mark.parametrize('language', ['es', 'en'])
def test_gate_rejects_a_stale_header_on_a_later_page_in_either_language(tmp_path, language):
    for suffix in ('es', 'en'):
        write_pdf(tmp_path / f'schedule-{suffix}.pdf', ['3.0.0', '2.0.0' if suffix == language else '3.0.0'])
    with pytest.raises(ValueError, match=f'schedule-{language}.pdf: page 2'):
        verify_exports(tmp_path, '3.0.0')


def test_gate_accepts_all_pages_matching_the_executable_version(tmp_path):
    for language in ('es', 'en'):
        write_pdf(tmp_path / f'schedule-{language}.pdf', ['7.8.9', '7.8.9'])
    assert verify_exports(tmp_path, '7.8.9') == {
        'ok': True, 'version': '7.8.9', 'pages': {'schedule-es.pdf': 2, 'schedule-en.pdf': 2},
    }


def test_failed_gate_replaces_a_stale_success_report(tmp_path):
    for language in ('es', 'en'):
        write_pdf(tmp_path / f'schedule-{language}.pdf', ['2.0.0'])
    output = tmp_path / 'result.json'
    output.write_text('{"ok": true}', encoding='utf-8')
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / 'tools/verify_pdf_export_identity.py'),
                             '--directory', str(tmp_path), '--version', '3.0.0',
                             '--output', str(output)], capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert json.loads(output.read_text(encoding='utf-8'))['ok'] is False


def test_windows_gate_checks_the_actual_frozen_exports():
    root = Path(__file__).resolve().parents[2]
    workflow = (root / '.github/workflows/windows-review.yml').read_text(encoding='utf-8')
    assert 'tools/verify_pdf_export_identity.py --directory $smokeDir --version $result.build_identity.version' in workflow
    assert workflow.index('tools/verify_pdf_export_identity.py') > workflow.index("'--smoke-test'")
    assert 'project_root/build/reports/packaged-smoke/*.pdf' in workflow
