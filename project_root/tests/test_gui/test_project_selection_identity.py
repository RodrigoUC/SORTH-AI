"""Catalog refreshes retain scenario identity, including native multi-selection."""
from PyQt6.QtCore import QItemSelectionModel, QSettings
import pytest

from src.application.scenario_comparison import scenario_metadata
from src.gui import project_dialog
from src.gui.main_window import MainWindow
from src.gui.project_dialog import ProjectDialog
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def dialog(tmp_path):
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False,
                        feature_settings=QSettings(str(tmp_path / 'features.ini'), QSettings.Format.IniFormat))
    window._classrooms = {'A': Classroom('A', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])
    assert window._save_session()
    dialog = ProjectDialog(window)
    yield dialog
    dialog.close()
    window._unsaved = False
    window.close()


def select_ids(dialog, *ids):
    dialog.table.clearSelection()
    model = dialog.table.selectionModel()
    for row, scenario in enumerate(dialog.rows):
        if scenario['id'] in ids:
            index = dialog.table.model().index(row, 1)
            model.select(index, QItemSelectionModel.SelectionFlag.Select |
                         QItemSelectionModel.SelectionFlag.Rows)
            model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)


def test_create_project_does_not_retarget_selected_scenario(dialog, monkeypatch):
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *args: 'Z selected')
    dialog.create()
    selected = dialog.window._scenario_id
    select_ids(dialog, selected)
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *args: 'A inserted')
    dialog.create()
    assert [row['id'] for row in dialog.selected()] == [selected]
    assert dialog.rows[dialog.table.currentRow()]['id'] == selected
    assert dialog.table.currentColumn() == 1
    assert dialog.buttons['rename'].isEnabled()

    # The next action affects the selected identity, never a replacement row.
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *args: 'Renamed selection')
    dialog.rename()
    actual = next(row for row in dialog.catalog.list_scenarios() if row['id'] == selected)
    assert actual['name'] == 'Renamed selection'
    assert next(row for row in dialog.rows if row['id'] == dialog.window._scenario_id)['name'] == '1'


def test_refresh_preserves_two_scenarios_and_current_keyboard_anchor(dialog):
    _, first = dialog.catalog.create_project('Z one', 'One', dialog.window._repo, scenario_metadata())
    _, second = dialog.catalog.create_project('Z two', 'Two', dialog.window._repo, scenario_metadata())
    dialog.refresh()
    select_ids(dialog, first, second)
    assert dialog.buttons['compare'].isEnabled()
    dialog.catalog.create_project('A inserted', 'Inserted', dialog.window._repo, scenario_metadata())
    dialog.refresh()
    assert {row['id'] for row in dialog.selected()} == {first, second}
    assert dialog.rows[dialog.table.currentRow()]['id'] == second
    assert dialog.table.currentColumn() == 1
    assert dialog.buttons['compare'].isEnabled()
    assert not dialog.buttons['open'].isEnabled()


def test_failed_refresh_leaves_selection_and_rows_unchanged(dialog, monkeypatch):
    select_ids(dialog, dialog.rows[0]['id'])
    before = list(dialog.rows)
    def fail():
        raise OSError('catalog unavailable')
    monkeypatch.setattr(dialog.catalog, 'list_scenarios', fail)
    dialog._run(dialog.refresh)
    assert dialog.rows == before
    assert dialog.selected() == before
    assert 'catalog unavailable' in dialog.feedback.text()
