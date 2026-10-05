"""Single-course actions cannot target a row deselected by native Ctrl-click."""
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog

from src.gui import course_manager_widget as course_module
from src.gui.course_manager_widget import CourseDialog, CourseManagerWidget
from src.scheduling.course import Course


@pytest.fixture
def manager():
    widget = CourseManagerWidget()
    widget.courses = [Course(code, 1, 60, 'REGULAR') for code in ('Z', 'A', 'M')]
    widget._refresh_table()
    widget.table.setSelectionMode(widget.table.SelectionMode.ExtendedSelection)
    widget.resize(900, 500)
    widget.show()
    QApplication.processEvents()
    yield widget
    widget.close()


def click_course(manager, code, *, control=False):
    table = manager.table
    item = next(table.item(row, 0) for row in range(table.rowCount())
                if table.item(row, 0).data(Qt.ItemDataRole.UserRole) == code)
    QTest.mouseClick(table.viewport(), Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.ControlModifier if control else Qt.KeyboardModifier.NoModifier,
                     table.visualItemRect(item).center())
    QApplication.processEvents()


@pytest.mark.parametrize('order', [Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder])
@pytest.mark.parametrize('keep_other_selected', [False, True])
@pytest.mark.parametrize('action', ['_edit_course', '_delete_course'])
def test_deselected_current_course_cannot_be_edited_or_deleted(
        manager, monkeypatch, order, keep_other_selected, action):
    manager.table.sortItems(0, order)
    if keep_other_selected:
        click_course(manager, 'A')
    click_course(manager, 'M', control=keep_other_selected)
    click_course(manager, 'M', control=True)
    assert manager.table.currentItem().data(Qt.ItemDataRole.UserRole) == 'M'
    assert not manager.table.currentItem().isSelected()
    assert manager.selected_course_codes() == (('A',) if keep_other_selected else ())
    warnings, edits, confirmations = [], [], []
    monkeypatch.setattr(course_module.QMessageBox, 'warning', lambda *args: warnings.append(args))
    monkeypatch.setattr(CourseDialog, 'exec', lambda dialog: edits.append(dialog.course.code) or QDialog.DialogCode.Rejected)
    monkeypatch.setattr(course_module, '_confirm', lambda *args: confirmations.append(args) or True)
    getattr(manager, action)()
    assert edits == [] and confirmations == []
    assert len(warnings) == 1
    assert [course.code for course in manager.courses] == ['Z', 'A', 'M']
    assert manager.selected_course_codes() == (('A',) if keep_other_selected else ())


@pytest.mark.parametrize('order', [Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder])
def test_sorted_selected_delete_cancel_retry_keeps_exact_identity(manager, monkeypatch, order):
    manager.table.sortItems(0, order)
    click_course(manager, 'A')
    click_course(manager, 'M', control=True)
    confirmations = []
    answers = iter((False, True))
    def confirm(parent, title, message):
        confirmations.append(str(message))
        return next(answers)
    monkeypatch.setattr(course_module, '_confirm', confirm)
    manager._delete_course()
    assert [course.code for course in manager.courses] == ['Z', 'A', 'M']
    assert manager.selected_course_codes() == ('A', 'M')
    manager._delete_course()
    assert [course.code for course in manager.courses] == ['Z', 'A']
    assert confirmations == ['¿Eliminar el curso M?', '¿Eliminar el curso M?']
    assert manager.selected_course_codes() == ('A',)
