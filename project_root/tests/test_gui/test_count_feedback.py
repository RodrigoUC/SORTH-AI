"""Count feedback follows locale rules without changing timetable meaning."""
from copy import deepcopy

import pytest
from PyQt6.QtWidgets import QFileDialog

from src.gui.i18n import msg, plural
from src.gui.locales import LANGUAGES, Language, register_language
from src.gui.locales.en import MESSAGES as EN
from src.scheduling.course import Course
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from src.scheduling.time_model import TimeModel
from tests.test_gui.test_export_feedback import f6_status, window
from tests.test_gui.test_i18n import app, manager


@pytest.fixture(autouse=True)
def isolated_language(manager):
    manager.set_language('es', persist=False)


@pytest.mark.parametrize('assigned,pending,rooms', [
    (0, 0, 0), (0, 1, 0), (1, 0, 1), (1, 2, 1),
    (2, 1, 1), (2, 0, 2), (3, 2, 2),
])
def test_summary_and_partial_status_retranslate_independent_counts(
        window, manager, assigned, pending, rooms):
    course = Course('DEMO', assigned + pending, 60, 'REGULAR')
    groups = course.generate_groups()
    assignments = {group.group_id: (f'A{i % rooms}', 1, 480 + i * 60, 540 + i * 60)
                   for i, group in enumerate(groups[:assigned])}
    window.current_groups, window.current_schedule = groups, assignments
    viewer = window.schedule_viewer
    viewer.display_schedule(assignments, TimeModel.default(), groups)
    window._show_schedule_status()
    viewer._list_search.setText('literal search')
    original = deepcopy((assignments, [vars(group) for group in groups], viewer.summary_data))
    for language in ('es', 'en', 'es'):
        manager.set_language(language, persist=False)
        if language == 'es':
            assigned_text = f'{assigned} sesión asignada' if assigned == 1 else f'{assigned} sesiones asignadas'
            room_text = f'{rooms} aula utilizada' if rooms == 1 else f'{rooms} aulas utilizadas'
            expected = f'{assigned_text} · {pending} sin asignar · {room_text}'
            pending_text = f'{pending} pendiente' if pending == 1 else f'{pending} pendientes'
        else:
            assigned_text = f'{assigned} session assigned' if assigned == 1 else f'{assigned} sessions assigned'
            room_text = f'{rooms} classroom used' if rooms == 1 else f'{rooms} classrooms used'
            expected = f'{assigned_text} · {pending} unassigned · {room_text}'
            pending_text = f'{pending} pending'
        assert viewer._summary_label.text() == expected
        status = window.status_bar.currentMessage()
        assert f'{assigned}/{assigned + pending}' in status
        assert ('parcial' in status or 'Partial' in status) == bool(pending)
        if pending:
            assert status.endswith('; ' + pending_text)
        assert viewer._list_search.text() == 'literal search'
        assert (assignments, [vars(group) for group in groups], viewer.summary_data) == original


@pytest.mark.parametrize('count', [0, 1, 2])
@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('compact', [False, True])
def test_resource_notice_counts_links_not_scheduled_sessions(
        window, manager, count, enabled, compact):
    resources = tuple(Resource(f'R{i}', f'Literal alias {i}') for i in range(count))
    # Unlinked catalog entries and explicit empty choices must not add to count.
    resources += (Resource('unused', 'Sin asignar'),)
    memberships = tuple((f'DEMO{i}', (f'R{i}',)) for i in range(count))
    memberships += (('UNLINKED', None), ('EMPTY', ()))
    if count:
        memberships += (('SECOND-LINK', ('R0',)),)
    window.resources = SchedulingResources((ResourceCatalog('teacher', enabled, resources, memberships),))
    window.current_schedule = {}
    original = deepcopy(window.resources)
    window.resize(960, 640 if compact else 1060)
    window._update_feature_notice()
    for language in ('es', 'en', 'es'):
        manager.set_language(language, persist=False)
        if language == 'es':
            phrase = f'{count} recurso vinculado a sesiones' if count == 1 else f'{count} recursos vinculados a sesiones'
            state = 'Activo' if enabled else 'Desactivado: datos conservados, sin restricciones'
            expected = f'Docentes: {state}. {phrase}.'
        else:
            phrase = f'{count} resource linked to sessions' if count == 1 else f'{count} resources linked to sessions'
            state = 'Active' if enabled else 'Off: records retained, constraints not applied'
            expected = f'Teachers: {state}. {phrase}.'
        notice = window._feature_notice
        assert notice.toolTip() == expected
        assert notice.accessibleDescription() == expected
        if compact:
            assert notice.text() == f'{"Docentes" if language == "es" else "Teachers"}: {state} ({count})'
        else:
            assert notice.text() == expected
        assert window.current_schedule == {} and window.resources == original


