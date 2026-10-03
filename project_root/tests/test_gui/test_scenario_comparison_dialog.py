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
