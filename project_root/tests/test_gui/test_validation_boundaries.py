import pytest
from PyQt6.QtWidgets import QDialog, QFileDialog
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom


@pytest.fixture
def window(tmp_path):
    win = MainWindow(SessionRepository(str(tmp_path/'session.db')),restore_session=False)
    win._classrooms = {'A': Classroom('A',20,'REGULAR')}
    win.course_manager.load_courses_from_excel([Course('C',2,60,'REGULAR')])
    yield win
    win._unsaved = False
    win.close()


def test_corrupt_worker_result_never_displays_or_saves(window,monkeypatch):
    errors=[]
    monkeypatch.setattr(window,'_on_schedule_error',errors.append)
    monkeypatch.setattr(window.schedule_viewer,'display_schedule',lambda *a: pytest.fail('Must not display'))
    monkeypatch.setattr(window,'_save_session',lambda: pytest.fail('Must not save'))
    window._on_schedule_done({'C-G1':('A',1,700,760)},window.course_manager.get_courses()[0].generate_groups())
    assert errors and window.current_schedule is None


@pytest.mark.parametrize('count',[0,1,2])
def test_complete_partial_and_zero_status(window,count):
    groups=window.course_manager.get_courses()[0].generate_groups()
    assignments={g.group_id:('A',1,420+i*60,480+i*60) for i,g in enumerate(groups[:count])}
    window._on_schedule_done(assignments,groups)
    message=window.status_bar.currentMessage()
    assert f'{count}/2' in message
    assert ('parcial' in message) == (count<2)
    assert window.btn_export.isEnabled() == (count>0)


def test_partial_export_dialog_keeps_pending_warning_and_scope(window,monkeypatch):
    groups=window.course_manager.get_courses()[0].generate_groups()
    window._on_schedule_done({groups[0].group_id:('A',1,420,480)},groups)
    titles=[]
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args: titles.append(args[1]) or ('',''))
    window._export_schedule()
    window._export_schedule(filtered=True)
    assert len(titles)==2 and all('parcial, 1 pendientes' in title for title in titles)
    assert 'todas las asignaciones' in titles[0] and 'filtrado' in titles[1]


def test_restored_constraint_violation_blocks_presentation_and_overwrite(window,monkeypatch):
    window._repo.save_session(None,42,window._classrooms,window.course_manager.get_courses(),{}, {'C-G1':('A',1,700,760)})
    monkeypatch.setattr(QDialog,'exec',lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(window.schedule_viewer,'display_schedule',lambda *args: pytest.fail('Invalid restore must not display'))
    window._restore_session_if_exists()
    assert window._restore_failed and not window._save_session()
    assert not window.btn_export.isEnabled()
    assert window._repo.load_session()['assignments']=={'C-G1':('A',1,700,760)}


def test_removing_assignment_updates_complete_status(window):
    groups=window.course_manager.get_courses()[0].generate_groups()
    assignments={g.group_id:('A',1,420+i*60,480+i*60) for i,g in enumerate(groups)}
    for group in groups:
        group.assignment=assignments[group.group_id]
    window._on_schedule_done(assignments,groups)
    window._on_group_removed(groups[0].group_id)
    assert 'parcial: 1/2' in window.status_bar.currentMessage()
    assert '1 pendientes' in window.status_bar.currentMessage()
    assert groups[0].unassigned_reason
