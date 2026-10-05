"""Reversible schedule focus and geometry-only classroom zoom in real Qt."""
from copy import deepcopy
from pathlib import Path

import pytest
from PyQt6.QtCore import QSettings, QSize, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.gui.i18n import language_manager, msg
from src.gui.main_window import MainWindow
from src.gui.schedule_grid_delegate import GRID_BLOCK_ROLE
from src.gui.smoke_rendering import _action_geometry, settle_capture_layout
from src.gui.theme import builtin_themes, theme_manager
from src.infrastructure.session_repository import SessionRepository
from tests.test_gui.test_grid_scope_details import populate_scope


@pytest.fixture
def window(tmp_path):
    result = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False,
                        feature_settings=QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat))
    populate_scope(result.schedule_viewer)
    result.tabs.setCurrentIndex(1)
    result.resize(960, 640)
    result.show()
    result.activateWindow()
    settle(result)
    yield result
    result.close()


def settle(window):
    QApplication.processEvents()
    settle_capture_layout(window)


def select_block(viewer):
    table = viewer.grid_table
    item = next(table.item(row, col) for row in range(table.rowCount())
                for col in range(1, table.columnCount())
                if table.item(row, col) and table.item(row, col).data(GRID_BLOCK_ROLE))
    table.setCurrentItem(item)
    return item


@pytest.mark.parametrize('index', [0, 1, 2])
def test_expand_restore_retains_views_filters_selection_and_data(window, index):
    viewer = window.schedule_viewer
    viewer.tabs.setCurrentIndex(index)
    viewer._list_search.setText('CUR')
    viewer._room_filter.setCurrentIndex(viewer._room_filter.findData('Aula 201'))
    table = (viewer.list_table, viewer.grid_table, viewer.classroom_table)[index]
    item = select_block(viewer) if index == 1 else table.item(0, 0)
    table.setCurrentItem(item)
    assignments = deepcopy(viewer._assignments)
    exports = viewer.filtered_assignments()
    settle(window)
    initial_height = table.viewport().height()
    for _ in range(3):
        viewer._btn_expand.click()
        settle(window)
        assert viewer._expanded and viewer._btn_expand.isChecked()
        assert viewer._btn_expand.text() == str(msg('Restaurar'))
        assert not window._workspace_chrome.isVisible()
        assert not window._workspace_actions.isVisible()
        assert not window.tabs.tabBar().isVisible()
        assert window.status_bar.isVisible()
        assert table.viewport().height() > initial_height + 100
        assert table.currentItem() is item and item.isSelected()
        viewer._btn_expand.click()
        settle(window)
        assert not viewer._expanded and not viewer._btn_expand.isChecked()
        assert window._workspace_chrome.isVisible() and window._workspace_actions.isVisible()
        assert window.tabs.tabBar().isVisible()
        assert viewer._btn_expand.hasFocus()
        assert table.viewport().height() == initial_height
        assert viewer.tabs.currentIndex() == index
        assert viewer._list_search.text() == 'CUR'
        assert viewer._room_filter.currentData() == 'Aula 201'
        assert viewer.filtered_assignments() == exports
        assert viewer._assignments == assignments


def test_keyboard_escape_resize_navigation_and_child_visibility(window):
    viewer = window.schedule_viewer
    viewer._btn_expand.setFocus()
    QTest.keyClick(viewer._btn_expand, Qt.Key.Key_Space)
    settle(window)
    assert viewer._expanded
    window.resize(1200, 950)
    window._update_compact_overview()
    window._refresh_theme_recovery_notice()
    settle(window)
    assert not window._workspace_chrome.isVisible()
    viewer.list_table.setFocus()
    QTest.keyClick(viewer.list_table, Qt.Key.Key_Escape)
    settle(window)
    assert not viewer._expanded and viewer._btn_expand.hasFocus()
    assert window._workspace_chrome.isVisible()
    assert window.overview_label.isVisible()
    viewer.set_expanded(True)
    window.tabs.setCurrentIndex(0)
    settle(window)
    assert not viewer._expanded and window.course_manager.isVisible()
    assert window.course_manager.isAncestorOf(QApplication.focusWidget())
    assert window.tabs.tabBar().isVisible()
    window.tabs.setCurrentIndex(1)
    assert not viewer._expanded


