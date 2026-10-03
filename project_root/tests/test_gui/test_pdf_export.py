from pathlib import Path

import pytest
from pypdf import PdfReader
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from src.gui.main_window import MainWindow, _InfoDialog
from src.gui.i18n import language_manager
from src.infrastructure.session_repository import SessionRepository
from src.infrastructure.schedule_exporter import ScheduleExporter
from tests.test_gui.test_schedule_viewer import app, populated, attach_validation_inputs


def content(path):
    return '\n'.join(p.extract_text() for p in PdfReader(path).pages)


@pytest.mark.parametrize('language', ['es', 'en'])
def test_pdf_gui_full_filtered_selected_format_and_scope(app, tmp_path, monkeypatch, language):
    language_manager().set_language(language)
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    try:
        window.current_schedule = populated(window.schedule_viewer)
        attach_validation_inputs(window)
        window.schedule_viewer._list_search.setText('ZOO')
        selected = tmp_path / 'chosen'
        seen = []
        def choose(*args):
            seen.append(args)
            assert '(*.pdf)' in args[3]
            assert ('PDF documents' if language == 'en' else 'Documentos PDF') in args[3]
            return str(selected), 'PDF documents (*.pdf)'
        monkeypatch.setattr(QFileDialog, 'getSaveFileName', choose)
        monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
        window._export_schedule(filtered=True)
        path = selected.with_suffix('.pdf')
        output = content(path)
        assert ('Filtered view' if language == 'en' else 'Vista filtrada') in output
        assert ('2 exported of 4 assigned' if language == 'en' else '2 exportadas de 4 asignadas') in output
        assert ('PARTIAL schedule: 1 pending' if language == 'en' else 'Horario PARCIAL: 1 pendientes') in output
        assert ('Search: ZOO' if language == 'en' else 'Buscar: ZOO') in output
        assert ('Wednesday' if language == 'en' else 'Miércoles') in output
        assert 'Biología marina' in output
        assert 'BIO-G2' not in output
        window._export_schedule()
        output = content(path)
        assert ('All assignments' if language == 'en' else 'Todas las asignaciones') in output
        assert ('4 exported of 4 assigned' if language == 'en' else '4 exportadas de 4 asignadas') in output
        assert 'BIO-G2' in output
        assert ('Not applied' if language == 'en' else 'No aplicados') in output
        assert window.schedule_viewer._list_search.text() == 'ZOO'
    finally:
        window.close()
        language_manager().set_language('es')


def test_pdf_gui_cancel_error_and_empty_filter(app, tmp_path, monkeypatch):
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    try:
        window.current_schedule = populated(window.schedule_viewer)
        attach_validation_inputs(window)
        before = window.current_schedule.copy()
        called = []
        monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: ('', 'PDF documents (*.pdf)'))
        monkeypatch.setattr(ScheduleExporter, 'to_pdf', lambda *a, **k: called.append(k))
        window._export_schedule()
        assert not called
        path = tmp_path / 'failed.pdf'
        notices = []
        monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (str(path), ''))
        monkeypatch.setattr(_InfoDialog, 'exec', lambda self: notices.append(self.windowTitle()))
        monkeypatch.setattr(ScheduleExporter, 'to_pdf', lambda *a, **k: (_ for _ in ()).throw(PermissionError('locked')))
        window._export_schedule()
        assert notices == ['Error'] and not path.exists()
        window.schedule_viewer._list_search.setText('no matches anywhere')
        monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: pytest.fail('Empty export opened picker'))
        monkeypatch.setattr(QMessageBox, 'information', lambda *a: None)
        window._export_schedule(filtered=True)
        assert window.current_schedule == before
    finally:
        window.close()
