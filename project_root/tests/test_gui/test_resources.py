from dataclasses import replace
from PyQt6.QtCore import QSettings, QTime, Qt
from PyQt6.QtWidgets import QDialog, QMessageBox, QApplication
import pytest
from src.gui.main_window import MainWindow
from src.gui.settings_dialog import SettingsDialog
from src.gui.manual_assignment_dialog import ManualAssignmentDialog
from src.gui.resource_dialog import ResourceDialog, ResourceEditor
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources, RESOURCE_KINDS
from src.scheduling.time_model import TimeModel
from tests.test_scheduling.test_teaching_resources import data


@pytest.fixture
def window(tmp_path):
    w=MainWindow(SessionRepository(str(tmp_path/'session.db')),restore_session=False,
                 feature_settings=QSettings(str(tmp_path/'settings.ini'),QSettings.Format.IniFormat))
    courses,groups,rooms,resources=data()
    w._classrooms=rooms
    w.course_manager.load_courses_from_excel(courses)
    w.current_groups=groups
    w.current_schedule={groups[0].group_id:('R1',1,480,540)}
    groups[0].assignment=w.current_schedule[groups[0].group_id]
    yield w
    w._unsaved=False;w.close()


def activate(window,kind):
    resources=data(kind)[3]
    window.resources=resources
    values=window._features.values();values[kind]=True
    window._features.save(values);window._apply_feature_preferences()
    assert window._save_session()


@pytest.mark.parametrize('kind',RESOURCE_KINDS)
def test_parameter_off_cancel_then_confirm_preserves_data_and_clears_result(window,monkeypatch,kind):
    activate(window,kind)
    original=window.resources.catalog(kind)
    original_schedule=dict(window.current_schedule)
    dialog=SettingsDialog(window);dialog.controls[kind].setChecked(False)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Cancel)
    dialog.accept()
    assert window.resources.catalog(kind).enabled
    assert window.current_schedule==original_schedule
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    dialog.accept()
    assert not window.resources.catalog(kind).enabled
    assert window.resources.catalog(kind).resources==original.resources
    assert window.resources.catalog(kind).memberships==original.memberships
    assert window.current_schedule is None and not window.pinned_group_ids
    assert window.resource_buttons[kind].isHidden()
    assert 'sin restricciones' in window._feature_notice.text()
    assert not window._repo.load_session()['resources'].catalog(kind).enabled


def test_failed_disable_restores_configuration_and_live_schedule(window,monkeypatch):
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:QMessageBox.StandardButton.Ok)
    activate(window,'teacher');before=window.resources;schedule=dict(window.current_schedule)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    def fail(**kwargs):raise OSError('Synthetic save failure')
    monkeypatch.setattr(window._repo,'save_session',fail)
    dialog=SettingsDialog(window);dialog.controls['teacher'].setChecked(False);dialog.accept()
    assert window.resources==before and window.current_schedule==schedule
    assert window._features.enabled('teacher')


@pytest.mark.parametrize('kind',RESOURCE_KINDS)
def test_manual_placement_uses_same_resource_validator(window,kind):
    activate(window,kind)
    dialog=ManualAssignmentDialog(window.current_groups[1],window.current_groups,window.current_schedule,
                window._classrooms,TimeModel.default(),resources=window.resources)
    dialog.room.setCurrentIndex(dialog.room.findData('R2'))
    dialog.day.setCurrentIndex(dialog.day.findData(1));dialog.start.setTime(QTime(8,0))
    dialog._submit()
    assert dialog.result_assignment is None
    assert 'solapan' in dialog.error.text()
    dialog.start.setTime(QTime(9,0));dialog._submit()
    assert dialog.result_assignment==('R2',1,540,600)


def test_resource_dialog_cancel_keeps_original_and_rename_preserves_id(window):
    original=data()[3].catalog('teacher')
    dialog=ResourceDialog(original,window.current_groups,TimeModel.default())
    dialog.resources[0]=replace(dialog.resources[0],label='Renamed alias')
    dialog.reject()
    assert original.resources[0].label=='Alias'
    assert dialog.result_catalog is None
    dialog._submit()
    assert dialog.result_catalog.resources[0].id==original.resources[0].id