def test_zoom_bounds_reset_identity_filters_and_render_refresh(window):
    viewer = window.schedule_viewer
    viewer.tabs.setCurrentIndex(1)
    settle(window)
    item = select_block(viewer)
    identity = item.data(GRID_BLOCK_ROLE)
    base_height = viewer.grid_table.rowHeight(item.row())
    base_font = item.font().pointSizeF()
    assignments = deepcopy(viewer._assignments)
    viewer._btn_zoom_in.setFocus()
    QTest.keyClick(viewer._btn_zoom_in, Qt.Key.Key_Space)
    settle(window)
    assert viewer._grid_zoom == 125
    assert "125%" in viewer._btn_zoom_reset.accessibleName()
    assert viewer.grid_table.currentItem() is item and item.isSelected()
    assert item.font().pointSizeF() == pytest.approx(base_font * 1.25)
    assert viewer.grid_table.rowHeight(item.row()) == round(base_height * 1.25)
    viewer.set_grid_zoom(999)
    settle(window)
    assert viewer._grid_zoom == 200 and not viewer._btn_zoom_in.isEnabled()
    assert viewer.grid_table.horizontalScrollBar().maximum() > 0
    assert viewer.grid_table.currentItem() is item
    viewer._request_grid_render()
    assert viewer.grid_table.currentItem().data(GRID_BLOCK_ROLE) == identity
    assert viewer.grid_table.currentItem().font().pointSizeF() == pytest.approx(base_font * 2)
    viewer.tabs.setCurrentIndex(0)
    viewer.tabs.setCurrentIndex(1)
    assert viewer._grid_zoom == 200
    viewer.set_expanded(True)
    viewer.set_expanded(False)
    assert viewer._grid_zoom == 200
    viewer.set_grid_zoom(-999)
    assert viewer._grid_zoom == 75 and not viewer._btn_zoom_out.isEnabled()
    viewer._btn_zoom_reset.click()
    assert viewer._grid_zoom == 100
    assert viewer._btn_zoom_out.isEnabled() and viewer._btn_zoom_in.isEnabled()
    assert viewer.grid_table.rowHeight(viewer.grid_table.currentItem().row()) == base_height
    assert viewer._assignments == assignments
    assert viewer.filtered_assignments() == assignments


@pytest.mark.parametrize('style', ['Fusion', 'Windows'])
@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('theme', ['original', 'nocturno', 'high_contrast'])
def test_small_window_reading_budget_and_visible_native_controls(window, style, language, theme):
    app = QApplication.instance()
    locale, appearance = language_manager(), theme_manager()
    old = (app.style().objectName(), locale.language, appearance.current)
    try:
        app.setStyle(style)
        locale.set_language(language, persist=False)
        appearance._apply(next(choice.spec for choice in builtin_themes() if choice.key == theme))
        viewer = window.schedule_viewer
        for index, table in enumerate((viewer.list_table, viewer.grid_table, viewer.classroom_table)):
            viewer.tabs.setCurrentIndex(index)
            settle(window)
            assert window.size() == QSize(960, 640)
            assert table.viewport().height() >= 120
            controls = [viewer._btn_expand]
            if index == 1:
                controls += [viewer._btn_zoom_out, viewer._btn_zoom_in, viewer._btn_zoom_reset]
            for control in controls:
                control.setFocus()
                settle(window)
                assert control.visibleRegion().boundingRect().contains(control.rect())
            captions = {button.text() for button in controls}
            assert all(row['fits'] for row in _action_geometry(window) if row['text'] in captions)
            viewer.set_expanded(True)
            settle(window)
            assert table.viewport().height() >= 300
            viewer.set_expanded(False)
        viewer.tabs.setCurrentIndex(1)
        viewer.set_grid_zoom(200)
        locale.set_language('en' if language == 'es' else 'es', persist=False)
        settle(window)
        assert viewer._grid_zoom == 200
        assert select_block(viewer).font().pointSizeF() == pytest.approx(viewer.grid_table.font().pointSizeF() * 2)
        viewer.set_expanded(True)
        settle(window)
        # Synthetic native captures travel with the existing CI checks artifact.
        reports = Path(__file__).resolve().parents[2] / 'build' / 'reports'
        reports.mkdir(parents=True, exist_ok=True)
        assert window.grab().save(str(reports / f'schedule-focus-zoom-{style}-{locale.language}-{theme}.png'))
    finally:
        app.setStyle(old[0])
        locale.set_language(old[1], persist=False)
        appearance._apply(old[2])


def test_details_escape_keeps_expansion_and_empty_zoom_is_safe(window):
    viewer = window.schedule_viewer
    viewer.tabs.setCurrentIndex(1)
    viewer.set_expanded(True)
    select_block(viewer)
    viewer._show_grid_details()
    settle(window)
    dialog = viewer._grid_details_dialog
    assert dialog is not None and dialog.isVisible()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    settle(window)
    assert viewer._grid_details_dialog is None
    assert viewer._expanded and not window._workspace_chrome.isVisible()
    viewer._clear()
    viewer.set_grid_zoom(200)
    assert viewer.grid_table.rowCount() == 0
    assert viewer.grid_table.columnCount() == 0
    assert viewer._grid_base_rows == []
    assert not viewer._btn_grid_details.isEnabled()
    populate_scope(viewer)
    assert viewer._grid_zoom == 200
    assert select_block(viewer).font().pointSizeF() == pytest.approx(viewer.grid_table.font().pointSizeF() * 2)
