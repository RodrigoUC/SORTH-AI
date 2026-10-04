"""Only accepted session data crosses the GUI worker result boundary."""
from contextlib import contextmanager
from copy import deepcopy
import time

import pytest
from PyQt6.QtCore import QSettings, QThread
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.application.edit_history import fingerprint
from src.application.placement_suggestions import enumerate_placements
from src.application.scheduling_service import SchedulingService
from src.gui.main_window import MainWindow
from src.gui.scheduler_worker import SchedulerWorker
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.project_calendar import ProjectCalendar
from src.scheduling.scheduler import Scheduler
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources


def wait_for_generation(window):
    window._generate_schedule()
    worker = window._worker
    assert worker is not None and worker.wait(3000)
    deadline = time.monotonic() + 3
    while window._worker is not None and time.monotonic() < deadline:
        QApplication.processEvents()
    assert window._worker is None
    assert not window._busy


def test_worker_drops_only_search_domains_and_keeps_service_and_caller_isolated():
    courses = [Course('BIO', 2, 60, 'REGULAR', size=20, name='Biology'),
               Course('SPLIT', 1, 300, 'REGULAR', size=20),
               Course('LAB', 2, 60, 'LAB', size=20)]
    rooms = {'R': Classroom('R', 30, 'REGULAR')}
    resources = SchedulingResources((ResourceCatalog('teacher', True,
        (Resource('T', 'Teacher'),), (('BIO-G1', ('T',)), ('BIO-G2', ('T',)))),))
    request = dict(courses=courses, classrooms=rooms, resources=resources,
                   calendar=ProjectCalendar(), pinned_assignments={'LAB-G1': ('R', 1, 480, 540)},
                   lab_overrides={'LAB-G1'})
    caller_before = fingerprint(request)
    expected_assignments, expected_groups = SchedulingService(None, seed=42).run(**request)
    assert any(group.domain for group in expected_groups)
    expected_values = [{key: value for key, value in vars(group).items() if key != 'domain'}
                       for group in expected_groups]
    results, errors, threads = [], [], []
    worker = SchedulerWorker(None, restrictions={}, seed=42, **request)
    def receive(assignments, groups):
        results.append((assignments, groups))
        threads.append(QThread.currentThread())
    worker.result_ready.connect(receive)
    worker.error.connect(errors.append)
    worker.start()
    assert worker.wait(3000)
    QApplication.processEvents()
    assert not errors and len(results) == 1
    assignments, groups = results[0]
    assert assignments == expected_assignments
    assert [{key: value for key, value in vars(group).items() if key != 'domain'}
            for group in groups] == expected_values
    assert all(group.domain == [] for group in groups)
    assert any(group.domain for group in expected_groups)
    assert threads == [QApplication.instance().thread()]
    assert fingerprint(request) == caller_before
    by_id = {group.group_id: group for group in groups}
    assert by_id['LAB-G1'].pinned and by_id['LAB-G1'].lab_override
    assert by_id['LAB-G2'].unassigned_reason and not by_id['LAB-G2'].is_assigned()
    assert len([group for group in groups if group.parent_group_id]) == 3


@pytest.mark.parametrize('cancel_after', [1, 2])
def test_cancellation_during_result_cleanup_never_emits_result(monkeypatch, cancel_after):
    groups = Course('BIO', 2, 60, 'REGULAR').generate_groups()
    for group in groups:
        group.domain = [('search scratch', 1, 420)]
    monkeypatch.setattr(SchedulingService, 'run', lambda *args, **kwargs: ({}, groups))
    worker = SchedulerWorker(None, [], {}, {}, 42)
    monkeypatch.setattr(worker, 'isInterruptionRequested',
                        lambda: sum(not group.domain for group in groups) >= cancel_after)
    results, errors, cancellations = [], [], []
    worker.result_ready.connect(lambda *args: results.append(args))
    worker.error.connect(errors.append)
    worker.cancelled.connect(lambda: cancellations.append(True))
    worker.start()
    assert worker.wait(3000)
    QApplication.processEvents()
    assert cancellations == [True] and not errors and not results
    assert sum(not group.domain for group in groups) == cancel_after


