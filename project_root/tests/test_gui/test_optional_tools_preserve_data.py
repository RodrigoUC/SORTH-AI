import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.gui.main_window import MainWindow
from src.gui.settings_dialog import SettingsDialog
from src.infrastructure.session_repository import SessionRepository
from src.infrastructure.project_repository import ProjectRepository
from src.application.scenario_comparison import scenario_metadata
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom

def test_disable_tools_preserves_active_pin_scenario_and_enforcement(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    repo=SessionRepository(str(tmp_path/'session.db'))
    q=QSettings(str(tmp_path/'preferences.ini'),QSettings.Format.IniFormat)
    w=MainWindow(repo,restore_session=False,feature_settings=q)
    w._features.save({**w._features.values(), 'pinned_sessions':True,'project_scenarios':True});w._apply_feature_preferences()
    w._classrooms={'R':Classroom('R',30,'REGULAR')}
    w.course_manager.load_courses_from_excel([Course('A',1,60,'REGULAR')])
    groups=w.course_manager.get_courses()[0].generate_groups()
    assignments={'A-G1':('R',1,480,540)};groups[0].assignment=assignments['A-G1']
    w._on_schedule_done(assignments,groups);w._toggle_pin('A-G1')
    catalog=ProjectRepository(tmp_path/'sorth_projects.db')
    _,sid=catalog.create_project('Project','Scenario',repo,scenario_metadata())
    w._scenario_id=sid;w._scenario_name='Project / Scenario'
    original=(tmp_path/'session.db').read_bytes();snapshot=catalog.path.read_bytes()
    dialog=SettingsDialog(w)
    for control in dialog.controls.values():control.setChecked(False)
    prompts=[]
    monkeypatch.setattr(QMessageBox,'question',lambda *a: prompts.append(a[2]) or QMessageBox.StandardButton.Yes)
    dialog.accept()
    assert prompts
    assert w.btn_projects.isHidden()
    assert all(control.isHidden() for control in w.schedule_viewer._pin_controls)
    assert w.current_schedule==assignments and w.pinned_group_ids=={'A-G1'}
    assert (tmp_path/'session.db').read_bytes()==original and catalog.path.read_bytes()==snapshot
    assert w._scenario_id==sid
    assert w._pinned_assignments()==assignments
    assert not w._feature_notice.isHidden()
    w._show_projects()
    assert catalog.path.read_bytes()==snapshot
    assert not w._features.enabled('project_scenarios')
    w.close();app.processEvents()
