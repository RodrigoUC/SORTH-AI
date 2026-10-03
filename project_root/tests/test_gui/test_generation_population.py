"""The completion boundary must not let worker metadata redefine the request."""
from copy import deepcopy

import pytest

from src.application.edit_history import fingerprint
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def window(tmp_path):
    win = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    win._classrooms = {'A': Classroom('A', 20, 'REGULAR')}
    win.course_manager.load_courses_from_excel([Course('C', 2, 60, 'REGULAR')])
    groups = win.course_manager.get_courses()[0].generate_groups()
    win._on_schedule_done({'C-G1': ('A', 1, 420, 480)}, groups)
    yield win
    win._unsaved = False
    win.close()


@pytest.mark.parametrize('corruption', ['missing', 'empty', 'extra', 'duplicate', 'duration',
                                      'size', 'split', 'missing_attribute', 'wrong_container'])
def test_invalid_population_preserves_previous_schedule(window, monkeypatch, corruption):
    groups = window.course_manager.get_courses()[0].generate_groups()
    if corruption == 'missing': groups.pop()
    elif corruption == 'empty': groups.clear()
    elif corruption == 'extra': groups += Course('EXTRA', 1, 60, 'REGULAR').generate_groups()
    elif corruption == 'duplicate': groups[1] = deepcopy(groups[0])
    elif corruption == 'duration': groups[1].duration_min = 120
    elif corruption == 'size': groups[1].size = 0.5
    elif corruption == 'split': groups[1].parent_group_id = 'C'
    elif corruption == 'missing_attribute': del groups[1].course_name
    elif corruption == 'wrong_container': groups = tuple(groups)
    state = fingerprint(window._capture_edit_state())
    disk = fingerprint(window._repo.load_session())
    history = deepcopy(vars(window._history))
    errors = []
    monkeypatch.setattr(window, '_on_schedule_error', errors.append)
    monkeypatch.setattr(window, '_persist_edit_state', lambda *a, **k: pytest.fail('Must not persist'))
    window._on_schedule_done({'C-G1': ('A', 2, 420, 480)}, groups)
    assert errors
    assert fingerprint(window._capture_edit_state()) == state
    assert fingerprint(window._repo.load_session()) == disk
    assert vars(window._history) == history
    assert not window._generation_result_committed
    assert '1/2' in window.status_bar.currentMessage()


@pytest.mark.parametrize('count', [0, 1, 3])
def test_split_population_accepts_partial_and_complete_results(window, count):
    course = Course('S', 1, 300, 'REGULAR')
    window.course_manager.load_courses_from_excel([course])
    groups = course.generate_groups()
    assert len(groups) == 3
    assignments = {g.group_id: ('A', i + 1, 420, 420 + g.duration_min)
                   for i, g in enumerate(groups[:count])}
    window._on_schedule_done(assignments, groups)
    assert len(window.current_groups) == 3
    assert window.current_schedule == assignments
    assert f'{count}/3' in window.status_bar.currentMessage()
    assert ('parcial' in window.status_bar.currentMessage()) == (count < 3)
    assert (window._repo.load_session()['assignments'] or {}) == assignments


@pytest.mark.parametrize('reordered', [False, True])
@pytest.mark.parametrize('days,assigned_count', [(3, 3), (4, 4)])
def test_real_solver_split_resource_results_are_accepted(window, reordered, days, assigned_count):
    from src.application.scheduling_service import SchedulingService
    from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources

    courses = [Course('FLEX', 1, 60, 'REGULAR'),
               Course('SPLIT', 1, 300, 'REGULAR', suggested_classroom='A',
                      preferred_day='Lunes', preferred_start_min=480)]
    window.course_manager.load_courses_from_excel(courses)
    groups = [g for course in courses for g in course.generate_groups()]
    window.resources = SchedulingResources((ResourceCatalog(
        'teacher', True, (Resource('T', 'Synthetic teacher',
            tuple((day, 480, 660) for day in range(1, days + 1))),),
        tuple((g.group_id, ('T',)) for g in groups)),))
    assignments, result = SchedulingService(None, seed=42).run(
        courses=courses, classrooms=window._classrooms, resources=window.resources)
    assert len(assignments) == assigned_count
    if reordered:
        result.reverse()
    window._on_schedule_done(assignments, result)
    assert window._generation_result_committed
    assert window.current_schedule == assignments
    assert {g.group_id for g in window.current_groups} == {g.group_id for g in groups}
    assert f'{assigned_count}/4' in window.status_bar.currentMessage()
    assert window._repo.load_session()['resources'] == window.resources