@pytest.fixture
def generated_window(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)
    for feature in ('undo_redo', 'pinned_sessions', 'placement_suggestions'):
        settings.setValue('features/' + feature, True)
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')),
                        restore_session=False, feature_settings=settings)
    window._classrooms = {'R': Classroom('R', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('BIO', 4, 60, 'REGULAR', size=20)])
    window.chk_random_seed.setChecked(False)
    window.seed_input.setValue(42)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.StandardButton.Cancel)
    wait_for_generation(window)
    assert window._generation_result_committed
    assert all(not group.domain for group in window.current_groups)
    yield window
    window._unsaved = False
    window.close()


@pytest.mark.parametrize('failure', ['render', 'commit'])
def test_regeneration_rollback_preserves_accepted_empty_domain_groups(generated_window, monkeypatch, failure):
    window = generated_window
    first = dict(window.current_schedule)
    window.schedule_viewer.tabs.setCurrentIndex(1)
    wait_for_generation(window)
    assert window._generation_result_committed and window.current_schedule == first
    assert all(not group.domain for group in window.current_groups)
    window._toggle_pin('BIO-G1')
    assert window._history.can_undo
    before = fingerprint(window._capture_edit_state())
    disk = fingerprint(window._repo.load_session())
    previous_groups = window.current_groups
    group_values = [deepcopy(vars(group)) for group in previous_groups]
    if failure == 'render':
        display = window.schedule_viewer.display_schedule
        calls = []
        def fail_once(*args, **kwargs):
            calls.append(True)
            if len(calls) == 1:
                raise RuntimeError('Injected result rendering failure')
            return display(*args, **kwargs)
        monkeypatch.setattr(window.schedule_viewer, 'display_schedule', fail_once)
    else:
        connect = window._repo._connect
        @contextmanager
        def fail_commit():
            with connect() as connection:
                yield connection
                if connection.total_changes:
                    raise OSError('Injected late commit failure')
        monkeypatch.setattr(window._repo, '_connect', fail_commit)
    wait_for_generation(window)
    assert not window._generation_result_committed and not window._restore_failed
    assert window.current_groups is previous_groups
    assert [vars(group) for group in previous_groups] == group_values
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == disk
    assert window._history.can_undo
    assert window.schedule_viewer._assignments == window.current_schedule


def test_suggestions_rebuild_domains_after_real_generation_and_survive_history(generated_window, monkeypatch):
    window = generated_window
    window._on_group_removed('BIO-G2')
    assert 'BIO-G2' not in window.current_schedule
    assert all(not group.domain for group in window.current_groups)
    before = fingerprint(window._capture_edit_state())
    build = Scheduler._build_domains
    rebuilt = []
    def observe(self, state, groups, **kwargs):
        assert all(not group.domain for group in groups)
        result = build(self, state, groups, **kwargs)
        rebuilt.extend(group.group_id for group in groups if group.domain)
        return result
    monkeypatch.setattr(Scheduler, '_build_domains', observe)
    options = enumerate_placements('BIO-G2', **window._placement_inputs())
    assert rebuilt == ['BIO-G2'] and options.placements
    assert fingerprint(window._capture_edit_state()) == before
    assert all(not group.domain for group in window.current_groups)
    assert window._apply_placement_option(options, options.placements[0])
    after = fingerprint(window._capture_edit_state())
    assert window._travel_history(True)
    assert fingerprint(window._capture_edit_state()) == before
    assert window._travel_history(False)
    assert fingerprint(window._capture_edit_state()) == after
    assert window._repo.load_session()['assignments'] == window.current_schedule
    assert all(not group.domain for group in window.current_groups)
