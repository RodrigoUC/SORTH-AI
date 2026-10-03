import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
import threading
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtCore import QSettings
from src.gui.main_window import MainWindow
from src.gui.scheduler_worker import SchedulingService
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course

def test_actual_worker_cancel_close_and_inputs(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path/'features.ini'), QSettings.Format.IniFormat)
    settings.setValue('features/pinned_sessions', True)
    window=MainWindow(SessionRepository(str(tmp_path/'session.db')),restore_session=False, feature_settings=settings)
    window._classrooms={'R':Classroom('R',30,'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('A',1,60,'REGULAR')])
    groups=window.course_manager.get_courses()[0].generate_groups()
    accepted={'A-G1':('R',1,480,540)}
    groups[0].assignment=accepted['A-G1']
    window._on_schedule_done(accepted,groups)
    window._toggle_pin('A-G1')
    original=(tmp_path/'session.db').read_bytes()
    entered, release=threading.Event(),threading.Event()
    def delayed(*args, **kwargs):
        entered.set(); release.wait(5)
        return {'A-G1':('R',2,480,540)}, groups
    monkeypatch.setattr(SchedulingService,'run',delayed)
    window._generate_schedule()
    assert entered.wait(2)
    assert not window.course_manager.isEnabled()
    assert not window.schedule_viewer.isEnabled()
    assert not window.btn_load.isEnabled()
    window._toggle_pin('A-G1')
    assert window.pinned_group_ids=={'A-G1'}
    window._cancel_generation()
    event=QCloseEvent(); window.closeEvent(event)
    assert not event.isAccepted()
    assert window._busy
    release.set()
    assert window._worker.wait(3000)
    for i in range(10): QApplication.processEvents(); time.sleep(.005)
    assert not window._busy
    assert window.current_schedule==accepted
    assert window.pinned_group_ids=={'A-G1'}
    assert (tmp_path/'session.db').read_bytes()==original
    window.close()


def test_cooperative_worker_stops_with_cancelled_not_error(tmp_path, monkeypatch):
    from src.gui.scheduler_worker import SchedulerWorker
    from src.scheduling.scheduler import Scheduler
    entered = threading.Event()
    original = Scheduler._build_domains
    def observed(self, *args, **kwargs):
        entered.set()
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Scheduler, '_build_domains', observed)
    worker = SchedulerWorker(None, [Course('BIG', 3000, 60, 'REGULAR')],
                             {'R': Classroom('R', 30, 'REGULAR')}, {}, 42)
    results, errors, cancellations = [], [], []
    worker.result_ready.connect(lambda *args: results.append(args))
    worker.error.connect(errors.append)
    worker.cancelled.connect(lambda: cancellations.append(True))
    worker.start()
    assert entered.wait(3)
    started = time.monotonic()
    worker.requestInterruption()
    assert worker.wait(2000), 'Synthetic fixture cancellation exceeds two-second test budget'
    elapsed = time.monotonic() - started
    QApplication.processEvents()
    assert cancellations == [True]
    assert not results and not errors
    assert elapsed < 2
