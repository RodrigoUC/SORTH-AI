"""Dotted basenames retain the selected export format and truthful filenames."""
import csv
from copy import deepcopy

import pytest
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from src.gui.main_window import _InfoDialog
from tests.test_gui.test_export_feedback import window


def assert_export_content(path, extension):
    data = path.read_bytes()
    if extension == 'csv':
        assert data.startswith(b'\xef\xbb\xbf')
        with path.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.reader(stream))
        assert len(rows) == 3
        assert {row[2] for row in rows[1:]} == {'BIO-G1', 'QUI-G1'}
    elif extension == 'pdf':
        from pypdf import PdfReader
        assert data.startswith(b'%PDF-')
        text = '\n'.join(page.extract_text() for page in PdfReader(path).pages)
        assert 'BIO-G1' in text and 'QUI-G1' in text
    else:
        from openpyxl import load_workbook
        assert data.startswith(b'PK\x03\x04')
        book = load_workbook(path)
        try:
            rows = list(book['Asignaciones'].values)
            assert len(rows) == 3
            assert {row[2] for row in rows[1:]} == {'BIO-G1', 'QUI-G1'}
        finally:
            book.close()


@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf'])
@pytest.mark.parametrize('filename', ['horario.v2', 'horario.2026.10.03',
                                      'horario.txt', 'horario.xls',
                                      'horario.other', 'horario.xlsx.bak'])
def test_unrecognized_suffix_appends_selected_format(
        window, tmp_path, monkeypatch, extension, filename):
    selected = tmp_path / filename
    # The picker may already have approved this path; it is never the output.
    selected.write_bytes(b'preserve entered destination')
    target = tmp_path / f'{filename}.{extension}'
    schedule = deepcopy(window.current_schedule)
    session = (tmp_path / 'session.db').read_bytes()
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        lambda *a: (str(selected), f'Format (*.{extension})'))
    monkeypatch.setattr(QMessageBox, 'exec', lambda *a: pytest.fail('Unexpected confirmation'))
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
    window._export_schedule()
    assert_export_content(target, extension)
    assert selected.read_bytes() == b'preserve entered destination'
    assert target.name in window.status_bar.currentMessage()
    assert window.current_schedule == schedule
    assert (tmp_path / 'session.db').read_bytes() == session
    assert not list(tmp_path.glob('.sorth-export-*'))


@pytest.mark.parametrize('selected_format', ['xlsx', 'csv', 'pdf'])
@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf', 'XLSX', 'CSV', 'PDF'])
def test_supported_extension_overrides_filter_with_matching_bytes(
        window, tmp_path, monkeypatch, selected_format, extension):
    target = tmp_path / f'horario.v2.{extension}'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        lambda *a: (str(target), f'Format (*.{selected_format})'))
    monkeypatch.setattr(QMessageBox, 'exec', lambda *a: pytest.fail('Unexpected confirmation'))
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
    window._export_schedule()
    assert_export_content(target, extension.lower())
    assert target.name in window.status_bar.currentMessage()
    assert not (tmp_path / f'{target.name}.{selected_format}').exists()
