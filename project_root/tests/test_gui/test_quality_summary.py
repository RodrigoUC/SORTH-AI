import copy
from PyQt6.QtWidgets import QApplication, QLabel, QScrollArea, QTableWidget, QDialogButtonBox
from src.gui.schedule_viewer_widget import ScheduleViewerWidget, SummaryDialog
from src.gui.i18n import language_manager
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.time_model import TimeModel


def populate(viewer):
    rooms = {'A': Classroom('A', 20, 'REGULAR'), 'B': Classroom('B', 20, 'LAB')}
    groups = Course('BIO', 2, 60, 'LAB', suggested_classroom='B', preferred_day='Lunes',
                    preferred_start_min=480).generate_groups()
    groups[0].lab_override = True
    assignments = {'BIO-G1': ('A', 1, 480, 540)}
    viewer.display_schedule(assignments, TimeModel.default(), groups, classrooms=rooms)
    return assignments, groups, rooms


def test_global_quality_ignores_every_filter_and_grid_selection():
    viewer = ScheduleViewerWidget()
    try:
        populate(viewer)
        original = copy.deepcopy(viewer.summary_data['quality'])
        viewer._list_search.setText('no match')
        viewer._room_filter.setCurrentIndex(1)
        viewer._day_filter.setCurrentIndex(2)
        viewer._status_filter.setCurrentIndex(2)
        viewer.classroom_selector.setCurrentIndex(0)
        viewer.tabs.setCurrentIndex(1)
        viewer._apply_filters()
        assert viewer.summary_data['quality'] == original
        assert original['scope'] == 'global'
        assert original['occupancy']['available_minutes'] == 2 * 6 * 840
    finally:
        viewer.close()


def test_removed_and_manually_replaced_assignment_recompute_global_quality():
    viewer = ScheduleViewerWidget()
    try:
        assignments, groups, rooms = populate(viewer)
        assert viewer.summary_data['quality']['manual_exceptions']['active_ids'] == ['BIO-G1']
        viewer._remove_group('BIO-G1')
        quality = viewer.summary_data['quality']
        assert quality['coverage']['pending_sessions'] == 2
        assert quality['preferences']['day']['ratio'] is None
        assert quality['occupancy']['occupied_minutes'] == 0
        assert quality['manual_exceptions']['active_ids'] == []
        # Manual reassignment is represented by the authoritative assignment map.
        assignments['BIO-G1'] = ('B', 2, 485, 545)
        groups[0].lab_override = False
        viewer.display_schedule(assignments, TimeModel.default(), groups, classrooms=rooms)
        quality = viewer.summary_data['quality']
        assert quality['preferences']['room']['ratio'] == 1
        assert quality['preferences']['day']['ratio'] == 0
        assert quality['preferences']['time']['ratio'] == 0
    finally:
        viewer.close()


def test_quality_summary_localizes_explanations_and_keeps_close_visible():
    viewer = ScheduleViewerWidget()
    manager = language_manager()
    previous = manager.language
    dialog = None
    try:
        manager.set_language('es', persist=False)
        populate(viewer)
        dialog = SummaryDialog(viewer, viewer.summary_data)
        dialog.show()
        QApplication.processEvents()
        assert dialog.findChild(QScrollArea).widgetResizable()
        assert all(table.verticalScrollBar().maximum() == 0
                   for table in dialog.findChildren(QTableWidget) if table.rowCount() <= 6)
        dialog.resize(640, 480)
        QApplication.processEvents()
        close = dialog.findChild(QDialogButtonBox)
        assert dialog.rect().contains(close.geometry())
        assert any('Calidad del horario completo' == label.text() for label in dialog.findChildren(QLabel))
        manager.set_language('en', persist=False)
        QApplication.processEvents()
        text = ' '.join(label.text() for label in dialog.findChildren(QLabel))
        assert 'Whole-schedule quality' in text
        assert 'Filters do not change these indicators.' in text
        assert 'Unconfirmed: None' in text
        dialog.reject()
        assert not dialog.isVisible()
    finally:
        manager.set_language(previous, persist=False)
        if dialog:
            dialog.close()
        viewer.close()
