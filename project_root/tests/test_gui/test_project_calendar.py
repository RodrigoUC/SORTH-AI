import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox
from src.gui.main_window import MainWindow
from src.gui.calendar_dialog import CalendarDialog
from src.gui.i18n import language_manager
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.project_calendar import ProjectCalendar
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.application.calendar_transition import preview_calendar_change


@pytest.fixture
def window(tmp_path):
    window=MainWindow(SessionRepository(str(tmp_path/'session.db')),restore_session=False,
                      feature_settings=QSettings(str(tmp_path/'prefs.ini'),QSettings.Format.IniFormat))
    window._classrooms={'A':Classroom('A',50,'REGULAR')}
    window.current_groups=Course(code='C',name='Course',number_of_groups=1,duration_min=60,required_room_type='REGULAR').generate_groups()
    yield window
    window._unsaved=False
    window.close()


def test_cancel_leaves_calendar_and_database_unchanged(window):
    window._save_session()
    before=window._repo.load_session()['calendar']
    dialog=CalendarDialog(window)
    dialog.days['Lunes'].setChecked(False)
    dialog.reject()
    assert window.calendar == before == window._repo.load_session()['calendar']


def test_atomic_failure_preserves_memory_and_disk(window,monkeypatch):
    window._save_session()
    calendar=ProjectCalendar(('Martes',),480,600,())
    preview=preview_calendar_change(window.calendar,calendar,{},[],{})
    monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(window._repo,'save_session',lambda **kwargs: (_ for _ in ()).throw(OSError('disk full')))
    assert not window._apply_calendar(calendar,preview)
    assert window.calendar == window._repo.load_session()['calendar'] == ProjectCalendar()


def test_apply_hidden_controls_reopen_and_reset(window,monkeypatch):
    calendar=ProjectCalendar(('Martes',),480,600,())
    preview=preview_calendar_change(window.calendar,calendar,{},[],{})
    assert window._apply_calendar(calendar,preview)
    assert not window._features.enabled('project_calendar')
    assert window._feature_notice.text()
    window._restore_session_if_exists(confirm=False)
    assert window.calendar == calendar
    assert window._repo.load_session()['calendar'] == calendar
    dialog=CalendarDialog(window)
    dialog.load(ProjectCalendar())
    dialog.reject()
    assert window.calendar == calendar


def test_preview_cancel_and_pins(window,monkeypatch):
    gid=window.current_groups[0].group_id
    window.current_schedule={gid:('A',1,480,540)}
    window.pinned_group_ids={gid}
    dialog=CalendarDialog(window)
    dialog.days['Lunes'].setChecked(False)
    dialog.accept()
    assert dialog.feedback.text()
    assert window.calendar == ProjectCalendar()
    window.pinned_group_ids.clear()
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k: QMessageBox.StandardButton.Cancel)
    dialog.accept()
    assert window.current_schedule == {gid:('A',1,480,540)}


@pytest.mark.parametrize('language',['es','en'])
def test_native_editor_accessible_and_localized(window,language):
    language_manager().set_language(language,persist=False)
    dialog=CalendarDialog(window)
    assert dialog.opening.accessibleName()
    assert dialog.breaks.accessibleName()
    assert len(dialog.days)==7
    assert dialog.value()==ProjectCalendar()
    assert dialog.windowTitle() == ('Calendario del proyecto' if language=='es' else 'Project calendar')
    dialog.reject()


def test_manual_uses_custom_opening_days_and_breaks(window):
    from PyQt6.QtCore import QTime
    from src.gui.manual_assignment_dialog import ManualAssignmentDialog
    from src.scheduling.time_model import TimeModel
    calendar=ProjectCalendar(('Viernes',),900,1080,((960,990),))
    group=window.current_groups[0]
    dialog=ManualAssignmentDialog(group,[group],{},window._classrooms,TimeModel.from_calendar(calendar))
    assert dialog.day.count()==1
    assert dialog.start.time()==QTime(15,0)
    dialog.room.setCurrentIndex(1)
    dialog.start.setTime(QTime(15,30))
    dialog._submit()
    assert dialog.result_assignment is None
    dialog.start.setTime(QTime(16,30))
    dialog._submit()
    assert dialog.result_assignment==('A',1,990,1050)


def test_calendar_apply_preserves_explicit_resources_and_pins(window):
    from src.scheduling.teaching_resources import SchedulingResources, ResourceCatalog, Resource
    course=Course('C',1,60,'REGULAR')
    window.course_manager.load_courses_from_excel([course])
    window.current_groups=course.generate_groups()
    gid=window.current_groups[0].group_id
    window.current_schedule={gid:('A',2,480,540)}
    window.current_groups[0].assignment=window.current_schedule[gid]
    window.pinned_group_ids={gid}
    window.resources=SchedulingResources((ResourceCatalog('teacher',True,(Resource('t','Teacher',((2,480,600),)),),((gid,('t',)),)),))
    calendar=ProjectCalendar(('Martes',),480,600,())
    preview=preview_calendar_change(window.calendar,calendar,window.current_schedule,window.current_groups,window._classrooms,resources=window.resources)
    assert not preview.affected
    assert window._apply_calendar(calendar,preview)
    restored=window._repo.load_session()
    assert restored['pinned_group_ids']=={gid}
    assert restored['assignments'][gid]==('A',1,480,540)
    assert restored['resources'].catalog('teacher').resources[0].availability==((1,480,600),)


