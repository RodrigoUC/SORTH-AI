"""Committed scenario transitions retain coherent identity through Qt recovery."""
from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox
import pytest

from src.application.scenario_comparison import scenario_metadata, session_fingerprint
from src.gui import project_dialog
from src.gui.main_window import MainWindow
from src.gui.project_dialog import ProjectDialog
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def scenario_pair(tmp_path, monkeypatch):
    window = MainWindow(SessionRepository(str(tmp_path / 'working.db')), restore_session=False,
                        feature_settings=QSettings(str(tmp_path / 'features.ini'), QSettings.Format.IniFormat))
    window._classrooms = {'A': Classroom('A', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('OLD', 1, 60, 'REGULAR')])
    window._algorithm_version = 'old-algorithm'
    assert window._save_session()
    dialog = ProjectDialog(window)
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *args: 'Old project')
    dialog.create()
    source = SessionRepository(str(tmp_path / 'candidate.db'))
    source.save_session(None, 17, {'A': Classroom('A', 30, 'REGULAR')},
                        [Course('NEW', 1, 60, 'REGULAR')], {}, {'NEW-G1': ('A', 1, 480, 540)})
    _, target = dialog.catalog.create_project('New project', 'New scenario', source,
                                              scenario_metadata('new-algorithm'))
    dialog.refresh()
    dialog.table.selectRow(next(i for i, row in enumerate(dialog.rows) if row['id'] == target))
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Yes)
    yield window, dialog, target
    dialog.close()
    window._unsaved = False
    window.close()


def identity(window):
    return (window._scenario_id, window._scenario_name, window._scenario_baseline,
            window._scenario_dirty, window._algorithm_version)


def fail(*args, **kwargs):
    raise OSError('temporary operation failure')


def test_committed_open_retry_recovers_the_target_scenario_identity(scenario_pair, monkeypatch):
    window, dialog, target = scenario_pair
    target_data = dialog.catalog.read(target)[0]
    render = window.course_manager.load_courses_from_excel
    # Instance-local fault leaves the isolated preflight renderer unaffected.
    monkeypatch.setattr(window.course_manager, 'load_courses_from_excel', fail)
    dialog._run(dialog.open_selected)
    assert window._restore_failed and window._busy
    assert window._repo.load_session()['courses'][0].code == 'NEW'
    assert not window._retry_session()
    assert window._restore_failed
    monkeypatch.setattr(window.course_manager, 'load_courses_from_excel', render)
    assert window._retry_session()
    assert not window._restore_failed and not window._busy
    assert window.course_manager.get_courses()[0].code == 'NEW'
    assert identity(window) == (target, 'New project / New scenario',
                                session_fingerprint(target_data), False, 'new-algorithm')
    assert 'New project / New scenario' in window._save_state_label.text()
    assert window._scenario_baseline == session_fingerprint(window._repo.load_session())
    backups = list(Path(window._repo._db_path).parent.glob('previous-session-*.db'))
    assert len(backups) == 1
    assert SessionRepository(str(backups[0])).load_session()['courses'][0].code == 'OLD'

    # Later publication must carry the recovered scenario's algorithm marker.
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *args: 'After retry')
    dialog.save_as()
    assert dialog.catalog.read(window._scenario_id)[1]['algorithm_version'] == 'new-algorithm'


@pytest.mark.parametrize('stage', ['backup', 'target_save'])
def test_failed_open_before_commit_preserves_previous_identity(scenario_pair, monkeypatch, stage):
    window, dialog, _target = scenario_pair
    before = identity(window)
    if stage == 'backup':
        monkeypatch.setattr(window._repo, 'backup_session', fail)
    else:
        save = window._repo.save_session
        def fail_target(*args, **kwargs):
            if kwargs['courses'][0].code == 'NEW':
                fail()
            return save(*args, **kwargs)
        monkeypatch.setattr(window._repo, 'save_session', fail_target)
    dialog._run(dialog.open_selected)
    assert identity(window) == before
    assert not window._restore_failed
    assert window._repo.load_session()['courses'][0].code == 'OLD'
    assert window.course_manager.get_courses()[0].code == 'OLD'


def test_open_does_not_reread_catalog_after_committing_target(scenario_pair, monkeypatch):
    window, dialog, target = scenario_pair
    read = dialog.catalog.read
    reads = []
    def read_once(scenario):
        reads.append(scenario)
        if len(reads) > 1:
            fail()
        return read(scenario)
    monkeypatch.setattr(dialog.catalog, 'read', read_once)
    dialog._run(dialog.open_selected)
    assert reads == [target]
    assert dialog.result() == dialog.DialogCode.Accepted
    assert window._scenario_id == target
    assert not window._restore_failed


@pytest.mark.parametrize('operation', ['create', 'save_as'])
def test_failed_snapshot_readback_never_mixes_scenario_identity(scenario_pair, monkeypatch, operation):
    window, dialog, _target = scenario_pair
    # There are real changes relative to the previous named snapshot.
    window.course_manager.load_courses_from_excel([Course('EDITED', 1, 60, 'REGULAR')])
    assert window._scenario_dirty
    before = identity(window)
    old_count = len(dialog.rows)
    monkeypatch.setattr(project_dialog, 'ask_name', lambda *args: 'Saved but unreadable')
    monkeypatch.setattr(dialog.catalog, 'read', fail)
    dialog._run(getattr(dialog, operation))
    assert len(dialog.catalog.list_scenarios()) == old_count + 1
    assert window._repo.load_session()['courses'][0].code == 'EDITED'
    assert not window._unsaved
    assert identity(window) == before
    assert 'temporary operation failure' in dialog.feedback.text()
