from copy import deepcopy
import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox, QDialogButtonBox
from src.gui.main_window import MainWindow
from src.gui.placement_options_dialog import PlacementOptionsDialog
from src.gui.features import FeaturePreferences
from src.gui.i18n import language_manager
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom


@pytest.fixture
def window(tmp_path):
    settings = QSettings(str(tmp_path/'preferences.ini'), QSettings.Format.IniFormat)
    w = MainWindow(SessionRepository(str(tmp_path/'session.db')), restore_session=False, feature_settings=settings)
    w._classrooms = {'R': Classroom('R', 30, 'REGULAR')}
    w.course_manager.load_courses_from_excel([Course('A', 2, 60, 'REGULAR')])
    groups = w.course_manager.get_courses()[0].generate_groups()
    groups[0].assignment = ('R', 1, 480, 540)
    w._on_schedule_done({'A-G1': groups[0].assignment}, groups)
    yield w
    w.close()


def enable(window, value=True):
    flags = window._features.values()
    flags['placement_suggestions'] = value
    flags['undo_redo'] = True
    window._features.save(flags)
    window._apply_feature_preferences()


def dialog(window):
    enable(window)
    return PlacementOptionsDialog('A-G2', window._placement_inputs, window._apply_placement_option, window)


def test_opt_in_persists_toggles_and_cancel_never_changes(window):
    assert not window._features.enabled('placement_suggestions')
    assert all(button.isHidden() for button in window.schedule_viewer._suggestion_controls)
    before = deepcopy(window._capture_edit_state())
    d = dialog(window)
    assert d.table.rowCount() > 0
    assert not d.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    d.reject()
    assert window.current_schedule == before['assignments']
    enable(window, False)
    assert all(button.isHidden() for button in window.schedule_viewer._suggestion_controls)
    enable(window)
    assert all(not button.isHidden() for button in window.schedule_viewer._suggestion_controls)
    assert FeaturePreferences(window._features.settings).enabled('placement_suggestions')


def test_explicit_selection_applies_one_and_undo_restores(window):
    before = deepcopy(window.current_schedule)
    d = dialog(window)
    placement = d.options.placements[0]
    d.table.selectRow(0)
    d._apply()
    assert window.current_schedule == dict(before, **{'A-G2': placement})
    assert window._repo.load_session()['assignments'] == window.current_schedule
    assert window._travel_history(True)
    assert window.current_schedule == before
    assert window._travel_history(False)
    assert window.current_schedule['A-G2'] == placement


def test_stale_recalculates_without_applying_until_reselected(window):
    d = dialog(window)
    d.table.selectRow(0)
    window._classrooms['R'].capacity = 31
    d._apply()
    assert 'A-G2' not in window.current_schedule
    assert d.table.currentRow() < 0
    assert 'cambió' in d.status.text()
    d.table.selectRow(0)
    d._apply()
    assert 'A-G2' in window.current_schedule


def test_disabled_during_review_and_persistence_failure_preserve_data(window, monkeypatch):
    d = dialog(window)
    d.table.selectRow(0)
    enable(window, False)
    d._apply()
    assert 'A-G2' not in window.current_schedule
    d = dialog(window)
    d.table.selectRow(0)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: QMessageBox.StandardButton.Ok)
    def fail(**kwargs): raise OSError('disk full')
    monkeypatch.setattr(window._repo, 'save_session', fail)
    before = deepcopy(window.current_schedule)
    d._apply()
    assert window.current_schedule == before and d.result() == 0
    window._unsaved = False


def test_dialog_english_accessibility_and_zero_options(window):
    window.current_groups[1].required_room_type = 'LAB'
    manager = language_manager()
    manager.set_language('en', persist=False)
    try:
        d = dialog(window)
        assert not d.options.placements
        assert 'current schedule' in d.status.text()
        assert 'global impossibility' in d.status.text()
        assert d.table.accessibleName() == 'Valid placements for the pending session'
        assert d.buttons.button(QDialogButtonBox.StandardButton.Save).text() == 'Assign'
        d.reject()
    finally:
        manager.set_language('es', persist=False)