def test_calendar_undo_redo_is_persistent_and_preserves_soft_preferences(window):
    from src.gui.features import FEATURES
    course=Course('C',1,60,'REGULAR',preferred_day='Lunes')
    window.course_manager.load_courses_from_excel([course])
    window.current_groups=course.generate_groups()
    window.current_schedule={'C-G1':('A',2,480,540)}
    window.current_groups[0].assignment=window.current_schedule['C-G1']
    window._features.save({feature.key:feature.key=='undo_redo' for feature in FEATURES})
    window._save_session()
    calendar=ProjectCalendar(('Martes',),480,600,())
    preview=preview_calendar_change(window.calendar,calendar,window.current_schedule,window.current_groups,window._classrooms,resources=window.resources)
    assert window._apply_calendar(calendar,preview)
    assert window._history.can_undo
    assert window._travel_history(True)
    assert window.calendar==ProjectCalendar()
    assert window.current_schedule['C-G1'][1]==2
    assert window._repo.load_session()['calendar']==ProjectCalendar()
    assert window._travel_history(False)
    assert window.calendar==calendar
    assert window.current_schedule['C-G1'][1]==1
    assert window._repo.load_session()['calendar']==calendar
    assert window.course_manager.get_courses()[0].preferred_day=='Lunes'


def test_day_filter_keeps_weekday_identity_after_calendar_change(window):
    course=Course('C',1,60,'REGULAR')
    window.course_manager.load_courses_from_excel([course])
    window.current_groups=course.generate_groups()
    window.current_schedule={'C-G1':('A',2,480,540)}
    from src.scheduling.time_model import TimeModel
    window.schedule_viewer.display_schedule(window.current_schedule,TimeModel.from_calendar(window.calendar),window.current_groups,classrooms=window._classrooms)
    control=window.schedule_viewer._day_filter
    control.setCurrentIndex(control.findData(2))
    calendar=ProjectCalendar(('Martes','Viernes'),480,600,())
    preview=preview_calendar_change(window.calendar,calendar,window.current_schedule,window.current_groups,window._classrooms,resources=window.resources)
    assert window._apply_calendar(calendar,preview)
    assert control.currentData()==1


def test_sunday_manual_save_export_and_undo_preserve_weekdays(window,tmp_path):
    import pandas as pd
    from src.scheduling.project_calendar import DAYS
    from src.scheduling.time_model import TimeModel
    from src.scheduling.teaching_resources import SchedulingResources, ResourceCatalog, Resource
    from src.gui.manual_assignment_dialog import ManualAssignmentDialog
    from src.gui.features import FEATURES
    from src.infrastructure.schedule_exporter import ScheduleExporter
    course=Course('SUN',1,60,'REGULAR')
    window.course_manager.load_courses_from_excel([course])
    window.current_groups=course.generate_groups()
    window._features.save({f.key:f.key=='undo_redo' for f in FEATURES})
    calendar=ProjectCalendar(DAYS,480,600,())
    preview=preview_calendar_change(window.calendar,calendar,{},window.current_groups,window._classrooms,resources=window.resources)
    assert window._apply_calendar(calendar,preview)
    assert window._travel_history(True) and 'Domingo' not in window.calendar.days
    assert window._travel_history(False) and window.calendar==calendar
    group=window.current_groups[0]
    resources=SchedulingResources((ResourceCatalog('teacher',True,(Resource('t','T',((7,480,600),)),),((group.group_id,('t',)),)),))
    dialog=ManualAssignmentDialog(group,[group],{},window._classrooms,TimeModel.from_calendar(calendar),resources=resources)
    dialog.room.setCurrentIndex(1)
    dialog.day.setCurrentIndex(dialog.day.findData(7))
    dialog._submit()
    assert dialog.result_assignment==('A',7,480,540)
    window._repo.save_session(None,42,window._classrooms,[course],{}, {group.group_id:dialog.result_assignment},calendar=calendar,resources=resources)
    restored=SessionRepository(window._repo._db_path).load_session()
    assert restored['calendar']==calendar
    exporter=ScheduleExporter(TimeModel.from_calendar(restored['calendar']))
    for suffix in ('csv','xlsx'):
        path=tmp_path/f'sunday.{suffix}'
        if suffix=='csv':exporter.to_csv(restored['assignments'],str(path))
        else:exporter.to_excel(restored['assignments'],str(path))
        table=pd.read_csv(path) if suffix=='csv' else pd.read_excel(path,sheet_name='Asignaciones')
        assert table.iloc[0]['Día']=='Domingo'
