"""Restoring source data must not manufacture a scheduling attempt."""
from src.infrastructure.feature_preferences import FeaturePreferences
from pathlib import Path
import pytest
from PyQt6.QtCore import QSettings

from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.mark.parametrize('assignments', [None, {}, {'BIO-G1': ('R', 1, 480, 540)}])
def test_restore_preserves_absent_empty_and_assigned_results(tmp_path, assignments):
    repo = SessionRepository(str(tmp_path / 'session.db'))
    repo.save_session(None, 42, {'R': Classroom('R', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'REGULAR')], {}, assignments)
    settings = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    window = MainWindow(repo, restore_session=False, feature_preferences=FeaturePreferences(path=Path(str((settings).fileName()) + '.features.json')))
    try:
        window.session.restore(confirm=False)
        assert not window._restore_failed
        assert window.current_schedule == assignments
        assert (window.current_groups is None) == (assignments is None)
        if assignments is not None:
            assert len(window.current_groups) == 1
        assert window.session.save()
        assert repo.load_session()['assignments'] == assignments
    finally:
        window._unsaved = False
        window.close()


@pytest.mark.parametrize('source_exists', [False, True])
def test_restore_uses_saved_suggestions_without_reimporting_source(tmp_path, monkeypatch, source_exists):
    """Missing or replaced workbooks cannot change accepted room restrictions."""
    from src.infrastructure import excel_reader

    source = tmp_path / 'source.xlsx'
    if source_exists:
        source.write_bytes(b'The original workbook has been replaced')
    repo = SessionRepository(str(tmp_path / 'session.db'))
    course = Course('BIO', 2, 60, 'REGULAR',
                    group_suggestions=[{'aula': 'R'}, {'aula': None}])
    repo.save_session(str(source), 42, {'R': Classroom('R', 30, 'REGULAR')}, [course], {}, None)
    def forbidden(*args, **kwargs):
        raise AssertionError('Restoration must not reimport the source workbook')
    monkeypatch.setattr(excel_reader, 'ExcelReader', forbidden)
    settings = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    window = MainWindow(repo, restore_session=False, feature_preferences=FeaturePreferences(path=Path(str((settings).fileName()) + '.features.json')))
    try:
        window.session.restore(confirm=False)
        assert not window._restore_failed
        assert window._classroom_course_map == {'R': ['BIO']}
        assert window.current_groups is None
    finally:
        window._unsaved = False
        window.close()
