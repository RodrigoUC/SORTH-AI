"""Viewer-originated edits select the course identity, not its unsorted index."""
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog
from src.gui.course_manager_widget import CourseDialog, CourseManagerWidget
from src.scheduling.course import Course


@pytest.fixture
def manager():
    widget = CourseManagerWidget()
    widget.courses = [Course(code, 1, 60, 'REGULAR') for code in ('Z', 'A', 'M')]
    widget._refresh_table()
    yield widget
    widget.close()


@pytest.mark.parametrize('order', [Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder])
@pytest.mark.parametrize('accept', [False, True])
def test_edit_by_code_selects_same_course_in_sorted_table(manager, monkeypatch, order, accept):
    manager.table.sortItems(0, order)
    def edit(dialog):
        assert dialog.course.code == 'A'
        assert manager.selected_course_codes() == ('A',)
        assert manager._selected_course_index() == 1
        dialog.name_edit.setText('Edited A')
        return QDialog.DialogCode.Accepted if accept else QDialog.DialogCode.Rejected
    monkeypatch.setattr(CourseDialog, 'exec', edit)
    manager.edit_course_by_code('A')
    assert manager.selected_course_codes() == ('A',)
    assert manager._selected_course_index() == 1
    assert manager.courses[1].name == ('Edited A' if accept else None)
    assert manager.courses[0].name is manager.courses[2].name is None


def test_edit_hidden_course_cannot_leave_unrelated_row_selected(manager, monkeypatch):
    manager.table.sortItems(0, Qt.SortOrder.DescendingOrder)
    manager._search.setText('M')
    manager.table.setCurrentCell(1, 0)
    assert manager.selected_course_codes() == ('M',)
    def cancel(dialog):
        assert dialog.course.code == 'A'
        assert manager.selected_course_codes() == ()
        assert manager._selected_course_index() == -1
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(CourseDialog, 'exec', cancel)
    manager.edit_course_by_code('A')
    assert manager._search.text() == 'M'
    assert manager._selected_course_index() == -1
