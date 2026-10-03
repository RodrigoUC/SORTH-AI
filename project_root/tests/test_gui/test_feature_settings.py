from src.application.scenario_comparison import session_fingerprint
import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox
from src.gui.features import FEATURES, FeaturePreferences
from src.gui.settings_dialog import SettingsDialog
from src.gui.main_window import MainWindow
from src.gui.i18n import language_manager
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom


def settings_at(path):
    return QSettings(str(path), QSettings.Format.IniFormat)


@pytest.fixture
def window(tmp_path):
    w = MainWindow(SessionRepository(str(tmp_path/'session.db')), restore_session=False,
                   feature_settings=settings_at(tmp_path/'preferences.ini'))
    yield w
    w._unsaved = False
    w.close()


def test_default_registry_contains_only_implemented_extras(tmp_path):
    prefs = FeaturePreferences(settings_at(tmp_path/'preferences.ini'))
    assert prefs.values() == {'pinned_sessions': False, 'project_scenarios': False}
    assert not prefs.enabled('unknown_future_feature')


@pytest.mark.parametrize('malformed', ['yes', '1', 'garbage', 1, [], {'enabled': True}])
def test_malformed_values_fail_closed(tmp_path, malformed):
    settings = settings_at(tmp_path/'preferences.ini')
    settings.setValue('features/pinned_sessions', malformed)
    assert not FeaturePreferences(settings).enabled('pinned_sessions')


def test_restart_and_future_keys_preserved(tmp_path):
    path = tmp_path/'preferences.ini'
    settings = settings_at(path)
    settings.setValue('features/future_feature', 'preserved')
    FeaturePreferences(settings).save({'pinned_sessions': True, 'project_scenarios': False})
    prefs = FeaturePreferences(settings_at(path))
    assert prefs.values() == {'pinned_sessions': True, 'project_scenarios': False}
    assert prefs.settings.value('features/future_feature') == 'preserved'
    assert not prefs.enabled('future_feature')
    with pytest.raises(ValueError):
        prefs.save({'pinned_sessions': 'true', 'project_scenarios': False})


def test_cancel_and_escape_do_not_write(window):
    dialog = SettingsDialog(window)
    dialog.controls['pinned_sessions'].setChecked(True)
    dialog.reject()
    assert not window._features.enabled('pinned_sessions')
    assert window._features.settings.allKeys() == []
    assert window.btn_projects.isHidden()
    assert all(control.isHidden() for control in window.schedule_viewer._pin_controls)


def test_save_shows_features_then_restart_restores(window, tmp_path):
    dialog = SettingsDialog(window)
    for control in dialog.controls.values():
        control.setChecked(True)
    dialog.accept()
    assert not window.btn_projects.isHidden()
    assert all(not control.isHidden() for control in window.schedule_viewer._pin_controls)
    other = MainWindow(SessionRepository(str(tmp_path/'other.db')), restore_session=False,
                       feature_settings=settings_at(tmp_path/'preferences.ini'))
    assert not other.btn_projects.isHidden()
    assert other._features.enabled('pinned_sessions')
    other.close()


def test_disabled_pins_preserved_enforced_and_explained(window, monkeypatch, tmp_path):
    window._features.save({'pinned_sessions': True, 'project_scenarios': False})
    window._apply_feature_preferences()
    window._classrooms = {'R': Classroom('R', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])
    groups = window.course_manager.get_courses()[0].generate_groups()
    assignments = {'BIO-G1': ('R', 1, 480, 540)}
    groups[0].assignment = assignments['BIO-G1']
    window._on_schedule_done(assignments, groups)
    window._toggle_pin('BIO-G1')
    before = session_fingerprint(window._repo.load_session())
    dialog = SettingsDialog(window)
    dialog.controls['pinned_sessions'].setChecked(False)
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.Cancel)
    dialog.accept()
    assert window._features.enabled('pinned_sessions')
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.Yes)
    dialog.accept()
    assert not window._features.enabled('pinned_sessions')
    assert session_fingerprint(window._repo.load_session()) == before
    assert window._pinned_assignments() == assignments
    assert not window._feature_notice.isHidden()
    assert 'fijadas' in window._feature_notice.text()
    window._toggle_pin('BIO-G1')
    assert window.pinned_group_ids == {'BIO-G1'}
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: QMessageBox.StandardButton.Cancel)
    assert not window._confirm_pin_inputs(classrooms={})
    restarted = MainWindow(window._repo, restore_session=False, feature_settings=settings_at(tmp_path/'preferences.ini'))
    restarted._restore_session_if_exists(confirm=False)
    assert restarted.pinned_group_ids == {'BIO-G1'}
    assert restarted._pinned_assignments() == assignments
    assert not restarted._feature_notice.isHidden()
    restarted.close()


def test_existing_catalog_notice_does_not_open_or_change_catalog(window, tmp_path):
    path = tmp_path/'sorth_projects.db'
    path.write_bytes(b'opaque future catalog')
    window._apply_feature_preferences()
    assert not window._feature_notice.isHidden()
    window._show_projects()
    assert path.read_bytes() == b'opaque future catalog'


def test_settings_localize_while_open(window):
    manager = language_manager()
    previous = manager.language
    dialog = SettingsDialog(window)
    try:
        manager.set_language('en', persist=False)
        assert dialog.windowTitle() == 'Settings'
        assert dialog.controls['pinned_sessions'].text() == 'Pinned sessions'
        assert dialog.controls['pinned_sessions'].accessibleName() == 'Pinned sessions'
        manager.set_language('es', persist=False)
        assert dialog.windowTitle() == 'Configuración'
    finally:
        manager.set_language(previous, persist=False)
        dialog.reject()


def test_escape_dismisses_without_saving(window):
    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import Qt
    dialog = SettingsDialog(window)
    dialog.controls['pinned_sessions'].setChecked(True)
    dialog.show()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()
    assert not window._features.enabled('pinned_sessions')


def test_save_failure_keeps_dialog_open_and_preferences(window, monkeypatch):
    dialog = SettingsDialog(window)
    dialog.controls['pinned_sessions'].setChecked(True)
    def fail_save(values):
        raise OSError('read only')
    monkeypatch.setattr(window._features, 'save', fail_save)
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args[2]))
    dialog.show()
    dialog.accept()
    assert dialog.isVisible()
    assert warnings
    assert not window._features.enabled('pinned_sessions')
    dialog.reject()
