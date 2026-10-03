"""Minimum-height layout with all advanced tool families visible."""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
import pytest
from src.gui.i18n import language_manager
from src.gui.settings_dialog import SettingsDialog
from src.scheduling.project_calendar import ProjectCalendar
from src.scheduling.teaching_resources import ResourceCatalog, SchedulingResources, RESOURCE_KINDS
from tests.test_gui.test_background_import import window


@pytest.mark.parametrize('language', ['es', 'en'])
def test_compact_schedule_retains_four_readable_rows_and_actions(window, language):
    manager = language_manager()
    previous = manager.language
    try:
        manager.set_language(language, persist=False)
        window.resources = SchedulingResources(tuple(ResourceCatalog(kind, True) for kind in RESOURCE_KINDS))
        window.calendar = ProjectCalendar(('Lunes', 'Domingo'), 0, 1440, ())
        window._features.save({key: True for key in window._features.values()})
        window._apply_feature_preferences()
        window.resize(960, 640)
        window.show()
        window.tabs.setCurrentIndex(1)
        QApplication.processEvents()
        table = window.schedule_viewer.list_table
        assert window.height() == 640
        assert table.viewport().height() >= 4 * table.rowHeight(0)
        assert window.overview_label.isHidden()
        assert not window._compact_tools.isHidden()
        assert ('Calendario personalizado' if language == 'es' else 'Custom calendar') in window._compact_summary.text()
        assert ('Parámetros activos: 3' if language == 'es' else 'Active parameters: 3') in window._compact_summary.text()
        assert ('1 asignada' if language == 'es' else '1 assigned') in window._compact_summary.text()
        menu = window._compact_tools_button.menu()
        observed = []
        def inspect_menu():
            observed.append(menu.isVisible())
            assert all(action.isVisible() for action in window._compact_resource_actions.values())
            menu.close()
        window.activateWindow()
        window._compact_tools_button.setFocus()
        QTimer.singleShot(0, inspect_menu)
        QTest.keyClick(window, Qt.Key.Key_F7)
        QApplication.processEvents()
        assert observed == [True]
        for button in window.schedule_viewer._suggestion_controls + window.schedule_viewer._pin_controls:
            assert not button.isHidden()
            assert button.height() >= 30
        window.tabs.setCurrentIndex(0)
        assert not window.overview_label.isHidden()
        settings = SettingsDialog(window)
        settings.show()
        QApplication.processEvents()
        assert settings.height() <= 640
        assert settings.buttons.geometry().bottom() < settings.height()
        settings.reject()
    finally:
        manager.set_language(previous, persist=False)
