"""Synthetic import timing and Linux Qt capture; not a Windows certification.

Run from project_root: python tools/benchmark_excel_import.py --output /tmp/import-qa
"""
import argparse
import json
import platform
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
import openpyxl
from PyQt6.QtCore import QSettings, QTimer, PYQT_VERSION_STR, QT_VERSION_STR
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.gui.import_preview_dialog import ImportPreviewDialog
from src.gui.i18n import language_manager
from src.gui import import_worker
from src.infrastructure.import_candidate import read_candidate
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom


def workbook(path, rows):
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'# DE AULA': ['R'], 'CAPACIDAD': [30]}).to_excel(writer, sheet_name='Aulas', index=False)
        pd.DataFrame({'Curso': [f'SYN-{index:05}' for index in range(rows)],
                      'Nombre de Curso': [f'Synthetic course {index}' for index in range(rows)],
                      'Horas': ['0800-0900']*rows, 'Aula': ['R']*rows}).to_excel(writer, sheet_name='Cursos', index=False)


def run(output, sizes):
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    report = {'platform': platform.platform(), 'python': platform.python_version(),
              'pandas': pd.__version__, 'openpyxl': openpyxl.__version__,
              'pyqt': PYQT_VERSION_STR, 'qt': QT_VERSION_STR,
              'method': '5 ms QTimer; actual background import through atomic persistence and Qt table replacement; synthetic unique courses; one observation per size, not a throughput guarantee.',
              'measurements': []}
    with tempfile.TemporaryDirectory(prefix='sorth-import-') as temporary:
        root = Path(temporary)
        for count in sizes:
            path = root/f'{count}.xlsx'
            workbook(path, count)
            window = MainWindow(SessionRepository(str(root/f'{count}.db')), restore_session=False,
                                feature_settings=QSettings(str(root/f'{count}.ini'), QSettings.Format.IniFormat))
            window.resize(1200, 800)
            window.show()
            app.processEvents()
            stages = []
            original_reader = import_worker.read_candidate
            original_commit = window._commit_import
            def measured_reader(*args, **kwargs):
                started = time.perf_counter()
                value = original_reader(*args, **kwargs)
                stages.append(('reader' if args[2] is None else 'verify', time.perf_counter() - started))
                return value
            def measured_commit(*args):
                started = time.perf_counter()
                value = original_commit(*args)
                stages.append(('persist_and_present', time.perf_counter() - started))
                return value
            import_worker.read_candidate = measured_reader
            window._commit_import = measured_commit
            ticks = [time.perf_counter()]
            timer = QTimer()
            timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
            timer.start(5)
            started = time.perf_counter()
            window._import.start(str(path))
            dispatch_ms = (time.perf_counter()-started)*1000
            while window._import.active or window._import.worker is not None:
                app.processEvents()
                time.sleep(.001)
            app.processEvents()
            ticks.append(time.perf_counter())
            timer.stop()
            result = {'rows': count, 'xlsx_bytes': path.stat().st_size,
                      'start_return_ms': round(dispatch_ms, 2),
                      'total_ms': round((time.perf_counter()-started)*1000, 2),
                      'timer_ticks': len(ticks)-2,
                      'max_event_loop_gap_ms': round(max(b-a for a,b in zip(ticks, ticks[1:]))*1000, 2),
                      **{name+'_ms': round(duration*1000, 2) for name, duration in stages}}
            report['measurements'].append(result)
            print(json.dumps(result), flush=True)
            import_worker.read_candidate = original_reader
            window.close()
        # Preview captures use only artificial courses and rooms.
        path = root/'preview.xlsx'
        workbook(path, 3)
        window = MainWindow(SessionRepository(str(root/'preview.db')), restore_session=False,
                            feature_settings=QSettings(str(root/'preview.ini'), QSettings.Format.IniFormat))
        window._classrooms = {'R': Classroom('R', 20, 'REGULAR'), 'OLD': Classroom('OLD', 10, 'REGULAR')}
        window.course_manager.load_courses_from_excel([Course('SYN-00000', 2, 90, 'REGULAR'), Course('OLD',1,60,'REGULAR')])
        window.classroom_restrictions = {'R': {'SYN-00000'}}
        window.current_schedule = {'OLD-G1': ('OLD', 1, 480, 540)}
        candidate = read_candidate(str(path), lambda: False)
        for language in ('es','en'):
            language_manager().set_language(language, persist=False)
            dialog = ImportPreviewDialog(window, candidate, set())
            dialog.show()
            app.processEvents()
            dialog.grab().save(str(output/f'preview-{language}.png'))
            dialog.close()
        window.resize(960,640)
        window.show()
        window._set_import_busy(True)
        window.status_bar.showMessage('Reading and validating Excel… Your current session is preserved.')
        app.processEvents()
        window.grab().save(str(output/'loading-en-960.png'))
        window._set_import_busy(False)
        window._unsaved=False
        window.close()
    (output/'measurements.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows', type=int, nargs='+', default=[100, 1000, 5000, 10000])
    args = parser.parse_args()
    if not all(1 <= value <= 10000 for value in args.rows):
        parser.error('Each row count must be between 1 and 10000')
    run(args.output, args.rows)
