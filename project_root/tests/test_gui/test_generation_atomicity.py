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
    monkeypatch.undo()
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


@pytest.mark.parametrize('failure', ['capture', 'reset'])
def test_postcommit_history_failure_is_guarded_and_never_reverts_saved_result(window, monkeypatch, failure):
    if failure == 'capture':
        original = window._capture_edit_state
        calls = []
        def capture():
            calls.append(1)
            if len(calls) == 3:
                raise RuntimeError('postcommit capture failed')
            return original()
        monkeypatch.setattr(window, '_capture_edit_state', capture)
    else:
        monkeypatch.setattr(window._history, 'reset', lambda *a, **k:
            (_ for _ in ()).throw(RuntimeError('postcommit reset failed')))
    generate(window)
    assert window.current_schedule == window._repo.load_session()['assignments'] == {'BIO-G1': ('R', 1, 600, 660)}
    assert window._restore_failed and window._busy and not window._unsaved
    assert 'se guardó' in window._save_state_label.text()
    assert not window._travel_history(True)
    if failure == 'capture':
        assert not window._history.can_undo


def finish_worker(window, close_requested=False):
    class Worker:
        disposed = 0
        def deleteLater(self): self.disposed += 1
    worker = Worker()
    window._worker = worker
    window._close_after_generation = close_requested
    window._generation_finished(worker)
    assert worker.disposed == 1
    assert window._worker is None
    assert not window._close_after_generation
    return worker


def test_persistent_history_render_failure_is_guarded_through_worker_finish(window, monkeypatch):
    before, disk = fingerprint(window._capture_edit_state()), fingerprint(window._repo.load_session())
    monkeypatch.setattr(window, '_update_history_actions', lambda:
        (_ for _ in ()).throw(RuntimeError('persistent history presentation failure')))
    generate(window)
    assert window._restore_failed and not window._generation_result_committed
    closes = []
    monkeypatch.setattr(window, 'close', lambda: closes.append(True))
    window._import.closing = True
    finish_worker(window, close_requested=True)
    assert not closes and not window._import.closing
    assert window._busy and window._restore_failed
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == disk
    assert 'Los datos se conservaron' in window._save_state_label.text()
    assert not window._retry_save_button.isHidden()
    assert window._progress.isHidden() and window._cancel_button.isHidden()
    assert not window.btn_generate.isEnabled()


def test_postcommit_finish_failure_retains_saved_wording_and_defers_close(window, monkeypatch):
    generate(window)
    assert window._generation_result_committed
    monkeypatch.setattr(window, '_update_history_actions', lambda:
        (_ for _ in ()).throw(RuntimeError('finish presentation failed')))
    closes = []
    monkeypatch.setattr(window, 'close', lambda: closes.append(True))
    finish_worker(window, close_requested=True)
    assert not closes
    assert window._busy and window._restore_failed and not window._unsaved
    assert window.current_schedule == window._repo.load_session()['assignments']
    assert 'se guardó' in window._save_state_label.text()


def test_normal_cancelled_worker_finish_disposes_and_honors_deferred_close(window, monkeypatch):
    window._generation_cancelled = True
    window._generation_result_committed = False
    closes = []
    monkeypatch.setattr(window, 'close', lambda: closes.append(True))
    finish_worker(window, close_requested=True)
    assert closes == [True]
    assert not window._busy and not window._restore_failed


def test_deferred_close_failure_enters_truthful_recovery(window, monkeypatch):
    generate(window)
    monkeypatch.setattr(window, 'close', lambda:
        (_ for _ in ()).throw(RuntimeError('close presentation failed')))
    finish_worker(window, close_requested=True)
    assert window._restore_failed and window._busy and not window._import.closing
    assert 'se guardó' in window._save_state_label.text()


@pytest.mark.parametrize('control,method', [('_progress', 'setVisible'), ('btn_generate', 'setText')])
def test_worker_finish_tolerates_persistent_recovery_widget_failure(window, monkeypatch, control, method):
    generate(window)
    window._committed_view_failure(RuntimeError('initial recovery'))
    monkeypatch.setattr(getattr(window, control), method, lambda *a:
        (_ for _ in ()).throw(RuntimeError('recovery widget failed')))
    finish_worker(window)
    assert window._restore_failed and window._busy
    assert 'se guardó' in window._save_state_label.text()
    assert 'recovery widget failed' in window._save_error
    assert not window._retry_save_button.isHidden()


def test_actual_worker_persistent_result_and_finish_failure_never_escape(window, monkeypatch):
    import time
    from PyQt6.QtWidgets import QApplication
    from src.gui.scheduler_worker import SchedulingService
    before = fingerprint(window._capture_edit_state())
    monkeypatch.setattr(SchedulingService, 'run', lambda *a, **k:
        ({'BIO-G1': ('R', 1, 600, 660)}, window.course_manager.courses[0].generate_groups()))
    window._generate_schedule()
    assert window._worker.wait(3000)
    monkeypatch.setattr(window, '_update_history_actions', lambda:
        (_ for _ in ()).throw(RuntimeError('persistent history failure')))
    deadline = time.monotonic() + 3
    while window._worker is not None and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(.005)
    assert window._worker is None
    assert window._restore_failed and window._busy
    assert fingerprint(window._capture_edit_state()) == before
