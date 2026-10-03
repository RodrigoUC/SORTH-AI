"""Unrelated edits must round-trip all accepted imported numeric values."""
import pytest
from PyQt6.QtCore import QSettings
from src.gui.course_manager_widget import CourseDialog
from src.gui.main_window import MainWindow
from src.infrastructure.excel_reader import ExcelReader
from src.infrastructure.session_repository import SessionRepository
from tests.test_gui.test_background_import import workbook


@pytest.mark.parametrize('hours,duration', [('0800-0859', 59), ('0000-1559', 959)])
def test_name_only_edit_preserves_imported_groups_and_duration(tmp_path, hours, duration):
    imported = ExcelReader(workbook(tmp_path / 'input.xlsx', hours=hours, count=51)).load_validated()
    assert not imported.warnings
    original = imported.courses[0]
    assert (original.number_of_groups, original.duration_min) == (51, duration)
    settings = QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False,
                        feature_settings=settings)
    try:
        window._classrooms = imported.classrooms
        window.course_manager.load_courses_from_excel(imported.courses)
        dialog = CourseDialog(window, original)
        dialog.name_edit.setText('Edited name only')
        assert window._commit_course_edit([dialog.get_course()], 'Rename')
        saved = window._repo.load_session()['courses'][0]
        assert (saved.number_of_groups, saved.duration_min) == (51, duration)
        assert saved.name == 'Edited name only'
        assert saved.group_suggestions == original.group_suggestions
        assert not window._unsaved
        dialog.close()
    finally:
        window._unsaved = False
        window.close()