def test_availability_editor_unknown_declared_empty_and_24h(window,monkeypatch):
    resource=Resource('synthetic','Alias',((1,0,1440),))
    editor=ResourceEditor(resource,TimeModel.default());editor._submit()
    assert editor.result_resource==resource
    editor=ResourceEditor(resource,TimeModel.default());editor.declared.setChecked(False);editor._submit()
    assert editor.result_resource.availability is None
    editor=ResourceEditor(Resource('synthetic','Alias'),TimeModel.default());editor.declared.setChecked(True)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Cancel)
    editor._submit();assert editor.result_resource is None
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    editor._submit();assert editor.result_resource.availability==()


def test_orphan_course_change_cancel_and_accept_are_explicit(window,monkeypatch):
    activate(window,'teacher');original=window.resources
    courses=window.course_manager.get_courses()[:1]
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Cancel)
    assert not window._confirm_course_inputs(courses)
    assert window.resources==original
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    assert window._confirm_course_inputs(courses)
    assert len(window.resources.catalog('teacher').memberships)==1
    assert window.resources.catalog('teacher').resources==original.catalog('teacher').resources


def test_restore_preserves_off_coverage_with_records(window):
    activate(window,'teacher')
    off=replace(window.resources.catalog('teacher'),enabled=False)
    assert window._commit_resource_change(SchedulingResources((off,)),clear_schedule=True)
    window._restore_session_if_exists(confirm=False,show_status=False)
    assert not window._restore_failed
    assert not window.resources.catalog('teacher').enabled
    assert not window._features.enabled('teacher')
    assert window.resources.catalog('teacher').memberships==off.memberships


def test_busy_blocks_resource_parameter_changes(window):
    window._set_busy(True)
    values=window._features.values();values['teacher']=True
    assert not window._apply_resource_parameters(values)
    assert not window.resources.catalog('teacher').enabled
    assert not window.btn_settings.isEnabled()
    window._set_busy(False)


def test_corrupt_preferences_do_not_hide_or_disable_restored_resources(window,monkeypatch):
    activate(window,'teacher')
    schedule=dict(window.current_schedule)
    path=window._features.path
    path.write_text('{broken synthetic preferences',encoding='utf-8')
    from src.gui.features import FeaturePreferences
    window._features=FeaturePreferences(window._features.settings)
    assert window._features.load_error
    window._restore_session_if_exists(confirm=False,show_status=False)
    assert not window._restore_failed
    assert window.resources.catalog('teacher').enabled
    assert not window.resource_buttons['teacher'].isHidden()
    assert window.current_schedule==schedule
    dialog=SettingsDialog(window)
    assert dialog.controls['teacher'].isChecked()
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    dialog.recover_preferences()
    assert window._features.enabled('teacher')
    assert window.resources.catalog('teacher').enabled
    assert window.current_schedule==schedule
    assert list(path.parent.glob(path.name+'.preserved-*.bak'))


def test_atomic_preference_failure_cannot_disable_resources(window,monkeypatch):
    activate(window,'teacher');before=window.resources;schedule=dict(window.current_schedule)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:None)
    def fail(_record):raise OSError('Synthetic atomic preference failure')
    monkeypatch.setattr(window._features,'_write_atomic',fail)
    dialog=SettingsDialog(window);dialog.controls['teacher'].setChecked(False);dialog.accept()
    assert window.resources==before and window.current_schedule==schedule
    assert window._features.enabled('teacher')


def test_dialog_retranslates_availability_without_replacing_literal_alias(window):
    from src.gui.i18n import language_manager
    manager=language_manager();old=manager.language
    catalog=ResourceCatalog('teacher',True,(Resource('shared-prefix-001','Guardar'),Resource('shared-prefix-002','Guardar')))
    dialog=ResourceDialog(catalog,window.current_groups,TimeModel.default())
    try:
        manager.set_language('en',persist=False)
        assert 'Availability not declared' in dialog.list.item(0).text()
        assert 'Guardar' in dialog.list.item(0).text()
        assert 'shared-prefix-001' in dialog.list.item(0).text()
        assert 'shared-prefix-002' in dialog.list.item(1).text()
    finally:
        manager.set_language(old,persist=False);dialog.close()


