"""Identity-based presentation snapshots for atomic editor materialization.

No model data or persistence lives here. Restores use synchronous Qt APIs only;
no event loops, dialogs, timers, or callbacks that accept user decisions.
"""
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QItemSelectionModel, QSignalBlocker
from PyQt6.QtWidgets import QApplication, QHeaderView
from PyQt6 import sip

from .schedule_grid_delegate import GRID_BLOCK_ROLE


@dataclass
class TableViewState:
    table: object
    selected: tuple
    current: tuple | None
    vertical: int
    horizontal: int
    sort_column: int
    sort_order: object
    widths: tuple

    @classmethod
    def capture(cls, table):
        def identity(row):
            item = table.item(row, 0)
            return item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        selected = tuple((identity(index.row()), index.column()) for index in table.selectedIndexes())
        current = (identity(table.currentRow()), table.currentColumn()) if table.currentRow() >= 0 else None
        header = table.horizontalHeader()
        return cls(table, selected, current, table.verticalScrollBar().value(),
                   table.horizontalScrollBar().value(), header.sortIndicatorSection(), header.sortIndicatorOrder(),
                   tuple(table.columnWidth(column) for column in range(table.columnCount())))

    def restore(self):
        table = self.table
        if table.isSortingEnabled() and 0 <= self.sort_column < table.columnCount():
            table.sortItems(self.sort_column, self.sort_order)
        rows = {table.item(row, 0).data(Qt.ItemDataRole.UserRole): row
                for row in range(table.rowCount()) if table.item(row, 0) is not None and not table.isRowHidden(row)}
        selection = table.selectionModel()
        selection.clearSelection()
        table.setCurrentItem(None)
        for key, column in self.selected:
            if key in rows and 0 <= column < table.columnCount():
                selection.select(table.model().index(rows[key], column), QItemSelectionModel.SelectionFlag.Select)
        if self.current and self.current[0] in rows and 0 <= self.current[1] < table.columnCount():
            selection.setCurrentIndex(table.model().index(rows[self.current[0]], self.current[1]),
                                      QItemSelectionModel.SelectionFlag.NoUpdate)
        for column, width in enumerate(self.widths[:table.columnCount()]):
            if table.horizontalHeader().sectionResizeMode(column) == QHeaderView.ResizeMode.Interactive:
                table.setColumnWidth(column, width)
        # Identity and multi-selection are restored as one logical change. Action
        # callbacks must see the final current cell, not the intermediate empty one.
        table.itemSelectionChanged.emit()
        table.doItemsLayout()
        table.verticalScrollBar().setValue(self.vertical)
        table.horizontalScrollBar().setValue(self.horizontal)


@dataclass
class GridViewState:
    room: str
    block: tuple | None
    vertical: int
    horizontal: int

    @classmethod
    def capture(cls, viewer):
        table = viewer.grid_table
        item = table.currentItem()
        block = (item.data(GRID_BLOCK_ROLE)
                 if item is not None and viewer._selected_grid_gids() else None)
        return cls(viewer.classroom_selector.currentText(), block,
                   table.verticalScrollBar().value(), table.horizontalScrollBar().value())

    def restore(self, viewer):
        table = viewer.grid_table
        table.clearSelection()
        table.setCurrentItem(None)
        # Row boundaries change when off-grid sessions are removed; the old
        # coordinates can now belong to an unrelated session. Match the complete
        # block, including its room and conflict segment, or leave it unselected.
        if (self.block is not None and not viewer._grid_dirty
                and viewer.classroom_selector.currentText() == self.room):
            for row in range(table.rowCount()):
                if table.isRowHidden(row):
                    continue
                for column in range(1, table.columnCount()):
                    item = table.item(row, column)
                    if (not table.isColumnHidden(column) and item is not None
                            and item.data(GRID_BLOCK_ROLE) == self.block):
                        table.setCurrentItem(item)
                        break
                else:
                    continue
                break
        viewer._update_grid_action()
        table.doItemsLayout()
        table.verticalScrollBar().setValue(self.vertical)
        table.horizontalScrollBar().setValue(self.horizontal)


class EditViewState:
    @classmethod
    def capture(cls, window):
        state = cls()
        viewer = window.schedule_viewer
        state.tables = [TableViewState.capture(table) for table in (
            window.course_manager.table, viewer.list_table, viewer.classroom_table)]
        state.course_query = window.course_manager._search.text()
        state.schedule_query = viewer._list_search.text()
        state.filters = tuple(control.currentData() for control in (
            viewer._room_filter, viewer._day_filter, viewer._status_filter))
        state.room = viewer.classroom_selector.currentText()
        state.tabs = window.tabs.currentIndex(), viewer.tabs.currentIndex()
        state.grid = GridViewState.capture(viewer)
        state.focus = QApplication.focusWidget()
        state.status = window.status_bar.currentMessage()
        return state

    def restore(self, window):
        viewer = window.schedule_viewer
        controls = (viewer._list_search, viewer._room_filter, viewer._day_filter,
                    viewer._status_filter, viewer.classroom_selector)
        blockers = [QSignalBlocker(control) for control in controls]
        viewer._list_search.setText(self.schedule_query)
        for control, value in zip(controls[1:4], self.filters):
            index = control.findData(value)
            if control is viewer._room_filter and index < 0 and value in window._classrooms:
                control.addItem(value, value)
                index = control.findData(value)
            if index >= 0:
                control.setCurrentIndex(index)
        index = viewer.classroom_selector.findText(self.room)
        if index < 0 and self.room in window._classrooms:
            viewer.classroom_selector.addItem(self.room)
            index = viewer.classroom_selector.findText(self.room)
        if index >= 0:
            viewer.classroom_selector.setCurrentIndex(index)
        del blockers
        viewer._apply_filters()
        window.course_manager._search.setText(self.course_query)
        window.course_manager._filter_table(self.course_query)
        window.tabs.setCurrentIndex(self.tabs[0])
        viewer.tabs.setCurrentIndex(self.tabs[1])
        for table in self.tables:
            table.restore()
        self.grid.restore(viewer)
        if self.focus is not None and not sip.isdeleted(self.focus) and self.focus.isEnabled() and self.focus.isVisible():
            self.focus.setFocus(Qt.FocusReason.OtherFocusReason)
        window.status_bar.showMessage(self.status)
