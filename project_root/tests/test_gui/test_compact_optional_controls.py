"""Minimum-height layout with all advanced tool families visible."""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtTest import QTest
import pytest
from src.gui.i18n import language_manager
from src.gui.settings_dialog import SettingsDialog
from src.scheduling.project_calendar import ProjectCalendar
from src.scheduling.teaching_resources import ResourceCatalog, SchedulingResources, RESOURCE_KINDS
from tests.test_gui.test_background_import import window


@pytest.mark.parametrize('style_name', [None, 'Fusion', 'Windows'], ids=['native-default', 'Fusion', 'Windows'])
@pytest.mark.parametrize('language', ['es', 'en'])
def test_compact_schedule_retains_four_readable_rows_and_actions(window, language, style_name):
    manager = language_manager()
    previous = manager.language
    app = QApplication.instance()
    previous_style = app.style().objectName()
    if style_name is not None:
        app.setStyle(style_name)
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
        assert window.size() == QSize(960, 640)
        assert table.viewport().height() >= 4 * table.rowHeight(0)
        assert window.overview_label.isHidden()
        assert all(hint.isHidden() for hint in window.schedule_viewer._selection_hints)
        assert table.accessibleDescription()
        assert window.schedule_viewer.accessibleDescription()
        assert window.schedule_viewer.toolTip()
        assert window.tabs.tabBar().height() >= 30
        assert window.schedule_viewer.tabs.tabBar().height() >= 30
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
        window.resize(1200, 800)
        QApplication.processEvents()
        assert not window.schedule_viewer._export_scope_hint.isHidden()
        assert all(not hint.isHidden() for hint in window.schedule_viewer._selection_hints)
        window.resize(960, 640)
        QApplication.processEvents()
        assert table.viewport().height() >= 4 * table.rowHeight(0)
        window.tabs.setCurrentIndex(0)
        assert not window.overview_label.isHidden()
        settings = SettingsDialog(window)
        settings.show()
        QApplication.processEvents()
        assert settings.height() <= 640
        assert settings.buttons.geometry().bottom() < settings.height()
        settings.reject()
    finally:
        app.setStyle(previous_style)
        manager.set_language(previous, persist=False)


