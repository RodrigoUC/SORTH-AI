from copy import deepcopy
import pytest
from PyQt6.QtCore import QSettings
from src.gui.course_manager_widget import CourseDialog
from src.gui.bulk_course_dialog import BulkCourseDialog
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.project_calendar import ProjectCalendar


@pytest.mark.parametrize('minute',[0,360,1380,1439])
@pytest.mark.parametrize('calendar',[ProjectCalendar(),ProjectCalendar(('Domingo',),0,1440,())])
def test_unrelated_edit_preserves_sunday_and_any_valid_minute(minute,calendar):
    course=Course('SUN',1,60,'REGULAR',name='Original',preferred_day='Domingo',preferred_start_min=minute,
                  group_suggestions=[{'aula':None,'preferred_day':'Domingo','preferred_start_min':minute}])
    before=deepcopy(vars(course))
    dialog=CourseDialog(course=course,calendar=calendar)
    assert dialog.day_combo.currentData()=='Domingo'
    assert dialog.pref_time_edit.time().hour()*60+dialog.pref_time_edit.time().minute()==minute
    dialog.name_edit.setText('Renamed')
    result=dialog.get_course()
    expected={**before,'name':'Renamed'}
    assert vars(result)==expected
    assert vars(course)==before
    dialog.reject()


def test_default_new_course_choices_and_initial_time_unchanged():
    dialog=CourseDialog()
    assert [dialog.day_combo.itemData(i) for i in range(dialog.day_combo.count())]==[None,*ProjectCalendar().days]
    assert dialog.pref_time_edit.time().hour()==8
    assert not dialog.chk_pref_time.isChecked()
    dialog.reject()


@pytest.fixture
def window(tmp_path):
    w=MainWindow(SessionRepository(str(tmp_path/'session.db')),restore_session=False,
                 feature_settings=QSettings(str(tmp_path/'prefs.ini'),QSettings.Format.IniFormat))
    w.course_manager.courses=[Course('SUN',1,60,'REGULAR',preferred_day='Domingo',preferred_start_min=1380)]
    w.course_manager._refresh_table()
    yield w
    w._unsaved=False
    w.close()


def test_manager_passes_current_calendar_on_every_open(window,monkeypatch):
    seen=[]
    def cancel(dialog):
        seen.append(dialog.calendar)
        return 0
    monkeypatch.setattr(CourseDialog,'exec',cancel)
    window.calendar=ProjectCalendar(('Domingo',),0,1440,())
    window.course_manager.edit_course_by_code('SUN')
    window.course_manager._edit_course()
    window.course_manager._add_course()
    assert seen==[window.calendar]*3
    window.calendar=ProjectCalendar(('Martes',),360,1440,())
    window.course_manager.edit_course_by_code('SUN')
    assert seen[-1]==window.calendar


@pytest.mark.parametrize('active_sunday',[True,False])
def test_bulk_active_and_latent_sunday_can_roundtrip_without_clearing(window,monkeypatch,active_sunday):
    window.calendar=ProjectCalendar(('Domingo',),0,1440,()) if active_sunday else ProjectCalendar()
    monkeypatch.setattr(window.course_manager,'selected_course_codes',lambda:('SUN',))
    dialog=BulkCourseDialog(window)
    assert dialog.inputs['preferred_day'].currentData()=='Domingo'
    assert dialog.inputs['preferred_day'].findData('Domingo')>=0
    dialog.checks['size'].setChecked(True)
    dialog.inputs['size'].setValue(12)
    dialog._review()
    assert dialog.plan is not None
    candidate=dialog.plan.candidate
    assert candidate['courses'][0].preferred_day=='Domingo'
    assert candidate['courses'][0].preferred_start_min==1380
    dialog.reject()


def test_locale_switch_preserves_latent_day_and_time():
    from src.gui.i18n import language_manager
    manager=language_manager(); previous=manager.language
    course=Course('SUN',1,60,'REGULAR',preferred_day='Domingo',preferred_start_min=1380)
    dialog=CourseDialog(course=course,calendar=ProjectCalendar())
    try:
        for language,label in [('en','Sunday'),('es','Domingo')]:
            manager.set_language(language,persist=False)
            assert dialog.day_combo.currentText()==label
            assert dialog.day_combo.currentData()=='Domingo'
            assert dialog.get_course().preferred_start_min==1380
    finally:
        manager.set_language(previous,persist=False)
        dialog.reject()
