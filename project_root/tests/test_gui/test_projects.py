import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QSettings
from src.gui.main_window import MainWindow
from src.gui.project_dialog import ProjectDialog, ComparisonDialog
from src.gui import project_dialog
from src.gui.i18n import language_manager
from src.infrastructure.session_repository import SessionRepository
from src.application.scenario_comparison import scenario_metadata, compare_scenarios
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom


@pytest.fixture
def window(tmp_path):
    settings = QSettings(str(tmp_path/'features.ini'), QSettings.Format.IniFormat)
    window = MainWindow(SessionRepository(str(tmp_path/'session.db')), restore_session=False, feature_settings=settings)
    window._classrooms = {'A': Classroom('A', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])
    window._save_session()
    yield window
    window._unsaved = False
    window.close()


def test_cancel_creation_does_not_save_or_create(window, monkeypatch):
    dialog = ProjectDialog(window)
    before = dialog.catalog.list_scenarios()
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *a: None)
    monkeypatch.setattr(window, '_save_session', lambda: pytest.fail('Cancelled operation saved'))
    dialog.create()
    assert dialog.catalog.list_scenarios() == before
    dialog.close()


def test_create_open_duplicate_and_failure_preserves_current(window, monkeypatch):
    dialog = ProjectDialog(window)
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *a: 'Test')
    dialog.create()
    assert window._scenario_name.endswith(' / 1')
    assert not window._scenario_dirty
    dialog.table.selectRow(len(dialog.rows)-1)
    selected = dialog.selected()[0]
    dialog.catalog.duplicate(selected['id'], 'Second')
    window._classrooms = {}
    window.course_manager.load_courses_from_excel([])
    assert window._scenario_dirty
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.No)
    dialog.open_selected()
    assert window.course_manager.get_courses() == []
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.Yes)
    dialog.open_selected()
    assert [c.code for c in window.course_manager.get_courses()] == ['BIO']
    assert set(window._classrooms) == {'A'}
    assert not window._restore_failed
    assert list(__import__('pathlib').Path(window._repo._db_path).parent.glob('previous-session-*.db'))
    dialog.close()


def test_comparison_and_catalog_localize(window):
    dialog = ProjectDialog(window)
    first = dialog.rows[0]
    second = dialog.catalog.duplicate(first['id'], 'Alternative')
    data = compare_scenarios(dialog.catalog.read(first['id']), dialog.catalog.read(second))
    comparison = ComparisonDialog(dialog, first, {'name':'Alternative'}, data)
    language_manager().set_language('en')
    assert dialog.windowTitle() == 'Projects and scenarios'
    assert comparison.windowTitle() == 'Compare scenarios'
    comparison.show()
    QApplication.processEvents()
    comparison.close()
    dialog.close()
    language_manager().set_language('es')


def test_failed_working_write_does_not_create_snapshot(window, monkeypatch):
    dialog = ProjectDialog(window)
    before = dialog.catalog.list_scenarios()
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *a: 'Cannot save')
    def fail(**kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(window._repo, 'save_session', fail)
    dialog._run(dialog.create)
    assert dialog.catalog.list_scenarios() == before
    assert window._unsaved
    assert 'disk full' in dialog.feedback.text()
    window._unsaved = False
    dialog.close()


def test_unchanged_save_keeps_named_snapshot_clean(window, monkeypatch):
    dialog = ProjectDialog(window)
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *a: 'Project')
    dialog.create()
    assert window._save_session()
    assert not window._scenario_dirty
    window.seed_input.setValue(91)
    window.chk_random_seed.setChecked(False)
    window._save_session()
    assert window._scenario_dirty
    dialog.close()


@pytest.mark.parametrize('field,value', [('format_version', 999), ('metrics_version', 999), ('calendar', {})])
def test_unsupported_snapshot_never_writes_working_session(window, monkeypatch, field, value):
    dialog = ProjectDialog(window)
    metadata = scenario_metadata()
    metadata[field] = value
    _, scenario = dialog.catalog.create_project('Future', 'Future', window._repo, metadata)
    dialog.refresh()
    index = next(i for i, row in enumerate(dialog.rows) if row['id'] == scenario)
    dialog.table.selectRow(index)
    before = __import__('pathlib').Path(window._repo._db_path).read_bytes()
    monkeypatch.setattr(window, '_save_session', lambda: pytest.fail('Unsupported snapshot wrote session'))
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: pytest.fail('Unsupported snapshot prompted opening'))
    with pytest.raises(ValueError):
        dialog.open_selected()
    assert __import__('pathlib').Path(window._repo._db_path).read_bytes() == before
    dialog.close()


def test_unrenderable_seed_preserves_disk_and_gui(window, monkeypatch):
    dialog = ProjectDialog(window)
    with window._repo._connect() as con:
        con.execute('UPDATE session SET seed=?', (2**40,))
    _, scenario = dialog.catalog.create_project('Bad seed', 'Bad', window._repo, scenario_metadata())
    window._save_session()
    before = __import__('pathlib').Path(window._repo._db_path).read_bytes()
    courses = window.course_manager.get_courses()
    dialog.refresh()
    dialog.table.selectRow(next(i for i, row in enumerate(dialog.rows) if row['id'] == scenario))
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: pytest.fail('Bad candidate prompted opening'))
    with pytest.raises(ValueError):
        dialog.open_selected()
    assert __import__('pathlib').Path(window._repo._db_path).read_bytes() == before
    assert window.course_manager.get_courses() == courses
    assert not window._restore_failed
    dialog.close()


def test_open_scenario_restores_pins_and_explicit_lab_exceptions(window, monkeypatch):
    window._features.save({**window._features.values(), 'pinned_sessions': True, 'project_scenarios': True})
    window._apply_feature_preferences()
    window.course_manager.load_courses_from_excel([Course('LAB', 1, 60, 'LAB')])
    groups = window.course_manager.get_courses()[0].generate_groups()
    assignments = {'LAB-G1': ('A', 1, 480, 540)}
    groups[0].assignment = assignments['LAB-G1']
    groups[0].lab_override = True
    window._on_schedule_done(assignments, groups)
    window._toggle_pin('LAB-G1')
    dialog = ProjectDialog(window)
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *args: 'Pinned LAB')
    dialog.create()
    scenario = window._scenario_id
    window._toggle_pin('LAB-G1')
    assert window._scenario_dirty
    dialog.refresh()
    dialog.table.selectRow(next(i for i, row in enumerate(dialog.rows) if row['id'] == scenario))
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Yes)
    dialog.open_selected()
    assert window.pinned_group_ids == {'LAB-G1'}
    assert window.current_schedule == assignments
    assert window.current_groups[0].pinned and window.current_groups[0].lab_override
    saved = window._repo.load_session()
    assert saved['pinned_group_ids'] == saved['lab_overrides'] == {'LAB-G1'}
    assert not window._scenario_dirty
    dialog.close()