def test_real_solver_preserves_pinned_manual_lab_override(window):
    from src.application.scheduling_service import SchedulingService

    course = Course('LAB', 2, 60, 'LAB')
    window.course_manager.load_courses_from_excel([course])
    groups = course.generate_groups()
    assignments = {'LAB-G1': ('A', 1, 480, 540)}
    groups[0].lab_override = True
    window._on_schedule_done(assignments, groups)
    window.pinned_group_ids = {'LAB-G1'}
    result, groups = SchedulingService(None).run(
        courses=[course], classrooms=window._classrooms,
        pinned_assignments=assignments, lab_overrides={'LAB-G1'})
    assert groups[0].pinned and groups[0].lab_override
    window._on_schedule_done(result, groups)
    assert window._generation_result_committed
    assert window.current_schedule == assignments
    assert window.current_groups[0].lab_override and window.current_groups[0].pinned
    assert not window.current_groups[1].is_assigned()
    assert '1/2' in window.status_bar.currentMessage()
    assert window._repo.load_session()['lab_overrides'] == {'LAB-G1'}


def test_cancelled_corrupt_result_is_ignored_before_validation(window, monkeypatch):
    window._generation_cancelled = True
    before = fingerprint(window._capture_edit_state())
    monkeypatch.setattr(window, '_on_schedule_error', lambda *a: pytest.fail('Cancelled result'))
    window._on_schedule_done({}, [])
    assert fingerprint(window._capture_edit_state()) == before


@pytest.mark.parametrize('language,expected', [('es', 'grupos solicitados'), ('en', 'requested groups')])
def test_population_error_is_localized(window, monkeypatch, language, expected):
    from src.gui.i18n import language_manager
    manager = language_manager()
    previous = manager.language
    errors = []
    monkeypatch.setattr(window, '_on_schedule_error', errors.append)
    try:
        manager.set_language(language, persist=False)
        window._on_schedule_done({}, [])
        assert expected in str(errors[0])
    finally:
        manager.set_language(previous, persist=False)


def test_empty_result_cannot_erase_all_requested_pending_groups(window, monkeypatch):
    before = fingerprint(window._capture_edit_state())
    disk = fingerprint(window._repo.load_session())
    errors = []
    monkeypatch.setattr(window, '_on_schedule_error', errors.append)
    window._on_schedule_done({}, [])
    assert errors
    assert fingerprint(window._capture_edit_state()) == before
    assert fingerprint(window._repo.load_session()) == disk


def test_stale_worker_result_is_ignored_without_population_error(window, monkeypatch):
    from PyQt6.QtCore import QObject, pyqtSignal
    from src.gui import main_window

    class Worker(QObject):
        result_ready = pyqtSignal(object, object)
        finished = pyqtSignal()
        error = pyqtSignal(str)
        cancelled = pyqtSignal()

        def __init__(self, **kwargs):
            super().__init__()

        def start(self):
            pass

    monkeypatch.setattr(main_window, 'SchedulerWorker', Worker)
    monkeypatch.setattr(window, '_on_schedule_error', lambda *a: pytest.fail('Stale result'))
    before = fingerprint(window._capture_edit_state())
    window._generate_schedule()
    stale = window._worker
    window._worker = None
    stale.result_ready.emit({}, [])
    stale.finished.emit()
    window._set_busy(False)
    assert fingerprint(window._capture_edit_state()) == before
