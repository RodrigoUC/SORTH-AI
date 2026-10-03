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
