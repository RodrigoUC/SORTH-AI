from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHeaderView, QAbstractItemView
import pytest

from src.gui.course_manager_widget import CourseManagerWidget
from src.scheduling.course import Course


def manager():
    widget = CourseManagerWidget()
    widget.courses = [Course(code, 1, 60, 'REGULAR', name='Long course name ' + code)
                      for code in ('Z', 'A', 'M')]
    widget._refresh_table()
    return widget


def test_refresh_batches_sizing_and_restores_mixed_modes(monkeypatch):
    widget = manager()
    header = widget.table.horizontalHeader()
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    before = [header.sectionResizeMode(i) for i in range(header.count())]
    original = widget._refresh_table_contents
    def populate():
        assert not widget.table.updatesEnabled()
        assert all(header.sectionResizeMode(i) == QHeaderView.ResizeMode.Fixed
                   for i in range(header.count()))
        original()
    monkeypatch.setattr(widget, '_refresh_table_contents', populate)
    widget._refresh_table()
    assert widget.table.updatesEnabled()
    assert [header.sectionResizeMode(i) for i in range(header.count())] == before
    widget.close()


def test_refresh_restores_modes_and_disabled_updates_after_failure(monkeypatch):
    widget = manager()
    header = widget.table.horizontalHeader()
    before = [header.sectionResizeMode(i) for i in range(header.count())]
    widget.table.setUpdatesEnabled(False)
    def fail():
        raise RuntimeError('render failure')
    monkeypatch.setattr(widget, '_refresh_table_contents', fail)
    with pytest.raises(RuntimeError, match='render failure'):
        widget._refresh_table()
    assert not widget.table.updatesEnabled()
    assert [header.sectionResizeMode(i) for i in range(header.count())] == before
    widget.close()


def test_refresh_keeps_sorted_filtered_selection_by_course_identity():
    widget = manager()
    widget.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    widget.table.sortItems(0, Qt.SortOrder.DescendingOrder)
    widget._search.setText('Long course')
    widget.table.selectRow(1)
    current = widget.table.item(widget.table.currentRow(), 0).data(Qt.ItemDataRole.UserRole)
    selected = widget.selected_course_codes()
    widget.courses[0].name = 'A changed long name'
    widget._refresh_table()
    assert widget.table.item(widget.table.currentRow(), 0).data(Qt.ItemDataRole.UserRole) == current
    assert widget.selected_course_codes() == selected
    assert [widget.table.item(row, 0).text() for row in range(3)] == ['Z', 'M', 'A']
    assert widget.table.isRowHidden(0)  # changed name no longer matches
    widget.close()