@pytest.mark.parametrize('style_name', [None, 'Fusion', 'Windows'], ids=['native-default', 'Fusion', 'Windows'])
@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('optional_enabled', [False, True], ids=['saved-off', 'saved-all-on'])
def test_reopened_schedule_layout_budget_across_themes(window, language, style_name, optional_enabled):
    """Persisted controls and real themes must share the short-window budget."""
    import json
    from pathlib import Path
    from src.gui.main_window import MainWindow
    from src.gui.theme import builtin_themes, theme_manager

    app = QApplication.instance()
    locale = language_manager()
    previous_language = locale.language
    previous_style = app.style().objectName()
    appearance = theme_manager()
    previous_theme = appearance.current
    reopened = None
    snapshots = []
    report_dir = Path(__file__).resolve().parents[2] / 'build' / 'reports'
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f'schedule-budget-{style_name}-{language}-{optional_enabled}.json'
    try:
        if style_name is not None:
            app.setStyle(style_name)
        locale.set_language(language, persist=False)
        window.resources = SchedulingResources(tuple(
            ResourceCatalog(kind, optional_enabled) for kind in RESOURCE_KINDS))
        window.calendar = ProjectCalendar(('Lunes', 'Domingo'), 0, 1440, ())
        window._features.save({key: optional_enabled for key in window._features.values()})
        assert window._save_session()
        window.close()
        reopened = MainWindow(window._repo, restore_session=False,
                              feature_settings=window._features.settings)
        reopened._restore_session_if_exists(confirm=False)
        assert not reopened._restore_failed
        assert all(value is optional_enabled for value in reopened._features.values().values())
        viewer = reopened.schedule_viewer
        original = dict(viewer._assignments)
        original_font = viewer.list_table.font().pointSizeF()
        # Four complete list rows define the shared 120px reading-area floor.
        # Time-grid sections retain their duration/content-dependent heights.
        original_row_height = viewer.list_table.rowHeight(0)
        reopened.tabs.setCurrentIndex(1)
        reopened.show()
        reopened.activateWindow()
        for choice in builtin_themes():
            appearance._apply(choice.spec)
            for width, height in ((960, 640), (960, 720), (960, 759), (960, 760),
                                  (960, 761), (960, 780), (960, 799), (960, 800),
                                  (960, 801), (960, 802), (960, 803), (960, 804),
                                  (1200, 800), (960, 919), (960, 920),
                                  (960, 921), (960, 922), (960, 640)):
                reopened.resize(width, height)
                app.processEvents()
                for index, table in ((0, viewer.list_table), (1, viewer.grid_table),
                                     (2, viewer.classroom_table)):
                    viewer.tabs.setCurrentIndex(index)
                    table.setCurrentCell(0, 0)
                    table.setFocus()
                    app.processEvents()
                    assert table.hasFocus()
                    snapshot = {
                        'theme': choice.key, 'size': [reopened.width(), reopened.height()],
                        'tab': index, 'viewport_height': table.viewport().height(),
                        'reference_list_row_height': original_row_height,
                        'actual_row_heights': [table.rowHeight(row) for row in range(table.rowCount())],
                        'actual_section_sizes': [table.verticalHeader().sectionSize(row)
                                                 for row in range(table.rowCount())],
                        'default_section_size': table.verticalHeader().defaultSectionSize(),
                        'font': table.font().pointSizeF(),
                        'scope_visible': viewer._export_scope_hint.isVisible(),
                        'compact_tools': reopened._compact_tools.isVisible(),
                        'table_focused': table.hasFocus(),
                        'font_line_height': table.fontMetrics().height(),
                        'header_height': table.horizontalHeader().height(),
                        'main_spacing': reopened._main_layout.spacing(),
                        'main_vertical_margins': (
                            reopened._main_layout.contentsMargins().top()
                            + reopened._main_layout.contentsMargins().bottom()),
                        'page_top_margin': viewer.tabs.widget(index).layout().contentsMargins().top(),
                    }
                    snapshots.append(snapshot)
                    report.write_text(json.dumps(snapshots, indent=2), encoding='utf-8')
                    assert reopened.size() == QSize(width, height)
                    assert table.font().pointSizeF() == original_font
                    assert viewer.list_table.rowHeight(0) == original_row_height
                    assert viewer._export_scope_hint.isVisible()
                    assert viewer._result_label.isVisible()
                    assert viewer._export_scope_hint.height() >= viewer._export_scope_hint.heightForWidth(viewer._export_scope_hint.width())
                    assert viewer._result_label.height() >= viewer._result_label.heightForWidth(viewer._result_label.width())
                    assert table.viewport().height() >= 4 * original_row_height
                    assert reopened._compact_tools.isVisible() is (height <= 802)
                    assert all(hint.isHidden() is (height <= 760) for hint in viewer._selection_hints)
                    assert reopened._feature_notice.isVisible() is (height > 760)
                    if index == 1:
                        assert viewer._grid_count.isVisible()
                        assert viewer._btn_grid_details.isVisible()
                        assert viewer._btn_grid_details.height() >= 30
                    else:
                        controls = (viewer._pin_controls[index // 2], viewer._suggestion_controls[index // 2])
                        assert all(control.isVisible() is optional_enabled for control in controls)
                        if optional_enabled:
                            assert all(control.height() >= 30 for control in controls)
                    assert viewer._assignments == original
    finally:
        if reopened is not None:
            reopened.close()
        appearance._apply(previous_theme)
        app.setStyle(previous_style)
        locale.set_language(previous_language, persist=False)


@pytest.mark.parametrize('style_name', [None, 'Fusion', 'Windows'], ids=['native-default', 'Fusion', 'Windows'])
@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('header_allowance', [4, 8])
def test_schedule_budget_reserves_native_header_metric_variation(window, language, style_name, header_allowance):
    """A native header change must retain the four-list-row reference budget.

    Native Segoe UI exposed a height deficit that Linux font metrics concealed.
    Keep real widget fonts and rows, and give every header a four- or eight-pixel larger
    native size requirement so tight platform-specific seams fail locally too.
    """
    import json
    from pathlib import Path

    snapshots = []
    report_dir = Path(__file__).resolve().parents[2] / 'build' / 'reports'
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f'schedule-budget-header-{style_name}-{language}-{header_allowance}.json'
    app = QApplication.instance()
    locale = language_manager()
    previous_language = locale.language
    previous_style = app.style().objectName()
    try:
        if style_name is not None:
            app.setStyle(style_name)
        locale.set_language(language, persist=False)
        window.resources = SchedulingResources(tuple(ResourceCatalog(kind, True) for kind in RESOURCE_KINDS))
        window.calendar = ProjectCalendar(('Lunes', 'Domingo'), 0, 1440, ())
        window._features.save({key: True for key in window._features.values()})
        window._apply_feature_preferences()
        viewer = window.schedule_viewer
        tables = (viewer.list_table, viewer.grid_table, viewer.classroom_table)
        window.resize(960, 640)
        window.tabs.setCurrentIndex(1)
        window.show()
        window.activateWindow()
        app.processEvents()
        # The grid renders lazily, so materialize each native table before
        # recording its normal font, rows and header metrics.
        for index in range(len(tables)):
            viewer.tabs.setCurrentIndex(index)
            app.processEvents()
        fonts = [table.font().toString() for table in tables]
        rows = [table.rowHeight(0) for table in tables]
        for table in tables:
            header = table.horizontalHeader()
            header.setMinimumHeight(header.sizeHint().height() + header_allowance)
        heights = (640, 760, 761, 802, 803, 804, 920, 921, 922,
                   921, 920, 804, 803, 802, 761, 760, 640)
        for height in heights:
            window.resize(960, height)
            app.processEvents()
            for index, table in enumerate(tables):
                viewer.tabs.setCurrentIndex(index)
                table.setCurrentCell(0, 0)
                table.setFocus()
                app.processEvents()
                assert window.size() == QSize(960, height)
                margins = window._main_layout.contentsMargins()
                snapshots.append({
                    'size': [window.width(), window.height()], 'tab': index,
                    'viewport_height': table.viewport().height(),
                    'reference_list_row_height': rows[0],
                    'row_height': table.rowHeight(0), 'font': table.font().toString(),
                    'font_line_height': table.fontMetrics().height(),
                    'header_allowance': header_allowance,
                    'header_height': table.horizontalHeader().height(),
                    'main_spacing': window._main_layout.spacing(),
                    'main_margins': [margins.left(), margins.top(), margins.right(), margins.bottom()],
                    'scope_visible': viewer._export_scope_hint.isVisible(),
                    'table_focused': table.hasFocus(),
                })
                report.write_text(json.dumps(snapshots, indent=2), encoding='utf-8')
                expected_margins = (16, 2, 16, 2) if height <= 920 else (24, 8, 24, 8)
                assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == expected_margins
                assert window._main_layout.spacing() == (1 if height <= 920 else 8)
                assert table.hasFocus()
                assert table.font().toString() == fonts[index]
                assert table.rowHeight(0) == rows[index]
                assert table.viewport().height() >= 4 * rows[0], (style_name, language, height, index)
                assert viewer._export_scope_hint.isVisible()
                assert viewer._export_scope_hint.height() >= viewer._export_scope_hint.heightForWidth(viewer._export_scope_hint.width())
                assert all(control.height() >= 30 for control in viewer._pin_controls + viewer._suggestion_controls)
    finally:
        app.setStyle(previous_style)
        locale.set_language(previous_language, persist=False)
