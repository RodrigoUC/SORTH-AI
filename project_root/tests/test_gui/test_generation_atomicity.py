from contextlib import contextmanager
from copy import deepcopy
import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox
from src.application.edit_history import fingerprint
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom


@pytest.fixture
def window(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path/'settings.ini'), QSettings.Format.IniFormat)
    settings.setValue('features/undo_redo', True)
    w = MainWindow(SessionRepository(str(tmp_path/'session.db')), restore_session=False,
                   feature_settings=settings)
    w._classrooms = {'R': Classroom('R', 30, 'REGULAR')}
    w.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])
    w._on_schedule_done({'BIO-G1': ('R', 1, 480, 540)}, w.course_manager.courses[0].generate_groups())
    course = deepcopy(w.course_manager.courses[0]); course.name = 'Edited'
    assert w._commit_course_edit([course], 'Edit')
    candidate = w._capture_edit_state()
    candidate.update(assignments={'BIO-G1': ('R', 1, 480, 540)}, schedule_present=True)
    assert w._commit_edit(candidate, 'Place session')
    assert w._history.can_undo
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.StandardButton.Cancel)
    yield w
    w._unsaved = False
    w.close()


def generate(window):
    window._on_schedule_done({'BIO-G1': ('R', 1, 600, 660)}, window.course_manager.courses[0].generate_groups())


def test_generation_renderer_failure_rolls_back_model_disk_and_history(window, monkeypatch):
    before, disk = fingerprint(window._capture_edit_state()), fingerprint(window._repo.load_session())
    refs = window.current_schedule, window.current_groups, window.course_manager.courses
    original = window.schedule_viewer.display_schedule
    calls = []
    def fail_once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1: raise RuntimeError('injected renderer failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(window.schedule_viewer, 'display_schedule', fail_once)
    generate(window)
    assert len(calls) == 2
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == disk
    assert all(a is b for a, b in zip(refs, (window.current_schedule, window.current_groups, window.course_manager.courses)))
    assert window._history.can_undo and not window._restore_failed
    assert not window._unsaved
    assert window.schedule_viewer._assignments == (window.current_schedule or {})


def test_generation_commit_failure_after_render_rolls_back(window, monkeypatch):
    before, disk = fingerprint(window._capture_edit_state()), fingerprint(window._repo.load_session())
    original = window._repo._connect
    @contextmanager
    def fail_commit():
        with original() as con:
            yield con
            if con.total_changes: raise OSError('commit failure')
    with monkeypatch.context() as patch:
        patch.setattr(window._repo, '_connect', fail_commit)
        generate(window)
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == disk
    assert window._history.can_undo and not window._restore_failed


def test_permanent_generation_renderer_failure_keeps_recovery_locked_after_worker_exit(window, monkeypatch):
    before, disk = fingerprint(window._capture_edit_state()), fingerprint(window._repo.load_session())
    monkeypatch.setattr(window.schedule_viewer, 'display_schedule', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('broken view')))
    generate(window)
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == disk
    assert window._restore_failed and window._busy and window._history.can_undo
    class Worker:
        def deleteLater(self): pass
    worker = Worker(); window._worker = worker
    window._generation_finished(worker)
    assert window._restore_failed and window._busy
    assert not window.btn_generate.isEnabled() and not window.course_manager.isEnabled()
    assert not window._retry_save_button.isHidden()
    assert window.btn_generate.text() == 'Recuperación pendiente'


def test_successful_generation_commits_and_resets_history(window):
    generate(window)
    assert window.current_schedule == window._repo.load_session()['assignments'] == {'BIO-G1': ('R', 1, 600, 660)}
    assert not window._history.can_undo and window._history.reset_reason == 'generation'
    assert not window._unsaved and window.tabs.currentIndex() == 1


def test_postcommit_generation_feedback_failure_is_truthfully_saved(window, monkeypatch):
    monkeypatch.setattr(window, '_show_schedule_status', lambda: (_ for _ in ()).throw(RuntimeError('feedback failed')))
    generate(window)
    assert window.current_schedule == window._repo.load_session()['assignments'] == {'BIO-G1': ('R', 1, 600, 660)}
    assert window._restore_failed and not window._unsaved
    assert 'se guardó' in window._save_state_label.text()
    assert not window._history.can_undo


def test_generation_write_failure_is_retryable_without_history_loss(window, monkeypatch):
    before = fingerprint(window._capture_edit_state())
    with monkeypatch.context() as patch:
        patch.setattr(window._repo, 'save_session', lambda **kwargs: (_ for _ in ()).throw(OSError('disk full')))
        generate(window)
    assert fingerprint(window._capture_edit_state()) == before
    assert window._history.can_undo
    generate(window)
    assert window.current_schedule == window._repo.load_session()['assignments']
    assert window.current_schedule['BIO-G1'][2] == 600
    assert not window._history.can_undo


def test_actual_worker_renderer_failure_does_not_escape_qt_slot(window, monkeypatch):
    import time
    from PyQt6.QtWidgets import QApplication
    from src.gui.scheduler_worker import SchedulingService
    before = fingerprint(window._capture_edit_state())
    monkeypatch.setattr(SchedulingService, 'run', lambda *a, **k:
        ({'BIO-G1': ('R', 1, 600, 660)}, window.course_manager.courses[0].generate_groups()))
    original = window.schedule_viewer.display_schedule
    calls = []
    def fail_once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1: raise RuntimeError('worker result rendering failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(window.schedule_viewer, 'display_schedule', fail_once)
    window._generate_schedule()
    assert window._worker.wait(3000)
    deadline = time.monotonic() + 3
    while window._worker is not None and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(.005)
    assert window._worker is None and not window._busy
    assert fingerprint(window._capture_edit_state()) == before
    assert window._history.can_undo