@pytest.mark.parametrize('filtered', [False, True])
def test_partial_export_scope_stays_marked_in_status_and_f6(
        window, manager, tmp_path, monkeypatch, filtered):
    window.current_schedule.pop('QUI-G1')
    window.schedule_viewer.display_schedule(window.current_schedule, TimeModel.default(), window.current_groups)
    if filtered:
        window.schedule_viewer._list_search.setText('BIO')
    window._update_export_actions()
    original = deepcopy(window.current_schedule)
    original_session = (tmp_path / 'session.db').read_bytes()
    target = tmp_path / 'literal & result.xlsx'
    titles = []
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        lambda *args: (titles.append(str(args[1])) or str(target), ''))
    window._export_schedule(filtered=filtered)
    assert 'horario parcial, 1 pendiente' in titles[0]
    assert '1 pendientes' not in titles[0]
    original_export = target.read_bytes()
    for language in ('en', 'es'):
        manager.set_language(language, persist=False)
        scope = ('filtered' if filtered else 'all assignments') if language == 'en' else ('filtrado' if filtered else 'todas las asignaciones')
        partial = 'partial schedule, 1 pending' if language == 'en' else 'horario parcial, 1 pendiente'
        expected = scope + ' · ' + partial
        assert expected in window.status_bar.currentMessage()
        assert expected in f6_status(window)
        assert '1 pendientes' not in f6_status(window)
    window.status_bar.showMessage(msg('Datos actualizados. Genere un nuevo horario para exportar.'))
    manager.set_language('en', persist=False)
    snapshot = f6_status(window)
    assert 'partial schedule, 1 pending' in snapshot and str(target) in snapshot
    assert window.current_schedule == original
    assert target.read_bytes() == original_export
    assert (tmp_path / 'session.db').read_bytes() == original_session


@pytest.mark.parametrize('key,spanish', [
    ('assigned_session_count', '1 sesión asignada'),
    ('used_classroom_count', '1 aula utilizada'),
    ('linked_resource_count', '1 recurso vinculado a sesiones'),
])
@pytest.mark.parametrize('failure', ['missing', 'placeholder', 'malformed'])
def test_new_count_messages_preserve_spanish_fallback(manager, monkeypatch, key, spanish, failure):
    if failure == 'missing':
        monkeypatch.delitem(EN, key)
    else:
        monkeypatch.setitem(EN, key, {'other': '{wrong}' if failure == 'placeholder' else '{broken'})
    manager.set_language('en', persist=False)
    assert plural(key, 1) == spanish


def test_new_counts_use_registered_plural_categories_in_live_summary(window, manager):
    catalog = {
        'assigned_session_count': {'zero': 'none assigned ({n})', 'one': 'single assigned ({n})',
                                   'few': 'few assigned ({n})', 'other': 'other assigned ({n})'},
        'used_classroom_count': {'zero': 'no room ({n})', 'one': 'single room ({n})',
                                'few': 'few rooms ({n})', 'other': 'other rooms ({n})'},
        'linked_resource_count': {'zero': 'no links ({n})', 'one': 'single link ({n})',
                                 'few': 'few links ({n})', 'other': 'other links ({n})'},
    }
    register_language(Language('count-test', 'Count test', 'en_US', catalog, {},
        lambda n: 'zero' if n == 0 else 'one' if n == 1 else 'few' if n in (2, 3) else 'other'))
    try:
        manager.set_language('count-test', persist=False)
        assert window.schedule_viewer._summary_label.text() == 'few assigned (2) · 0 sin asignar · single room (1)'
        for key in catalog:
            for n, category in ((0, 'zero'), (1, 'one'), (2, 'few'), (4, 'other')):
                assert plural(key, n) == catalog[key][category].format(n=n)
        manager.set_language('en', persist=False)
        assert window.schedule_viewer._summary_label.text() == '2 sessions assigned · 0 unassigned · 1 classroom used'
    finally:
        manager.set_language('es', persist=False)
        LANGUAGES.pop('count-test')
