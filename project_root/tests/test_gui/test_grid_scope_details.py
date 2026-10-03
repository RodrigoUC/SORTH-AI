"""Actual native widgets: local grid scope, global export and detail handoff."""
import csv
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFileDialog
from src.gui.i18n import language_manager, msg
from src.gui.schedule_viewer_widget import ScheduleViewerWidget
from src.scheduling.classroom import Classroom
from src.scheduling.group import Group
from src.scheduling.time_model import TimeModel


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def viewer(app):
    language_manager().set_language('es', persist=False)
    widget = ScheduleViewerWidget()
    yield widget
    widget.close()
    language_manager().set_language('es', persist=False)


def populate_scope(viewer):
    assignments = {}
    for index in range(15):
        start = 480 + 60 * (index // 5)
        assignments[f'CUR{index + 1:02}-G1'] = (
            'Aula 201' if index < 13 else 'Aula 202', index % 5 + 1, start, start + 60)
    groups = [Group(gid, 60, 'REGULAR', course_code=gid.rsplit('-G', 1)[0],
                    course_name='Curso de investigación y conservación ' + gid)
              for gid in assignments]
    groups.append(Group('PEND-G1', 60, 'LAB', course_code='PEND', course_name='Pendiente'))
    tm = TimeModel(['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'], day_start=480, day_end=720)
    rooms = {name: Classroom(name, 40, 'REGULAR') for name in ('Aula 201', 'Aula 202')}
    viewer.display_schedule(assignments, tm, groups, classrooms=rooms)
    return assignments, groups, rooms


def assert_counts(viewer, assigned, pending, visible, total=16):
    expected = str(msg('Filtros globales · Asignadas exportables: {assigned} · Pendientes: {pending} · Sesiones: {visible}/{total}',
                       assigned=assigned, pending=pending, visible=visible, total=total))
    assert viewer._result_label.text().startswith(expected)
    assert len(viewer.filtered_assignments()) == assigned


@pytest.mark.parametrize('language', ['es', 'en'])
def test_local_count_global_count_and_filter_scope(viewer, language):
    original, _, _ = populate_scope(viewer)
    language_manager().set_language(language, persist=False)
    for tab in range(3):
        viewer.tabs.setCurrentIndex(tab)
        assert_counts(viewer, 15, 1, 16)
    viewer.tabs.setCurrentIndex(1)
    assert viewer._grid_count.text() == str(msg('Sesiones en esta aula: {count}', count=13))
    viewer.classroom_selector.setCurrentText('Aula 202')
    assert viewer._grid_count.text() == str(msg('Sesiones en esta aula: {count}', count=2))
    assert_counts(viewer, 15, 1, 16)
    assert viewer.filtered_assignments() == original
    viewer._room_filter.setCurrentIndex(viewer._room_filter.findData('Aula 202'))
    assert_counts(viewer, 2, 0, 2)
    assert not viewer.classroom_selector.isEnabled()
    viewer._day_filter.setCurrentIndex(viewer._day_filter.findData(4))
    assert_counts(viewer, 1, 0, 1)
    viewer._list_search.setText('NO_MATCH')
    assert_counts(viewer, 0, 0, 0)
    assert str(msg('. No hay coincidencias; cambie o restablezca los filtros.')) in viewer._result_label.text()
    viewer._reset_filters()
    viewer._status_filter.setCurrentIndex(viewer._status_filter.findData('unassigned'))
    assert_counts(viewer, 0, 1, 1)
    assert str(msg(' Consulte las sesiones sin asignar en Lista detallada.')) in viewer._result_label.text()
    assert viewer._assignments == original


@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('size', [(1200, 900), (960, 720), (960, 640)])
def test_scope_stays_visible_in_compact_real_window(app, tmp_path, language, size):
    from src.gui.main_window import MainWindow
    from src.infrastructure.session_repository import SessionRepository
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    viewer = window.schedule_viewer
    populate_scope(viewer)
    window.tabs.setCurrentIndex(1)
    viewer.tabs.setCurrentIndex(1)
    language_manager().set_language(language, persist=False)
    window.resize(*size)
    window.show()
    app.processEvents()
    assert (window.width(), window.height()) == size
    for label in (viewer._result_label, viewer._grid_count, viewer._export_scope_hint):
        assert label.isVisible()
        assert label.width() >= label.minimumSizeHint().width()
        assert label.height() >= label.heightForWidth(label.width())
    assert viewer.grid_table.viewport().height() >= 3 * viewer.grid_table.fontMetrics().height()
    assert_counts(viewer, 15, 1, 16)
    window.close()
    language_manager().set_language('es', persist=False)


@pytest.mark.parametrize('extension', ['csv', 'xlsx'])
def test_actual_export_rows_unaffected_by_local_room(app, tmp_path, monkeypatch, extension):
    from openpyxl import load_workbook
    from src.gui.main_window import MainWindow, _InfoDialog
    from src.infrastructure.session_repository import SessionRepository
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    viewer = window.schedule_viewer
    assignments, groups, rooms = populate_scope(viewer)
    window.current_schedule = assignments.copy()
    window.current_groups = groups
    window._classrooms = rooms
    viewer.tabs.setCurrentIndex(1)
    viewer.classroom_selector.setCurrentText('Aula 202')
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
    saved = tmp_path / f'filtered.{extension}'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(saved), ''))
    def exported_ids():
        window._export_schedule(filtered=True)
        if extension == 'csv':
            with saved.open(encoding='utf-8-sig', newline='') as handle:
                return {row['Grupo'] for row in csv.DictReader(handle)}
        book = load_workbook(saved)
        result = {row[2].value for row in list(book['Asignaciones'])[1:]}
        book.close()
        return result
    assert exported_ids() == set(assignments)
    viewer._room_filter.setCurrentIndex(viewer._room_filter.findData('Aula 202'))
    assert exported_ids() == {gid for gid, slot in assignments.items() if slot[0] == 'Aula 202'}
    assert window.current_schedule == assignments
    assert len(window.current_groups) == 16
    window.close()


