"""Compare persisted optional-rule variants without losing identity or labels."""
from dataclasses import replace

import pytest
from PyQt6.QtWidgets import QLabel

from src.application.scenario_comparison import compare_scenarios, scenario_metadata
from src.gui.i18n import language_manager
from src.gui.project_dialog import ComparisonDialog
from src.infrastructure.project_repository import ProjectRepository
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.project_calendar import ProjectCalendar
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources


def saved_scenario(tmp_path, name, *, calendar=None, resources=None, assignments=None):
    calendar = calendar or ProjectCalendar()
    repo = SessionRepository(str(tmp_path / f'{name}.db'))
    repo.save_session(None, 42, {'A': Classroom('A', 30, 'REGULAR')},
                      [Course('BIO', 2, 60, 'REGULAR')], {}, assignments,
                      calendar=calendar, resources=resources or SchedulingResources())
    catalog = ProjectRepository(tmp_path / 'projects.db')
    _, scenario = catalog.create_project(name, '1', repo, scenario_metadata('test', calendar))
    return catalog.read(scenario)


@pytest.mark.parametrize('kind', ['teacher', 'student_group', 'student'])
@pytest.mark.parametrize('language', ['es', 'en'])
def test_resource_differences_render_and_retranslate(tmp_path, kind, language):
    manager = language_manager()
    previous = manager.language
    manager.set_language(language, persist=False)
    catalog = ResourceCatalog(kind, True, (Resource('resource-1', 'Literal alias'),),
                              (('BIO-G1', ('resource-1',)),))
    left = saved_scenario(tmp_path, 'A', resources=SchedulingResources((catalog,)))
    right = saved_scenario(tmp_path, 'B', resources=SchedulingResources((replace(catalog, enabled=False),)))
    result = compare_scenarios(left, right)
    assert result['differences'] == ['resources']
    assert not result['comparable']
    dialog = None
    try:
        dialog = ComparisonDialog(None, {'name': 'A'}, {'name': 'B'}, result)
        for active in (language, 'en' if language == 'es' else 'es'):
            manager.set_language(active, persist=False)
            label = 'Recursos' if active == 'es' else 'Resources'
            assert any(label in item.text() for item in dialog.findChildren(QLabel))
            assert dialog._difference_detail.toPlainText().startswith(label + '\n')
            assert 'Literal alias' in dialog._difference_detail.toPlainText()
            assert dialog._difference_detail.isReadOnly()
            assert dialog._difference_detail.accessibleName()
    finally:
        if dialog is not None:
            dialog.close()
        manager.set_language(previous, persist=False)


@pytest.mark.parametrize('left_days,right_days,left_assignments,right_assignments,expected', [
    (ProjectCalendar().days, ('Martes',),
     {'BIO-G1': ('A', 1, 480, 540), 'BIO-G2': ('A', 2, 600, 660)},
     {'BIO-G1': ('A', 1, 480, 540)},
     {'Lunes': ('60', None), 'Martes': ('60', '60'), 'Miércoles': ('0', None),
      'Jueves': ('0', None), 'Viernes': ('0', None), 'Sábado': ('0', None)}),
    (('Lunes', 'Miércoles'), ('Martes', 'Miércoles'),
     {'BIO-G1': ('A', 1, 480, 540), 'BIO-G2': ('A', 2, 600, 660)},
     {'BIO-G1': ('A', 2, 480, 540), 'BIO-G2': ('A', 2, 600, 660)},
     {'Lunes': ('60', None), 'Martes': (None, '0'), 'Miércoles': ('60', '120')}),
    (('Martes',), ('Martes', 'Domingo'),
     {'BIO-G1': ('A', 1, 480, 540)}, {'BIO-G1': ('A', 2, 480, 540)},
     {'Martes': ('60', '0'), 'Domingo': (None, '60')}),
])
def test_calendar_comparison_aligns_weekdays_and_marks_non_teaching_days(
        tmp_path, left_days, right_days, left_assignments, right_assignments, expected):
    from PyQt6.QtWidgets import QTableWidget
    from src.gui.i18n import msg
    from src.scheduling.project_calendar import DAYS

    manager = language_manager()
    previous = manager.language
    manager.set_language('es', persist=False)
    left = saved_scenario(tmp_path, 'A', calendar=ProjectCalendar(left_days, 480, 720, ()),
                          assignments=left_assignments)
    right = saved_scenario(tmp_path, 'B', calendar=ProjectCalendar(right_days, 480, 720, ()),
                           assignments=right_assignments)
    result = compare_scenarios(left, right)
    assert result['differences'] == ['calendar']
    assert not result['comparable']
    dialog = None
    try:
        dialog = ComparisonDialog(None, {'name': 'A'}, {'name': 'B'}, result)
        table = dialog.findChild(QTableWidget)
        assert table.accessibleName()
        assert not table.tabKeyNavigation()
        for language in ('es', 'en'):
            manager.set_language(language, persist=False)
            rows = {table.item(row, 0).text(): tuple(table.item(row, col).text() for col in (1, 2))
                    for row in range(10, table.rowCount())}
            labels = [str(msg('Docencia, día {day} (min)', day=msg(day)))
                      for day in DAYS if day in expected]
            assert list(rows) == labels
            for day, values in expected.items():
                label = str(msg('Docencia, día {day} (min)', day=msg(day)))
                assert rows[label] == tuple(value if value is not None else str(msg('No lectivo'))
                                            for value in values)
    finally:
        if dialog is not None:
            dialog.close()
        manager.set_language(previous, persist=False)
