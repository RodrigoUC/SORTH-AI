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
