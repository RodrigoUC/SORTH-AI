"""Qt metadata/keyboard regressions; not native screen-reader acceptance."""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QPlainTextEdit

from src.gui.i18n import language_manager, msg
from src.gui.i18n_widgets import QWidget, QPushButton, QTableWidget, QTableWidgetItem, QDialog
from src.gui.course_manager_widget import CourseManagerWidget, CourseDialog
from src.gui.dialogs import ClassroomRestrictionsDialog, AddClassroomDialog
from src.gui.manual_assignment_dialog import ManualAssignmentDialog
from src.gui.schedule_viewer_widget import ScheduleViewerWidget
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.group import Group
from src.scheduling.classroom import Classroom
from src.scheduling.time_model import TimeModel


def show(widget):
    widget.show()
    widget.activateWindow()
    QApplication.processEvents()


def test_tab_and_shift_tab_leave_table_and_arrows_explore():
    page = QWidget()
    layout = QVBoxLayout(page)
    before, after = QPushButton('Before'), QPushButton('After')
    table = QTableWidget(2, 2)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    for row in range(2):
        for col in range(2):
            table.setItem(row, col, QTableWidgetItem(f'{row}-{col}'))
    for widget in (before, table, after):
        layout.addWidget(widget)
    show(page)
    table.setFocus()
    table.setCurrentCell(0, 0)
    QTest.keyClick(table, Qt.Key.Key_Right)
    assert table.currentColumn() == 1
    QTest.keyClick(table, Qt.Key.Key_Tab)
    assert after.hasFocus()
    QTest.keyClick(after, Qt.Key.Key_Backtab)
    assert table.hasFocus()
    QTest.keyClick(table, Qt.Key.Key_Backtab)
    assert before.hasFocus()
    page.close()