def select_list_gid(table, gid):
    for row in range(table.rowCount()):
        if table.item(row, 0).data(Qt.ItemDataRole.UserRole) == gid:
            table.setCurrentCell(row, 0)
            return
    raise AssertionError(gid)


def select_grid_gids(viewer, gids):
    for row in range(viewer.grid_table.rowCount()):
        for col in range(1, viewer.grid_table.columnCount()):
            item = viewer.grid_table.item(row, col)
            if item and set(item.data(Qt.ItemDataRole.UserRole)) == set(gids):
                viewer.grid_table.setCurrentItem(item)
                viewer.grid_table.scrollToItem(item)
                return item
    raise AssertionError(gids)


def open_grid(viewer, app):
    viewer.tabs.setCurrentIndex(1)
    viewer.resize(960, 640)
    viewer.show()
    viewer.activateWindow()
    app.processEvents()


def test_enter_details_full_selectable_text_escape_focus_and_tab(viewer, app):
    from PyQt6.QtTest import QTest
    original, groups, _ = populate_scope(viewer)
    gid = 'CUR01-G1'
    long_name = 'Álgebra <avanzada> & conservación ' * 15
    viewer._name_map[gid] = long_name
    open_grid(viewer, app)
    item = select_grid_gids(viewer, [gid])
    viewer.grid_table.setFocus()
    QTest.keyClick(viewer.grid_table, Qt.Key.Key_Return)
    app.processEvents()
    dialog = viewer._grid_details_dialog
    assert dialog is not None and dialog.isVisible()
    text = dialog.details.toPlainText()
    for expected in (gid, long_name, 'Aula 201', 'Lunes', '08:00–09:00'):
        assert expected in text
    assert dialog.details.isReadOnly()
    assert dialog.details.hasFocus()
    QTest.keyClick(dialog.details, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    assert dialog.details.textCursor().selectedText().replace('\u2029', '\n') == text
    QTest.keyClick(dialog.details, Qt.Key.Key_Tab)
    assert not dialog.details.hasFocus()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    app.processEvents()
    assert viewer._grid_details_dialog is None
    assert viewer.grid_table.hasFocus()
    assert viewer.grid_table.currentItem() is item
    # Native Tab reaches the explicit action and leaves it again.
    QTest.keyClick(viewer.grid_table, Qt.Key.Key_Backtab)
    assert viewer._btn_grid_details.hasFocus()
    QTest.keyClick(viewer._btn_grid_details, Qt.Key.Key_Tab)
    assert viewer.grid_table.hasFocus()
    assert viewer._assignments == original
    assert len(groups) == 16


def test_exact_handoff_replaces_previous_list_target_preserving_sort_filters(viewer, app):
    from PyQt6.QtTest import QTest
    original, _, _ = populate_scope(viewer)
    viewer.list_table.sortItems(2, Qt.SortOrder.DescendingOrder)
    select_list_gid(viewer.list_table, 'CUR12-G1')
    viewer._list_search.setText('CUR')
    open_grid(viewer, app)
    select_grid_gids(viewer, ['CUR01-G1'])
    viewer._btn_grid_details.click()
    app.processEvents()
    dialog = viewer._grid_details_dialog
    assert dialog.view_in_list.isEnabled()
    dialog.view_in_list.click()
    app.processEvents()
    assert viewer._grid_details_dialog is None
    assert viewer.tabs.currentIndex() == 0
    assert viewer._selected_gid(viewer.list_table) == 'CUR01-G1'
    assert viewer.list_table.hasFocus()
    assert viewer._list_search.text() == 'CUR'
    assert viewer.list_table.horizontalHeader().sortIndicatorOrder() == Qt.SortOrder.DescendingOrder
    edits = []
    viewer.edit_course_requested.connect(edits.append)
    viewer._btn_edit_list.click()
    assert edits == ['CUR01']
    assert viewer._assignments == original


def test_conflict_lists_all_sessions_requires_explicit_choice(viewer, app):
    assignments = {'ONE-G1': ('Room', 1, 480, 550), 'TWO-G1': ('Room', 1, 510, 560),
                   'THREE-G1': ('Room', 1, 520, 555)}
    viewer.display_schedule(assignments, TimeModel.default(), course_name_by_code={
        'ONE': 'First course', 'TWO': 'Second course', 'THREE': 'Third course'})
    open_grid(viewer, app)
    select_grid_gids(viewer, assignments)
    viewer._show_grid_details()
    app.processEvents()
    dialog = viewer._grid_details_dialog
    assert dialog.session_selector.isVisible()
    assert dialog.session_selector.currentData() is None
    assert not dialog.view_in_list.isEnabled()
    assert {dialog.session_selector.itemData(i) for i in range(1, 4)} == set(assignments)
    for gid in assignments:
        assert gid in dialog.details.toPlainText()
    dialog._view_in_list()
    assert viewer.tabs.currentIndex() == 1
    dialog.session_selector.setCurrentIndex(dialog.session_selector.findData('TWO-G1'))
    assert dialog.view_in_list.isEnabled()
    assert '08:30–09:20' in dialog.details.toPlainText()
    dialog.view_in_list.click()
    app.processEvents()
    assert viewer._selected_gid(viewer.list_table) == 'TWO-G1'
    assert viewer._assignments == assignments


@pytest.mark.parametrize('change', ['remove', 'filter', 'clear', 'replace'])
def test_stale_details_close_and_never_activate_previous_row(viewer, app, change):
    original, groups, rooms = populate_scope(viewer)
    select_list_gid(viewer.list_table, 'CUR12-G1')
    open_grid(viewer, app)
    select_grid_gids(viewer, ['CUR01-G1'])
    viewer._show_grid_details()
    app.processEvents()
    dialog = viewer._grid_details_dialog
    if change == 'remove':
        viewer._remove_group('CUR01-G1')
    elif change == 'filter':
        viewer._list_search.setText('CUR12')
    elif change == 'clear':
        viewer._clear()
    else:
        viewer.display_schedule({'NEW-G1': ('Aula 201', 1, 480, 540)}, viewer._time_model)
    assert viewer._grid_details_dialog is None
    assert not dialog.isVisible()
    # Even a queued stale explicit request cannot keep an unrelated prior row.
    assert not viewer._show_grid_gid_in_list('CUR01-G1')
    assert viewer._selected_gid(viewer.list_table) is None
    assert not viewer._btn_edit_list.isEnabled()
    assert viewer.tabs.currentIndex() == 1
    if change == 'filter':
        assert viewer._assignments == original


def test_empty_and_removed_grid_selection_disable_details(viewer, app):
    from PyQt6.QtTest import QTest
    populate_scope(viewer)
    open_grid(viewer, app)
    select_grid_gids(viewer, ['CUR01-G1'])
    viewer._remove_group('CUR01-G1')
    assert viewer.grid_table.currentItem() is None
    assert not viewer._btn_grid_details.isEnabled()
    QTest.keyClick(viewer.grid_table, Qt.Key.Key_Return)
    assert viewer._grid_details_dialog is None
    viewer.grid_table.setCurrentCell(0, 0)
    assert not viewer._btn_grid_details.isEnabled()
    viewer._show_grid_details()
    assert viewer._grid_details_dialog is None
    # Empty cells, even when the table retains a native current index, are inert.
    viewer.grid_table.setCurrentCell(viewer.grid_table.rowCount() - 1, 1)
    assert not viewer._btn_grid_details.isEnabled()


def test_language_and_theme_keep_grid_and_dialog_identity(viewer, app):
    from src.gui.schedule_grid_delegate import GRID_BLOCK_ROLE
    from src.gui.theme import builtin_themes, theme_manager
    original, _, _ = populate_scope(viewer)
    open_grid(viewer, app)
    item = select_grid_gids(viewer, ['CUR01-G1'])
    identity = item.data(GRID_BLOCK_ROLE)
    color = item.background().color().name()
    viewer._show_grid_details()
    dialog = viewer._grid_details_dialog
    manager = theme_manager()
    initial_theme = manager.current
    for language, choice in zip(('en', 'es', 'en'), builtin_themes()):
        language_manager().set_language(language, persist=False)
        manager._apply(choice.spec)
        app.processEvents()
        assert viewer._grid_details_dialog is dialog
        assert dialog.session_selector.currentData() == 'CUR01-G1'
        assert viewer.grid_table.currentItem().data(GRID_BLOCK_ROLE) == identity
        assert viewer.grid_table.currentItem().background().color().name() == color
        assert ('Monday' if language == 'en' else 'Lunes') in dialog.details.toPlainText()
        assert ('Session:' if language == 'en' else 'Sesión:') in dialog.details.toPlainText()
    dialog.reject()
    manager._apply(initial_theme)
    assert viewer._assignments == original


def test_native_double_click_opens_details(viewer, app):
    from PyQt6.QtTest import QTest
    populate_scope(viewer)
    open_grid(viewer, app)
    item = select_grid_gids(viewer, ['CUR01-G1'])
    pos = viewer.grid_table.visualItemRect(item).center()
    QTest.mouseClick(viewer.grid_table.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    QTest.mouseDClick(viewer.grid_table.viewport(), Qt.MouseButton.LeftButton, pos=pos)
    app.processEvents()
    assert viewer._grid_details_dialog is not None
    assert viewer._grid_details_dialog.session_selector.currentData() == 'CUR01-G1'
    viewer._grid_details_dialog.reject()


@pytest.mark.parametrize('language', ['es', 'en'])
def test_long_room_and_empty_states_keep_compact_grid_geometry(app, tmp_path, language):
    from src.gui.main_window import MainWindow
    from src.infrastructure.session_repository import SessionRepository
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    viewer = window.schedule_viewer
    assignments, groups, rooms = populate_scope(viewer)
    long_room = 'Laboratorio de conservación e investigación de ecosistemas costeros ' * 4
    assignments = {gid: (long_room, *slot[1:]) for gid, slot in assignments.items()}
    viewer.display_schedule(assignments, viewer._time_model, groups)
    language_manager().set_language(language, persist=False)
    window.tabs.setCurrentIndex(1)
    viewer.tabs.setCurrentIndex(1)
    window.resize(960, 640)
    window.show()
    app.processEvents()
    assert window.width() == 960
    assert viewer.classroom_selector.toolTip() == long_room
    geometry = viewer.grid_table.geometry()
    viewer._status_filter.setCurrentIndex(viewer._status_filter.findData('unassigned'))
    app.processEvents()
    assert viewer.grid_table.geometry() == geometry
    viewer._list_search.setText('NO_MATCH')
    app.processEvents()
    assert viewer.grid_table.geometry() == geometry
    window.close()
    language_manager().set_language('es', persist=False)


def test_viewing_details_emits_no_domain_commands_and_respects_reduced_motion(app, tmp_path):
    from PyQt6.QtTest import QSignalSpy
    from src.gui.main_window import MainWindow
    from src.infrastructure.session_repository import SessionRepository
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False)
    viewer = window.schedule_viewer
    original, groups, _ = populate_scope(viewer)
    before_groups = [vars(group).copy() for group in groups]
    signals = [QSignalSpy(signal) for signal in (viewer.edit_course_requested,
        viewer.manual_assignment_requested, viewer.placement_options_requested,
        viewer.group_removed, viewer.pin_requested, viewer.schedule_cleared)]
    window.resize(960, 640)
    window.show()
    window.tabs.setCurrentIndex(1)
    viewer.tabs.setCurrentIndex(1)
    window.chk_reduce_motion.setChecked(True)
    select_grid_gids(viewer, ['CUR01-G1'])
    viewer._show_grid_details()
    app.processEvents()
    first = viewer._grid_details_dialog
    viewer._show_grid_details()
    assert viewer._grid_details_dialog is first
    window.chk_reduce_motion.setChecked(False)
    window.chk_reduce_motion.setChecked(True)
    assert first.graphicsEffect() is None
    first.view_in_list.click()
    app.processEvents()
    assert viewer.list_table.hasFocus()
    assert window._motion._effect is None
    assert viewer._assignments == original
    assert [vars(group) for group in groups] == before_groups
    assert all(not spy for spy in signals)
    window.close()
