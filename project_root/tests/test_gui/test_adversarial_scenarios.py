import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from copy import deepcopy
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.gui.main_window import MainWindow
from src.gui.project_dialog import ProjectDialog
from src.infrastructure.session_repository import SessionRepository
from src.application.scenario_comparison import scenario_metadata
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom

@pytest.mark.parametrize('kind',['future_format','future_calendar','nondict_metadata'])
def test_unsupported_snapshot_never_replaces_working(tmp_path, monkeypatch, kind):
    repo=SessionRepository(str(tmp_path/'working.db'))
    window=MainWindow(repo,restore_session=False)
    window._classrooms={'R':Classroom('R',30,'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('OLD',1,60,'REGULAR')])
    assert window._save_session()
    dialog=ProjectDialog(window)
    meta=scenario_metadata()
    if kind=='future_format': meta['format_version']=999
    elif kind=='future_calendar': meta['calendar']['end']=1260
    else: meta=[]
    source=SessionRepository(str(tmp_path/'alternative.db'))
    source.save_session(None,99,{'R':Classroom('R',30,'REGULAR')},[Course('NEW',1,60,'REGULAR')],{}, {})
    _, sid=dialog.catalog.create_project('future','scenario',source,meta)
    dialog.refresh()
    dialog.table.selectRow(next(i for i,r in enumerate(dialog.rows) if r['id']==sid))
    before=(tmp_path/'working.db').read_bytes()
    monkeypatch.setattr(QMessageBox,'question',lambda *a: QMessageBox.StandardButton.Yes)
    dialog._run(dialog.open_selected)
    assert (tmp_path/'working.db').read_bytes()==before
    assert [c.code for c in window.course_manager.get_courses()]==['OLD']
    actual=[c.code for c in repo.load_session()['courses']]
    window._unsaved=False
    dialog.close(); window.close()
    assert actual==['OLD'], f'Unsupported {kind} replaced working data with {actual}'

def test_unrenderable_seed_never_replaces_working(tmp_path, monkeypatch):
    repo=SessionRepository(str(tmp_path/'working.db'))
    window=MainWindow(repo,restore_session=False)
    window._classrooms={'R':Classroom('R',30,'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('OLD',1,60,'REGULAR')])
    assert window._save_session()
    dialog=ProjectDialog(window)
    source=SessionRepository(str(tmp_path/'alternative.db'))
    source.save_session(None,2**40,{'R':Classroom('R',30,'REGULAR')},[Course('NEW',1,60,'REGULAR')],{}, {})
    _,sid=dialog.catalog.create_project('badseed','scenario',source,scenario_metadata())
    dialog.refresh(); dialog.table.selectRow(next(i for i,r in enumerate(dialog.rows) if r['id']==sid))
    before=(tmp_path/'working.db').read_bytes()
    monkeypatch.setattr(QMessageBox,'question',lambda *a: QMessageBox.StandardButton.Yes)
    dialog._run(dialog.open_selected)
    actual=repo.load_session()
    window._unsaved=False; dialog.close(); window.close()
    assert [c.code for c in actual['courses']]==['OLD'], f'Open failure modified working session: seed={actual["seed"]}'
    assert (tmp_path/'working.db').read_bytes()==before