def test_keyboard_sort_keeps_current_item_identity():
    table = QTableWidget(2, 1)
    table.setItem(0, 0, QTableWidgetItem('A'))
    table.setItem(1, 0, QTableWidgetItem('Z'))
    table.setSortingEnabled(True)
    table.sortItems(0, Qt.SortOrder.AscendingOrder)
    table.setCurrentCell(0, 0)
    selected = table.currentItem()
    QTest.keyClick(table, Qt.Key.Key_Down, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    assert table.item(0, 0).text() == 'Z'
    assert table.currentItem() is selected
    QTest.keyClick(table, Qt.Key.Key_Up, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
    assert table.item(0, 0).text() == 'A'
    table.close()


def test_form_names_and_checkable_lists_switch_language():
    manager = language_manager()
    original = manager.language
    course, room = CourseDialog(), AddClassroomDialog(None)
    restrictions = ClassroomRestrictionsDialog(None, {'A1': ['BIO']})
    try:
        for lang, hours, classrooms in [('es', 'Duración en horas', 'Aulas con restricciones'),
                                       ('en', 'Duration in hours', 'Restricted classrooms')]:
            manager.set_language(lang, persist=False)
            assert course.dur_hours.accessibleName() == hours
            assert course.code_edit.accessibleName()
            assert course.pref_time_edit.accessibleName()
            assert room.inp_capacity.accessibleName()
            assert restrictions.cls_list.accessibleName() == classrooms
            assert restrictions.course_list.accessibleName()
        show(restrictions)
        restrictions.cls_list.setFocus()
        state = restrictions.cls_list.item(0).checkState()
        QTest.keyClick(restrictions.cls_list, Qt.Key.Key_Space)
        assert restrictions.cls_list.item(0).checkState() != state
    finally:
        manager.set_language(original, persist=False)
        for widget in (course, room, restrictions):
            widget.close()


def test_escape_and_accept_restore_invoker_focus():
    page = QWidget()
    layout = QVBoxLayout(page)
    opener = QPushButton('Open')
    layout.addWidget(opener)
    show(page)
    for accept in (False, True):
        opener.setFocus()
        dialog = QDialog(page)
        QVBoxLayout(dialog).addWidget(QPushButton('Inside'))
        if accept:
            QTimer.singleShot(0, dialog.accept)
        else:
            QTimer.singleShot(0, lambda: QTest.keyClick(dialog, Qt.Key.Key_Escape))
        result = dialog.exec()
        QApplication.processEvents()
        assert result == (QDialog.DialogCode.Accepted if accept else QDialog.DialogCode.Rejected)
        # Some offscreen window managers do not reactivate the owner globally;
        # its remembered focus widget is the reliable Qt-level contract.
        assert page.focusWidget() is opener
    page.close()


def test_refresh_preserves_selected_course_and_hides_no_stale_action():
    widget = CourseManagerWidget()
    widget.courses = [Course('BIO', 1, 60, 'REGULAR'), Course('ZOO', 1, 60, 'REGULAR')]
    widget._refresh_table()
    widget.table.sortItems(0, Qt.SortOrder.AscendingOrder)
    widget.table.setCurrentCell(1, 0)
    widget.courses.insert(0, Course('AAA', 1, 60, 'REGULAR'))
    widget._refresh_table()
    assert widget.table.item(widget.table.currentRow(), 0).text() == 'ZOO'
    widget._search.setText('BIO')
    assert widget._selected_course_index() == -1
    widget.close()


def test_schedule_refresh_keeps_gid_and_reason_localizes():
    viewer = ScheduleViewerWidget()
    pending = Group('P-G1', 60, 'REGULAR', course_code='P')
    pending.unassigned_reason = 'Seleccione un aula.'
    groups = [Group('BIO-G1', 60, 'REGULAR', course_code='BIO'), pending]
    viewer.display_schedule({'BIO-G1': ('A1', 1, 480, 540)}, TimeModel.default(), groups)
    table = viewer.list_table
    row = next(row for row in range(table.rowCount()) if table.item(row, 0).data(Qt.ItemDataRole.UserRole) == 'P-G1')
    table.setCurrentCell(row, 0)
    viewer._display_list(viewer._assignments, viewer._time_model)
    assert viewer._selected_gid(table) == 'P-G1'
    item = table.currentItem()
    manager = language_manager()
    original = manager.language
    try:
        manager.set_language('en', persist=False)
        assert item.data(Qt.ItemDataRole.AccessibleDescriptionRole) == 'Select a classroom.'
    finally:
        manager.set_language(original, persist=False)
    viewer.close()


def test_manual_validation_focuses_problem_and_preserves_inputs():
    group = Group('BIO-G1', 60, 'REGULAR', course_code='BIO')
    dialog = ManualAssignmentDialog(group, [group], {}, {'A1': Classroom('A1', 30, 'REGULAR')}, TimeModel.default())
    show(dialog)
    dialog._submit()
    assert dialog.room.hasFocus()
    assert dialog.error.text()
    dialog.room.setCurrentIndex(1)
    # Invalid time, outside the configured day, yields readable error focus.
    from PyQt6.QtCore import QTime
    dialog.start.setTime(QTime(23, 0))
    dialog._submit()
    assert dialog.error.hasFocus()
    assert dialog.start.time() == QTime(23, 0)
    dialog.close()


def test_status_f6_exposes_generation_save_and_summary(tmp_path):
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    show(window)
    window.btn_load.setFocus()
    window.status_bar.showMessage(msg('⏳ Generando horario...'))
    window._save_error = 'Synthetic save failure'
    observed = []
    def inspect():
        dialog = QApplication.activeModalWidget()
        if dialog is None:
            observed.append('no dialog')
            return
        field = dialog.findChild(QPlainTextEdit)
        observed.append(field.toPlainText())
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
    QTimer.singleShot(30, inspect)
    QTest.keyClick(window, Qt.Key.Key_F6)
    assert observed and 'Synthetic save failure' in observed[0]
    assert window.status_bar.currentMessage() in observed[0]
    assert window.focusWidget() is window.btn_load
    window._save_error = None
    window.close()


def test_invalid_course_stays_open_and_returns_focus(monkeypatch):
    from src.gui.course_manager_widget import QMessageBox
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: None)
    dialog = CourseDialog()
    show(dialog)
    dialog.name_edit.setText('Synthetic course')
    dialog.name_edit.setFocus()
    dialog.accept()
    assert dialog.isVisible()
    assert dialog.code_edit.hasFocus()
    assert dialog.name_edit.text() == 'Synthetic course'
    dialog.close()
