"""Native session headers keep full captions and interactive section sizing."""
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QHeaderView, QStyleFactory
from PyQt6.QtTest import QTest

from src.gui.edit_view_state import TableViewState
from src.gui.i18n import language_manager
from src.gui.schedule_viewer_widget import ScheduleViewerWidget
from src.gui.smoke_rendering import settle_capture_layout
from src.gui.theme import STYLESHEET
from src.scheduling.group import Group
from src.scheduling.time_model import TimeModel


@pytest.mark.parametrize('style_name', [None, 'Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('points', [10, 20])
def test_session_header_fits_native_caption_preserving_user_resize(style_name, locale, points):
    app = QApplication.instance()
    old_style = app.style().objectName()
    manager = language_manager()
    old_locale = manager.language
    viewer = None
    try:
        if style_name:
            app.setStyle(QStyleFactory.create(style_name))
        manager.set_language(locale, persist=False)
        viewer = ScheduleViewerWidget()
        viewer.setStyleSheet(STYLESHEET + f'\nQHeaderView {{ font-size: {points}pt; }}')
        assignments = {'BIO-G10': ('A', 2, 480, 540), 'BIO-G2': ('A', 1, 540, 600)}
        groups = [Group(gid, 60, 'REGULAR', course_name='Synthetic course') for gid in assignments]
        # Capture the initial empty-table geometry just as atomic generation
        # does. Previously restoring its 100px defaults clipped session labels.
        initial = [TableViewState.capture(table) for table in
                   (viewer.list_table, viewer.classroom_table)]
        viewer.display_schedule(assignments, TimeModel.default(), groups)
        for state in initial:
            state.restore()
        viewer.show()
        for tab, table, column in ((0, viewer.list_table, 2), (2, viewer.classroom_table, 1)):
            viewer.tabs.setCurrentIndex(tab)
            header = table.horizontalHeader()
            for width in (1200, 960, 640, 960):
                viewer.resize(width, 640)
                settle_capture_layout(viewer)
                for order in (Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder):
                    table.sortItems(column, order)
                    required = header.sectionSizeHint(column)
                    assert header.sectionSize(column) >= required
                    assert header.sectionResizeMode(column) == QHeaderView.ResizeMode.Interactive
                    assert table.horizontalHeaderItem(column).text() == (
                        'Grupo / sesión' if manager.language == 'es' else 'Group / session')
                    ids = [table.item(row, 0).data(Qt.ItemDataRole.UserRole) for row in range(2)]
                    expected = ['BIO-G2', 'BIO-G10']
                    assert ids == (expected if order == Qt.SortOrder.AscendingOrder else expected[::-1])
                before_other = [header.sectionSize(index) for index in range(header.count())
                                if index != column and header.sectionResizeMode(index) == QHeaderView.ResizeMode.Interactive]
                table.setColumnWidth(column, required + 90)
                wide = header.sectionSize(column)
                assert wide == required + 90
                state = TableViewState.capture(table)
                viewer.display_schedule(assignments, TimeModel.default(), groups)
                state.restore()
                assert header.sectionSize(column) == wide
                manager.set_language('en' if manager.language == 'es' else 'es', persist=False)
                settle_capture_layout(viewer)
                assert header.sectionSize(column) == wide
                assert [header.sectionSize(index) for index in range(header.count())
                        if index != column and header.sectionResizeMode(index) == QHeaderView.ResizeMode.Interactive] == before_other
                # Dragging narrower still works down to the full-caption floor.
                table.setColumnWidth(column, 65)
                assert header.sectionSize(column) == header.sectionSizeHint(column)
                # A deliberately wide user size remains reachable by native
                # horizontal scrolling, not hidden or squeezed into the window.
                table.setColumnWidth(column, 1000)
                QTest.qWait(1)  # Native header scroll-range updates use a zero timer.
                settle_capture_layout(viewer)
                assert table.horizontalScrollBar().maximum() > 0
                table.horizontalScrollBar().setValue(table.horizontalScrollBar().maximum())
                assert table.horizontalScrollBar().value() > 0
                table.setColumnWidth(column, header.sectionSizeHint(column))
        # A live font change must recalculate the minimum in the native layout
        # queue, without requiring a language change or schedule regeneration.
        viewer.setStyleSheet(STYLESHEET + '\nQHeaderView { font-size: 24pt; }')
        settle_capture_layout(viewer)
        for table, column in ((viewer.list_table, 2), (viewer.classroom_table, 1)):
            header = table.horizontalHeader()
            assert header.sectionSize(column) >= header.sectionSizeHint(column)
        assert viewer._assignments == assignments
    finally:
        if viewer is not None:
            viewer.close()
            viewer.deleteLater()
        manager.set_language(old_locale, persist=False)
        app.setStyle(QStyleFactory.create(old_style))


@pytest.mark.parametrize('style_name', ['Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('points', [10, 20])
def test_session_header_native_paint_rect_contains_full_caption(style_name, locale, points):
    """Inspect the actual style-adjusted text rectangle, not only cached hints."""
    from PyQt6.QtWidgets import QProxyStyle

    class PaintSpy(QProxyStyle):
        def __init__(self):
            super().__init__(QStyleFactory.create(style_name))
            self.captions = []

        def drawItemText(self, painter, rect, flags, palette, enabled, text, role):
            if text in ('Grupo / sesión', 'Group / session'):
                self.captions.append((rect.width(), painter.fontMetrics().size(flags, text).width()))
            return super().drawItemText(painter, rect, flags, palette, enabled, text, role)

    app = QApplication.instance()
    old_style = app.style().objectName()
    manager = language_manager()
    old_locale = manager.language
    viewer = None
    spy = PaintSpy()
    app.setStyle(spy)
    try:
        manager.set_language(locale, persist=False)
        viewer = ScheduleViewerWidget()
        viewer.setStyleSheet(STYLESHEET + f'\nQHeaderView {{ font-size: {points}pt; }}')
        viewer.resize(960, 640)
        viewer.show()
        for tab, table, column in ((0, viewer.list_table, 2), (2, viewer.classroom_table, 1)):
            viewer.tabs.setCurrentIndex(tab)
            table.setColumnWidth(column, 100)  # The previously restored default.
            for order in (Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder):
                table.sortItems(column, order)
                QTest.qWait(1)
                settle_capture_layout(viewer)
                spy.captions.clear()
                assert not viewer.grab().isNull()
                assert spy.captions, 'Native style must actually paint the session header.'
                assert all(available >= required for available, required in spy.captions), spy.captions
    finally:
        if viewer is not None:
            viewer.close()
            viewer.deleteLater()
        manager.set_language(old_locale, persist=False)
        app.setStyle(QStyleFactory.create(old_style))
