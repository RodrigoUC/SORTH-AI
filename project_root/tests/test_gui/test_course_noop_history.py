"""Saving an unchanged course must not discard its accepted schedule."""
from copy import deepcopy

import pytest
from PyQt6.QtCore import QSettings
from src.application.edit_history import encoded
from src.gui.main_window import MainWindow
from src.gui.course_manager_widget import CourseDialog
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources


@pytest.fixture(params=['single', 'split'])
def window(tmp_path, request):
    settings = QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)
    w = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False,
                   feature_settings=settings)
    w._classrooms = {'R': Classroom('R', 30, 'REGULAR'), 'L': Classroom('L', 30, 'LAB')}
    split = request.param == 'split'
    course = Course('BIO', 1, 300 if split else 60, 'LAB' if split else 'REGULAR',
                    size=20, group_suggestions=[{'preferred_day': 'Viernes'}])
    w.course_manager.load_courses_from_excel([course])
    groups = course.generate_groups()
    if split:
        assignments = {'BIO-G1-P1': ('R', 1, 480, 600), 'BIO-G1-P2': ('L', 2, 480, 600)}
        w.pinned_group_ids = {'BIO-G1-P1'}
        groups[0].lab_override = True
        groups[2].unassigned_reason = 'Saved pending feedback'
        w.resources = SchedulingResources(tuple(
            ResourceCatalog(kind, enabled, (Resource('resource', 'Synthetic alias'),),
                            tuple((g.group_id, ('resource',)) for g in groups))
            for kind, enabled in [('teacher', True), ('student_group', False), ('student', True)]))
    else:
        assignments = {'BIO-G1': ('R', 1, 480, 540)}
    w._on_schedule_done(assignments, groups)
    assert w.current_schedule == assignments
    yield w
    w._unsaved = False
    w.close()


@pytest.mark.parametrize('history_enabled', [False, True])
def test_accept_unchanged_course_preserves_schedule_and_history(window, history_enabled, monkeypatch):
    window._features.save({**window._features.values(), 'undo_redo': history_enabled})
    before = encoded(window._capture_edit_state())
    disk = encoded(window._repo.load_session())
    history = encoded(vars(window._history))
    monkeypatch.setattr(window._repo, 'save_session', lambda **kwargs: pytest.fail('No-op must not save'))
    dialog = CourseDialog(window, window.course_manager.courses[0], calendar=window.calendar)
    assert window.course_manager._replace_course(0, dialog.get_course())
    assert encoded(window._capture_edit_state()) == before
    assert encoded(window._repo.load_session()) == disk
    assert encoded(vars(window._history)) == history


def test_accept_unchanged_course_preserves_existing_redo_branch(window):
    window._features.save({**window._features.values(), 'undo_redo': True})
    changed = deepcopy(window.course_manager.courses[0])
    changed.name = 'Edited'
    assert window.course_manager._replace_course(0, changed)
    assert window._travel_history(True)
    before = encoded(window._capture_edit_state())
    history = encoded(vars(window._history))
    assert window.course_manager._replace_course(0, deepcopy(window.course_manager.courses[0]))
    assert encoded(window._capture_edit_state()) == before
    assert encoded(vars(window._history)) == history
    assert window._travel_history(False)
    assert window.course_manager.courses[0].name == 'Edited'
