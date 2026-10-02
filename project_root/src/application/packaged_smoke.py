"""Opt-in executable validation against bundled sample data and an isolated session.

Never opens or modifies the normal user's session. Results go to the explicitly
requested output directory; the CI launcher enforces its own timeout as well.
"""
import json
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import QTimer

from ..gui.main_window import MainWindow
from ..gui.i18n import language_manager
from ..infrastructure.excel_reader import ExcelReader
from ..infrastructure.schedule_exporter import ScheduleExporter
from ..infrastructure.session_repository import SessionRepository
from ..scheduling.time_model import TimeModel


def run_smoke_test(app, output_dir: Path) -> int:
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / 'smoke-result.json'
    if result_path.exists() or (output_dir / 'smoke-session.db').exists():
        raise ValueError('Use a fresh smoke-output directory to avoid stale results.')
    source_root = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
    result = {'ok': False, 'frozen': bool(getattr(sys, 'frozen', False)), 'stages': []}
    if result['frozen']:
        result['build_identity'] = json.loads((source_root / 'build-identity.json').read_text(encoding='utf-8'))
    repo = SessionRepository(str(output_dir / 'smoke-session.db'))
    window = MainWindow(repo=repo, restore_session=False)
    window.show()
    completed = False

    def finish(error=None):
        nonlocal completed
        if completed:
            return
        completed = True
        poll.stop()
        deadline.stop()
        if error:
            result['error'] = str(error)
        result['ok'] = error is None
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        if window._worker is None or not window._worker.isRunning():
            window.close()
        app.exit(0 if result['ok'] else 1)

    def check_done():
        if window._busy:
            return
        poll.stop()
        try:
            if not window.current_schedule:
                raise RuntimeError('The bundled sample produced no schedule.')
            assignments = window.current_schedule
            groups = window.current_groups
            if len(assignments) != len(groups):
                raise RuntimeError(f'Only {len(assignments)}/{len(groups)} sample groups assigned.')
            result.update(assigned=len(assignments), groups=len(groups), classrooms=len(window._classrooms))
            result['stages'].append('background_schedule')
            exporter = ScheduleExporter(TimeModel.default())
            exporter.to_excel(assignments, str(output_dir / 'schedule.xlsx'), groups=groups)
            exporter.to_csv(assignments, str(output_dir / 'schedule.csv'), groups=groups)
            if not all((output_dir / name).stat().st_size > 0 for name in ('schedule.xlsx', 'schedule.csv')):
                raise RuntimeError('An export is empty.')
            result['stages'].append('excel_csv_export')
            saved = repo.load_session()
            if saved['assignments'] != assignments:
                raise RuntimeError('SQLite roundtrip changed assignments.')
            result['stages'].append('sqlite_roundtrip')
            manager = language_manager()
            previous_language = manager.language
            try:
                for language, label in [('es', 'Generar horario'), ('en', 'Generate schedule')]:
                    manager.set_language(language, persist=False)
                    if window.btn_generate.text() != label or window.current_schedule != assignments:
                        raise RuntimeError('Language switching changed data or failed to translate controls.')
                    if not window.grab().save(str(output_dir / f'schedule-{language}.png')):
                        raise RuntimeError('Could not capture the localized Qt window.')
                result['stages'].append('language_switch_es_en')
            finally:
                manager.set_language(previous_language, persist=False)
            if not window.grab().save(str(output_dir / 'schedule.png')):
                raise RuntimeError('Could not capture the rendered Qt window.')
            result['stages'].append('qt_render')
            from .packaged_workflow import verify_workflow
            verify_workflow(window, output_dir, result)
            finish()
        except Exception:
            finish(traceback.format_exc())

    def start():
        try:
            sample = source_root / 'data/input/Cursos_Ejemplo.xlsx'
            reader = ExcelReader(str(sample))
            window._classrooms = reader.load_classrooms()
            window.course_manager.load_courses_from_excel(reader.load_courses(known_classrooms=set(window._classrooms)))
            window.excel_path = str(sample)
            window.excel_path_label.setText(sample.name)
            result['stages'].append('bundled_excel_import')
            window._generate_schedule()
            # Avoid interactive error dialogs in this explicitly automated mode.
            window._worker.error.disconnect(window._on_schedule_error)
            window._worker.error.connect(lambda message: finish(message))
            poll.start(25)
            deadline.start(60000)
        except Exception:
            finish(traceback.format_exc())

    poll = QTimer()
    poll.timeout.connect(check_done)
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(lambda: finish('Timed out after 60 seconds.'))
    QTimer.singleShot(0, start)
    code = app.exec()
    # A timed-out worker must not be destroyed while still executing. The CI
    # process launcher has a hard timeout for a genuinely wedged worker.
    if window._worker is not None:
        window._worker.wait()
    return code
