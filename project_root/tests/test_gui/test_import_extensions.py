"""Import/resource/calendar/history cross-feature transaction regressions."""
from copy import deepcopy
from dataclasses import replace
import pytest
from PyQt6.QtWidgets import QMessageBox
from src.infrastructure.import_candidate import read_candidate
from src.application.edit_history import encoded
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from src.scheduling.project_calendar import ProjectCalendar
from tests.test_gui.test_background_import import window, workbook, session


def prepare(window):
    window.resources = SchedulingResources((ResourceCatalog('teacher', True,
        (Resource('teacher-local', 'Alias'),), (('BIO-G1', ('teacher-local',)),)),))
    window.calendar = ProjectCalendar(('Lunes', 'Domingo'), 0, 1440, ())
    window._features.save({**window._features.values(), 'undo_redo': True, 'teacher': True})
    assert window._save_session()
    candidate = window._capture_edit_state()
    candidate['pinned_group_ids'] = set()
    assert window._commit_edit(candidate, 'Unpin')
    assert window._history.can_undo


def test_import_detach_review_cancel_preserves_all_extensions(window, tmp_path, monkeypatch):
    prepare(window)
    candidate = read_candidate(workbook(tmp_path/'new.xlsx', code='NEW'), lambda: False)
    before = encoded(window._capture_edit_state())
    history = encoded(vars(window._history))
    disk = (tmp_path/'session.db').read_bytes()
    window._import.active = True
    monkeypatch.setattr(QMessageBox, 'exec', lambda *args: QMessageBox.StandardButton.Cancel)
    assert not window._import._review_candidate(window._import.token, candidate)
    assert encoded(window._capture_edit_state()) == before
    assert encoded(vars(window._history)) == history
    assert (tmp_path/'session.db').read_bytes() == disk


def test_import_detach_accepted_retains_catalog_calendar_and_resets_history(window, tmp_path, monkeypatch):
    prepare(window)
    candidate = read_candidate(workbook(tmp_path/'new.xlsx', code='NEW'), lambda: False)
    calendar = window.calendar
    records = window.resources.catalog('teacher').resources
    window._import.active = True
    monkeypatch.setattr(QMessageBox, 'exec', lambda *args: QMessageBox.StandardButton.Yes)
    assert window._import._review_candidate(window._import.token, candidate)
    assert window.resources.catalog('teacher').memberships
    window._commit_import(candidate, window._import.retained_pins, window._import.retained_resources)
    assert window.resources.catalog('teacher').resources == records
    assert window.resources.catalog('teacher').memberships == ()
    assert window.calendar == calendar
    assert not window._history.can_undo and not window._history.can_redo
    assert window._history.reset_reason == 'import'
    saved = window._repo.load_session()
    assert saved['resources'] == window.resources and saved['calendar'] == calendar


def test_import_failure_keeps_resource_catalog_calendar_and_history(window, tmp_path, monkeypatch):
    prepare(window)
    candidate = read_candidate(workbook(tmp_path/'new.xlsx', code='NEW'), lambda: False)
    original_resources, original_calendar = window.resources, window.calendar
    history = encoded(vars(window._history))
    before = session(window)
    disk = (tmp_path/'session.db').read_bytes()
    proposed = SchedulingResources(tuple(replace(c, memberships=()) for c in window.resources.catalogs))
    original = window.status_bar.showMessage
    def fail_success(text, *args):
        if 'Excel' in text:
            raise RuntimeError('late extension import presentation')
        return original(text, *args)
    monkeypatch.setattr(window.status_bar, 'showMessage', fail_success)
    with pytest.raises(RuntimeError, match='late extension import presentation'):
        window._commit_import(candidate, set(), proposed)
    assert window.resources is original_resources and window.calendar is original_calendar
    assert encoded(vars(window._history)) == history
    assert session(window) == before
    assert (tmp_path/'session.db').read_bytes() == disk
