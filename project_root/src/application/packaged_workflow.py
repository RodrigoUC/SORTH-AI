"""Deterministic packaged workflow checks; isolated synthetic data only."""
import csv
import hashlib
from time import monotonic
from openpyxl import Workbook, load_workbook
from PyQt6.QtCore import QTimer, QEventLoop
from PyQt6.QtWidgets import QApplication, QDialog
from ..gui.main_window import MainWindow
from ..infrastructure.excel_reader import ExcelReader, ExcelImportError
from ..infrastructure.session_repository import SessionRepository
from ..infrastructure.schedule_exporter import ScheduleExporter
from ..scheduling.time_model import TimeModel
from .scheduling_service import SchedulingService


def verify_workflow(window, output, result):
    course = window.course_manager.get_courses()[0]
    edited_name = 'Revisión Ω / 日本語'
    def edit():
        dialog = QApplication.activeModalWidget()
        if dialog is not None and hasattr(dialog, 'name_edit'):
            dialog.name_edit.setText(edited_name)
            dialog.accept()
    QTimer.singleShot(0, edit)
    window.course_manager.edit_course_by_code(course.code)
    assert window.course_manager.get_courses()[0].name == edited_name
    # Editing deliberately invalidates the old schedule; regenerate through
    # the real background worker before persisting and reopening.
    loop = QEventLoop()
    probe = QTimer()
    probe.timeout.connect(lambda: loop.quit() if not window._busy else None)
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    window._generate_schedule()
    probe.start(25)
    deadline.start(60000)
    loop.exec()
    probe.stop()
    deadline.stop()
    assert not window._busy and window.current_schedule, 'Regeneration failed'
    assert window._save_session(), 'Edited session failed to save'
    result['stages'].append('course_dialog_edit_save')
    def accept_restore():
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, QDialog):
            dialog.accept()
    QTimer.singleShot(0, accept_restore)
    reopened = MainWindow(repo=SessionRepository(str(output / 'smoke-session.db')))
    try:
        assert reopened.course_manager.get_courses()[0].name == edited_name
        assert reopened.current_schedule == window.current_schedule
        result['stages'].append('new_window_restore')
        exporter = ScheduleExporter(TimeModel.default())
        names = {c.code: c.name for c in reopened.course_manager.get_courses()}
        exporter.to_excel(reopened.current_schedule, str(output / 'reopened.xlsx'), groups=reopened.current_groups, course_name_by_code=names)
        exporter.to_csv(reopened.current_schedule, str(output / 'reopened.csv'), groups=reopened.current_groups, course_name_by_code=names)
        with (output / 'reopened.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == len(reopened.current_schedule)
        assert any(row['Nombre Curso'] == edited_name for row in rows)
        book = load_workbook(output / 'reopened.xlsx', read_only=True)
        assert book['Asignaciones'].max_row == len(rows) + 1
        book.close()
        result['stages'].append('reopened_export_content')
    finally:
        reopened.close()
    db = output / 'smoke-session.db'
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    invalid = output / 'corrupt.xlsx'
    invalid.write_bytes(b'not an Excel workbook')
    bad_book = Workbook()
    bad_book.active.title = 'Aulas'
    bad_book.active.append(['# DE AULA', 'CAPACIDAD'])
    bad_book.active.append(['R1', -1])
    bad_courses = bad_book.create_sheet('Cursos')
    bad_courses.append(['Curso', 'Horas'])
    bad_courses.append(['BAD', 'not-time'])
    malformed = output / 'invalid-values.xlsx'
    bad_book.save(malformed)
    for path in [invalid, malformed, output / 'missing.xlsx']:
        try:
            ExcelReader(str(path)).load_validated()
        except ExcelImportError:
            pass
        else:
            raise AssertionError('Bad workbook was accepted')
    assert before == hashlib.sha256(db.read_bytes()).hexdigest()
    result['stages'].append('invalid_input_preserves_session')
    started = monotonic()
    book = Workbook()
    rooms = book.active
    rooms.title = 'Aulas'
    rooms.append(['# DE AULA', 'CAPACIDAD'])
    for i in range(50):
        rooms.append([f'R{i:03}', 60])
    courses = book.create_sheet('Cursos')
    courses.append(['Curso', 'Nombre de Curso', 'Horas'])
    for i in range(500):
        courses.append([f'C{i:04}', f'Synthetic {i}', '0800-0900'])
    large = output / 'large-input.xlsx'
    book.save(large)
    imported = ExcelReader(str(large)).load_validated()
    assert len(imported.courses) == 500 and len(imported.classrooms) == 50
    assignments, groups = SchedulingService(None, seed=42).run(courses=imported.courses, classrooms=imported.classrooms)
    assert len(assignments) == len(groups) == 500
    exporter.to_csv(assignments, str(output / 'large.csv'), groups=groups)
    with (output / 'large.csv').open(encoding='utf-8-sig', newline='') as stream:
        assert len(list(csv.DictReader(stream))) == 500
    result['large_fixture'] = {'courses': 500, 'rooms': 50, 'assigned': len(assignments), 'elapsed_seconds': round(monotonic()-started, 3)}
    result['stages'].append('large_workbook_schedule_export')
