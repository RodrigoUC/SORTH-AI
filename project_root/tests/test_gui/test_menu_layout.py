"""Popup labels retain explicit gutters across native styles and font metrics."""
import pytest
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.gui.i18n import language_manager
from src.gui.theme import builtin_themes, theme_manager
from tests.test_gui.test_background_import import window


@pytest.mark.parametrize('style_name', [None, 'Fusion', 'Windows'],
                         ids=['native-default', 'Fusion', 'Windows'])
@pytest.mark.parametrize('large_text', [False, True], ids=['normal', 'large-text'])
@pytest.mark.parametrize('optional_enabled', [False, True], ids=['basic', 'all-tools'])
def test_schedule_tools_menu_keeps_complete_labels_and_gutters(
        window, style_name, large_text, optional_enabled):
    app = QApplication.instance()
    locale = language_manager()
    appearance = theme_manager()
    previous = (app.style().objectName(), locale.language, appearance.current)
    menu = window._compact_tools_button.menu()
    try:
        if style_name is not None:
            app.setStyle(style_name)
        from src.scheduling.teaching_resources import (
            ResourceCatalog, SchedulingResources, RESOURCE_KINDS)
        window.resources = SchedulingResources(tuple(
            ResourceCatalog(kind, optional_enabled) for kind in RESOURCE_KINDS))
        window.resize(960, 640)
        window.tabs.setCurrentIndex(1)
        window.show()
        for choice in builtin_themes():
            appearance._apply(choice.spec)
            for language in ('es', 'en', 'es'):
                locale.set_language(language, persist=False)
                # Exercise real stylesheet font growth, not fabricated metrics.
                menu.setStyleSheet('QMenu { font-size: 14pt; }' if large_text else '')
                menu.popup(window._compact_tools_button.mapToGlobal(QPoint(0, 0)))
                app.processEvents()
                visible = [a for a in menu.actions()
                           if a.isVisible() and not a.isSeparator()]
                assert len(visible) >= 3
                for action in sorted(visible, key=lambda a: menu.fontMetrics().horizontalAdvance(a.text()), reverse=True):
                    rect = menu.actionGeometry(action)
                    # The shared menu item box owns 28px left/right padding.
                    # This catches the native-style width seen in the report,
                    # where the final ')' touched the popup's right edge.
                    assert rect.width() >= menu.fontMetrics().horizontalAdvance(action.text()) + 56
                    assert rect.height() >= menu.fontMetrics().height() + 12
                    assert menu.rect().contains(rect)
                menu.setActiveAction(visible[-1])
                app.processEvents()
                assert menu.activeAction() is visible[-1]
                QTest.keyClick(menu, Qt.Key.Key_Escape)
                app.processEvents()
                assert not menu.isVisible()
        # Popup styling must not consume the compact schedule's reading area.
        table = window.schedule_viewer.list_table
        assert table.viewport().height() >= 4 * table.rowHeight(0)
    finally:
        menu.close()
        menu.setStyleSheet('')
        app.setStyle(previous[0])
        locale.set_language(previous[1], persist=False)
        appearance._apply(previous[2])
