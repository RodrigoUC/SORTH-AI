"""A malformed spreadsheet cannot discard accepted pins or resources."""
import pytest
from PyQt6.QtWidgets import QMessageBox

from src.application.edit_history import encoded
from src.gui.i18n import language_manager
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from tests.test_gui.import_helpers import wait_for_import
from tests.test_gui.test_background_import import window
from tests.test_infrastructure.test_excel_error_cells import error_workbook


@pytest.mark.parametrize('language,expected', [('es', 'error de Excel'), ('en', 'Excel error')])
@pytest.mark.parametrize('missing_cache', [False, True], ids=['cached-error', 'missing-result'])
def test_formula_error_preserves_disk_pin_resources_and_history(window, tmp_path, monkeypatch, language, expected, missing_cache):
    window.resources = SchedulingResources((ResourceCatalog('teacher', True,
        (Resource('t-synthetic', 'Synthetic teacher'),), (('BIO-G1', ('t-synthetic',)),)),))
    assert window._save_session()
    before = encoded(window._capture_edit_state())
    history = encoded(vars(window._history))
    db_path = tmp_path / 'session.db'
    disk = db_path.read_bytes()
    if missing_cache:
        from tests.test_infrastructure.test_excel_formula_results import workbook, formula
        path = tmp_path / 'missing-result.xlsx'
        path.write_bytes(workbook([('Cursos', 'B3', formula())]))
        expected = ('Recalcule y guarde el libro en Excel, o pegue los valores' if language == 'es'
                    else 'Recalculate and save the workbook in Excel, or paste values')
    else:
        path = error_workbook(tmp_path / 'cached-error.xlsx', formula=True)
    errors = []
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: errors.append(str(args[2])))
    monkeypatch.setattr(window._import, '_review_candidate', lambda *args: pytest.fail('Invalid workbook reached acceptance review'))
    manager = language_manager()
    previous = manager.language
    try:
        manager.set_language(language, persist=False)
        window._import.start(str(path))
        wait_for_import(window)
        assert len(errors) == 1 and expected in errors[0] and 'B3' in errors[0]
        assert encoded(window._capture_edit_state()) == before
        assert encoded(vars(window._history)) == history
        assert db_path.read_bytes() == disk
        restored = SessionRepository(str(db_path)).load_session()
        assert restored['pinned_group_ids'] == {'BIO-G1'}
        assert restored['assignments'] == {'BIO-G1': ('R', 1, 480, 540)}
        assert restored['resources'] == window.resources
        assert restored['restrictions'] == {'R': {'BIO'}}
        assert [course.code for course in restored['courses']] == ['BIO']
    finally:
        manager.set_language(previous, persist=False)


def test_reimported_split_groups_keep_exact_pins_and_resources_then_cancel_safely(window, tmp_path, monkeypatch):
    from src.infrastructure.import_candidate import read_candidate
    from src.scheduling.time_model import TimeModel
    from tests.test_gui.test_background_import import workbook

    path = workbook(tmp_path / 'split.xlsx', hours='0800-1300', count=2)
    imported = read_candidate(path, lambda: False).imported
    window.pinned_group_ids.clear()
    window.course_manager.load_courses_from_excel(imported.courses)
    window._classrooms = imported.classrooms
    window._classroom_course_map = imported.classroom_course_map
    window.current_groups = [group for course in imported.courses for group in course.generate_groups()]
    window.current_schedule = {
        'BIO-G1-P1': ('R', 1, 480, 600),
        'BIO-G2-P1': ('R', 2, 600, 720),
    }
    window.pinned_group_ids = {'BIO-G1-P1'}
    for group in window.current_groups:
        group.assignment = window.current_schedule.get(group.group_id)
        group.pinned = group.group_id in window.pinned_group_ids
    window.resources = SchedulingResources(tuple(
        ResourceCatalog(kind, True, (Resource(f'{kind}-local', f'Synthetic {kind}'),), (
            ('BIO-G1-P1', (f'{kind}-local',)), ('BIO-G2-P1', (f'{kind}-local',)),
        )) for kind in ('teacher', 'student_group', 'student')))
    resources = window.resources.to_data()
    window.schedule_viewer.display_schedule(window.current_schedule, TimeModel.default(), window.current_groups)
    assert window._save_session()

    for _ in range(2):
        window._import.start(path)
        wait_for_import(window)
        assert window.pinned_group_ids == {'BIO-G1-P1'}
        assert window.current_schedule == {'BIO-G1-P1': ('R', 1, 480, 600)}
        assert window.resources.to_data() == resources
        assert [group.group_id for group in window.current_groups] == [
            f'BIO-G{number}-P{part}' for number in (1, 2) for part in (1, 2, 3)]
        assert sum(group.duration_min for group in window.current_groups) == 600
        saved = SessionRepository(str(tmp_path / 'session.db')).load_session()
        assert saved['pinned_group_ids'] == window.pinned_group_ids
        assert saved['assignments'] == window.current_schedule
        assert saved['resources'].to_data() == resources
        assert saved['restrictions'] == {}

    before = encoded(window._capture_edit_state())
    disk = (tmp_path / 'session.db').read_bytes()
    reviews = []
    monkeypatch.setattr(QMessageBox, 'exec', lambda dialog: reviews.append(dialog.text()) or QMessageBox.StandardButton.Cancel)
    window._import.start(workbook(tmp_path / 'replacement.xlsx', code='NEW'))
    wait_for_import(window)
    assert len(reviews) == 1
    assert encoded(window._capture_edit_state()) == before
    assert (tmp_path / 'session.db').read_bytes() == disk
    reopened = SessionRepository(str(tmp_path / 'session.db')).load_session()
    assert reopened['resources'].to_data() == resources
    assert reopened['pinned_group_ids'] == {'BIO-G1-P1'}
