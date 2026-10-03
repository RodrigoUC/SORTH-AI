from pathlib import Path

import pytest
from pypdf import PdfReader

from src.infrastructure.schedule_exporter import ScheduleExporter
from src.scheduling.group import Group
from src.scheduling.time_model import TimeModel


def text(path):
    return '\n'.join(page.extract_text() for page in PdfReader(path).pages)


def test_pdf_exact_times_names_literals_conflicts_and_late_hours(tmp_path):
    assignments = {'BIO-G1': ('Aula Á2', 1, 482, 487),
                   'BIO-G2': ('Aula Á2', 1, 487, 492),
                   'CHEM-G1': ('Aula Á2', 1, 485, 490),
                   'LATE-G1': ('B', 6, 1382, 1439)}
    path = tmp_path / 'schedule.pdf'
    ScheduleExporter(TimeModel.default()).to_pdf(assignments, path,
        course_name_by_code={'BIO': '=SUM(1,2) <b>Biología</b> & Français Ελληνικά Русский',
                             'CHEM': 'Química', 'LATE': 'Última sesión'}, pending_count=2)
    content = text(path)
    for value in ('08:02 - 08:07', '08:07 - 08:12', '23:02 - 23:59', 'CONFLICTO',
                  '=SUM(1,2)', '<b>Biología</b>', 'Français', 'Ελληνικά', 'Русский',
                  'Horario PARCIAL: 2 pendientes', '4 exportadas de 4 asignadas'):
        assert value in content
    assert not PdfReader(path).get_fields()
    assert len(PdfReader(path).pages) >= 2


def test_pdf_filtered_global_counts_filters_and_lab_exception(tmp_path):
    group = Group('BIO-G1', 5, 'REGULAR', course_name='Biología')
    group.lab_override = True
    path = tmp_path / 'filtered.pdf'
    ScheduleExporter(TimeModel.default()).to_pdf({'BIO-G1': ('A2', 2, 482, 487)}, path,
        groups=[group], filtered=True, total_assigned=10, pending_count=3,
        filters={'Buscar': 'BIO', 'Aula': 'A2', 'Día': 'Martes', 'Estado': 'Asignados'})
    content = text(path)
    for value in ('Vista filtrada', '1 exportadas de 10 asignadas', '3 pendientes',
                  'Buscar: BIO', 'Aula: A2', 'Día: Martes', 'EXCEPCIÓN LAB'):
        assert value in content


def test_pdf_long_names_repeat_context_without_truncation(tmp_path):
    path = tmp_path / 'long.pdf'
    name = ('Biología écologie Ελληνικά Русский ' * 150) + 'FINAL-NOMBRE'
    assignments = {f'BIO-G{i}': ('Sala principal', 1, 480+i*5, 485+i*5) for i in range(1, 31)}
    ScheduleExporter(TimeModel.default()).to_pdf(assignments, path,
        course_name_by_code={'BIO': name}, pending_count=4)
    reader = PdfReader(path)
    assert len(reader.pages) > 3
    for page in reader.pages:
        content = page.extract_text()
        assert 'SORTH 2.0.0' in content and 'Página ' in content
        assert '30 exportadas de 30 asignadas' in content and '4 pendientes' in content
        assert 'Sala principal' in content
        assert 'Inicio - Fin' in content
    content = text(path)
    assert content.count('FINAL-NOMBRE') == 30
    assert 'Continuación' in content


def test_pdf_empty_scope_and_unknown_pending_never_claim_complete(tmp_path):
    path = tmp_path / 'empty.pdf'
    ScheduleExporter(TimeModel.default()).to_pdf({}, path)
    content = text(path)
    assert 'Sin sesiones asignadas' in content
    assert 'pendientes no informados' in content
    assert 'Horario completo' not in content
    ScheduleExporter(TimeModel.default()).to_pdf({}, path, filtered=True,
                                               total_assigned=8, pending_count=2)
    assert '0 exportadas de 8 asignadas' in text(path)


@pytest.mark.parametrize('kwargs', [dict(filtered=True), dict(total_assigned=4), dict(pending_count=-1)])
def test_pdf_bad_context_does_not_write(tmp_path, kwargs):
    path = tmp_path / 'no.pdf'
    with pytest.raises(ValueError):
        ScheduleExporter(TimeModel.default()).to_pdf({}, path, **kwargs)
    assert not path.exists()


def test_pdf_failed_build_and_replace_preserve_destination(tmp_path, monkeypatch):
    from src.infrastructure import pdf_schedule_writer
    path = tmp_path / 'existing.pdf'
    path.write_bytes(b'previous document')
    exporter = ScheduleExporter(TimeModel.default())
    with pytest.raises(ValueError, match='caracteres'):
        exporter.to_pdf({'C-G1': ('A', 1, 480, 485)}, path,
                        course_name_by_code={'C': '日本語'})
    assert path.read_bytes() == b'previous document'
    monkeypatch.setattr(pdf_schedule_writer.os, 'replace', lambda *a: (_ for _ in ()).throw(PermissionError('locked')))
    with pytest.raises(PermissionError):
        exporter.to_pdf({'C-G1': ('A', 1, 480, 485)}, path)
    assert path.read_bytes() == b'previous document'
    assert set(tmp_path.iterdir()) == {path}


def test_pdf_font_and_runtime_dependency_are_shipped():
    root = Path(__file__).resolve().parents[2]
    assert (root / 'assets/fonts/DejaVuSans.ttf').stat().st_size > 100000
    assert (root / 'assets/fonts/DejaVu-LICENSE.txt').exists()
    assert 'reportlab==4.4.9' in (root / 'requirements.txt').read_text()
    assert "str(root / 'assets')" in (root / 'SORTH.spec').read_text()


@pytest.mark.parametrize('language', ['es', 'en'])
def test_pdf_catalog_translates_labels_and_days_but_never_data(tmp_path, language):
    from src.gui.locales import LANGUAGES
    path = tmp_path / 'localized.pdf'
    group = Group('CURSO-G1', 5, 'REGULAR', course_name='=Biología & Español Русский')
    group.lab_override = True
    ScheduleExporter(TimeModel.default()).to_pdf(
        {'CURSO-G1': ('Aula propia', 3, 482, 487)}, path, groups=[group],
        labels=LANGUAGES[language].messages, pending_count=2)
    output = text(path)
    expected = (['Classroom timetable', 'All assignments', 'PARTIAL schedule: 2 pending',
                 'Wednesday', 'Start - End', 'Full course name', 'LAB EXCEPTION', 'Page 1']
                if language == 'en' else
                ['Horario por aula', 'Todas las asignaciones', 'Horario PARCIAL: 2 pendientes',
                 'Miércoles', 'Inicio - Fin', 'Nombre completo del curso', 'EXCEPCIÓN LAB', 'Página 1'])
    assert all(value in output for value in expected)
    assert '=Biología & Español Русский' in output
    assert 'Aula propia' in output and 'CURSO-G1' in output and '08:02 - 08:07' in output


def test_pdf_incomplete_or_malformed_catalog_falls_back_to_source(tmp_path):
    path = tmp_path / 'fallback.pdf'
    ScheduleExporter(TimeModel.default()).to_pdf({'C-G1': ('A', 1, 480, 485)}, path,
        labels={'Día': 'Custom day', 'SORTH - Horario por aula': None,
                'Página {page}': 'Page {wrong}', 'Horario completo: 0 pendientes': '{broken'},
        pending_count=0)
    output = text(path)
    assert 'Custom day' in output
    assert 'Lunes' in output and 'Horario por aula' in output
    assert 'Página 1' in output and 'Horario completo: 0 pendientes' in output
