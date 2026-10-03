from pathlib import Path
import pytest
from tools.prune_unused_qt_pdf import prune, PLUGIN, LIBRARY


def build(tmp_path):
    root = tmp_path / 'app'
    for name in ('SORTH.exe', PLUGIN, LIBRARY, '_internal/PyQt6/Qt6/bin/Qt6Network.dll',
                 '_internal/PyQt6/Qt6/bin/opengl32sw.dll'):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(name.encode())
    return root


def test_prunes_only_two_known_files_and_reports_hashes(tmp_path):
    root = build(tmp_path)
    result = prune(root, tmp_path / 'report.json', lambda p: ['kernel32.dll'])
    assert {x['path'] for x in result['removed']} == {PLUGIN, LIBRARY}
    assert all(len(x['sha256']) == 64 for x in result['removed'])
    assert not (root / PLUGIN).exists() and not (root / LIBRARY).exists()
    assert len(list(root.rglob('*.dll'))) == 2
    assert result['license_clearance'] is False


@pytest.mark.parametrize('kind', ['dependent', 'unreadable', 'binding', 'unexpected', 'report_exists'])
def test_fails_before_removing_any_files(tmp_path, kind):
    root = build(tmp_path)
    report = tmp_path / 'report.json'
    def scan(p):
        if kind == 'unreadable':
            raise ValueError('Invalid PE')
        return ['qt6pdf.dll'] if kind == 'dependent' else []
    if kind == 'binding':
        (root / 'QtPdf.pyd').write_bytes(b'binding')
    if kind == 'unexpected':
        (root / 'qpdf.dll').write_bytes(b'duplicate')
    if kind == 'report_exists':
        report.write_text('{}')
    with pytest.raises((ValueError, FileExistsError)):
        prune(root, report, scan)
    assert (root / PLUGIN).exists() and (root / LIBRARY).exists()