def test_removing_unpinned_course_does_not_unpin_valid_resource_session(window,monkeypatch):
    activate(window,'teacher')
    first=window.current_groups[0].group_id
    window.pinned_group_ids={first}
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:warnings.append(a) or QMessageBox.StandardButton.Cancel)
    assert window._confirm_course_inputs(window.course_manager.get_courses()[:1])
    assert window.pinned_group_ids=={first}
    assert not warnings


@pytest.mark.parametrize('kind', RESOURCE_KINDS)
def test_failed_resource_parameter_presentation_preserves_session_preferences_and_history(window, monkeypatch, kind):
    from pathlib import Path
    from src.application.edit_history import encoded
    activate(window, kind)
    window._features.save({**window._features.values(), 'undo_redo': True})
    before = encoded(window._capture_edit_state())
    history = encoded(vars(window._history))
    database = Path(window._repo._db_path).read_bytes()
    preferences = window._features.path.read_bytes()
    original = window._display_edit_state
    calls = []
    def fail_once(state):
        original(state)
        if not calls:
            calls.append(True)
            raise RuntimeError('resource presentation failed')
    monkeypatch.setattr(window, '_display_edit_state', fail_once)
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    dialog = SettingsDialog(window)
    dialog.controls[kind].setChecked(False)
    dialog.accept()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert encoded(window._capture_edit_state()) == before
    assert encoded(vars(window._history)) == history
    assert Path(window._repo._db_path).read_bytes() == database
    assert window._features.path.read_bytes() == preferences
    assert window.resources.catalog(kind).enabled and not window._restore_failed


def test_preference_rollback_failure_locks_but_session_flags_remain_authoritative(window, monkeypatch):
    from pathlib import Path
    activate(window, 'teacher')
    original_resources = window.resources
    database = Path(window._repo._db_path).read_bytes()
    save_preferences = window._features.save
    calls = []
    def preference_failure(values):
        calls.append(True)
        if len(calls) == 2:
            raise OSError('rollback preferences unavailable')
        return save_preferences(values)
    monkeypatch.setattr(window._features, 'save', preference_failure)
    monkeypatch.setattr(window._repo, 'save_session', lambda **kwargs: (_ for _ in ()).throw(OSError('session unavailable')))
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: warnings.append(str(args[2])) or QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    dialog = SettingsDialog(window)
    dialog.controls['teacher'].setChecked(False)
    dialog.accept()
    assert window._restore_failed and window._busy and window._features.load_error
    assert window.resources == original_resources
    assert Path(window._repo._db_path).read_bytes() == database
    assert any('preferencias' in text or 'preferences' in text for text in warnings)
    # The cached JSON flag is stale, but cannot silently turn the saved rules off.
    assert not window._features.enabled('teacher')
    reopened = MainWindow(SessionRepository(window._repo._db_path), restore_session=False,
                          feature_settings=window._features.settings)
    assert not reopened.resources.catalog('teacher').enabled
    reopened._restore_session_if_exists(confirm=False, show_status=False)
    assert reopened.resources == original_resources
    assert not reopened._restore_failed
    reopened._unsaved = False
    reopened.close()


def test_postcommit_settings_presentation_failure_is_locked_and_truthful(window, monkeypatch):
    activate(window, 'teacher')
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(window, '_apply_feature_preferences', lambda: (_ for _ in ()).throw(RuntimeError('late settings view')))
    dialog = SettingsDialog(window)
    dialog.controls['teacher'].setChecked(False)
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert window._restore_failed and window._busy
    assert not window._repo.load_session()['resources'].catalog('teacher').enabled
    assert not window.resources.catalog('teacher').enabled
    assert 'se guardó' in window.status_bar.currentMessage() or 'saved' in window.status_bar.currentMessage()
