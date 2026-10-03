import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
from src.gui.manual_assignment_dialog import ManualAssignmentDialog
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.group import Group
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.time_model import TimeModel

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])

@pytest.mark.parametrize('answer,accepted', [(QMessageBox.StandardButton.Yes, True), (QMessageBox.StandardButton.No, False)])
def test_exception_requires_positive_confirmation(app, monkeypatch, answer, accepted):
    g = Group('B', 60, 'LAB')
    dialog = ManualAssignmentDialog(g, [g], {}, {'A': Classroom('A', 30, 'REGULAR')}, TimeModel.default())
    dialog.room.setCurrentIndex(1)
    calls = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: calls.append(args) or answer)
    dialog._submit()
    assert len(calls) == 1
    assert (dialog.result() == QDialog.DialogCode.Accepted) is accepted
    assert dialog.lab_override is accepted
    assert g.assignment is None  # cancel/dialog itself never mutates live session
    dialog.close()


def test_conflict_rejected_before_exception_prompt(app, monkeypatch):
    g, other = Group('B', 60, 'LAB'), Group('C', 60, 'REGULAR')
    dialog = ManualAssignmentDialog(g, [g, other], {'C': ('A', 1, 420, 480)},
                                    {'A': Classroom('A', 30, 'REGULAR')}, TimeModel.default())
    dialog.room.setCurrentIndex(1)
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: pytest.fail('Must reject conflict first'))
    dialog._submit()
    assert 'conflicto' in dialog.error.text()
    assert dialog.result_assignment is None
    dialog.close()


def test_all_pending_can_be_displayed_and_manually_assigned(app, tmp_path, monkeypatch):
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    course = Course('BIO', 1, 60, 'LAB')
    window._classrooms = {'A': Classroom('A', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([course])
    groups = course.generate_groups()
    groups[0].unassigned_reason = 'No hay laboratorios configurados.'
    window._on_schedule_done({}, groups)
    assert window.schedule_viewer.list_table.rowCount() == 1
    assert not window.btn_export.isEnabled()
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.StandardButton.Yes)
    def accept(dialog):
        dialog.room.setCurrentIndex(1)
        dialog._submit()
        return dialog.result()
    monkeypatch.setattr(ManualAssignmentDialog, 'exec', accept)
    window._manual_assignment(groups[0].group_id)
    assert window.current_schedule and window.current_groups[0].lab_override
    assert window.btn_export.isEnabled()
    assert window._repo.load_session()['lab_overrides'] == {groups[0].group_id}
    assert 'Excepción manual' in window.schedule_viewer.list_table.item(0, 7).text()
    window.close()


def test_invalid_lab_assignment_is_blocked_before_export(app, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QFileDialog
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    g = Group('BIO-G1', 60, 'LAB')
    window.current_groups = [g]
    window._classrooms = {'A': Classroom('A', 30, 'REGULAR')}
    window.current_schedule = {g.group_id: ('A', 1, 420, 480)}
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: pytest.fail('Invalid export must be blocked'))
    window._export_schedule()
    assert warnings and 'excepción' in warnings[0][2]
    window.close()


def test_lab_room_needs_no_exception_prompt(app, monkeypatch):
    g = Group('B', 60, 'LAB')
    dialog = ManualAssignmentDialog(g, [g], {}, {'L': Classroom('L', 30, 'LAB')}, TimeModel.default())
    dialog.room.setCurrentIndex(1)
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: pytest.fail('No exception needed'))
    dialog._submit()
    assert dialog.result() == QDialog.DialogCode.Accepted and not dialog.lab_override
    dialog.close()
