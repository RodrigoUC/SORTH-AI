"""Real Qt paint and identity regressions, independent of the platform's font."""
import pytest
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem

from src.gui.i18n import language_manager
from src.gui.schedule_grid_delegate import COURSE_CARD_ROLE, GRID_BLOCK_ROLE, CourseCard
from src.gui.schedule_viewer_widget import ScheduleViewerWidget
from src.gui.theme import COLORS, apply_theme
from src.scheduling.course_style import course_style
from src.scheduling.group import Group
from src.scheduling.time_model import TimeModel


@pytest.fixture
def viewer():
    app = QApplication.instance() or QApplication([])
    widget = ScheduleViewerWidget()
    apply_theme(widget)
    widget.resize(960, 640)
    yield widget
    widget.close()


def populate(viewer):
    assignments = {
        'QUI-G1': ('A1', 1, 480, 510),
        'GEN-G1': ('A1', 1, 510, 520),
        'BIO-G1': ('A1', 2, 480, 540),
        'QUI-G2': ('A2', 1, 480, 540),
    }
    groups = [Group(gid, end-start, 'REGULAR', course_code=gid.rsplit('-G', 1)[0],
                    course_name='Curso sintético con nombre largo y 🧬 datos literales <BIO>')
              for gid, (_, _, start, end) in assignments.items()]
    groups[2].pinned = True
    viewer.display_schedule(assignments, TimeModel.default(), groups)
    viewer.tabs.setCurrentIndex(1)
    return assignments, groups


def item_for(viewer, gid):
    return next(viewer.grid_table.item(row, column)
                for row in range(viewer.grid_table.rowCount())
                for column in range(1, viewer.grid_table.columnCount())
                if viewer.grid_table.item(row, column)
                and gid in viewer.grid_table.item(row, column).data(Qt.ItemDataRole.UserRole))


def paint_card(viewer, item, selected=False):
    image = QImage(200, 120, QImage.Format.Format_ARGB32)
    image.fill(QColor('magenta'))
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 200, 120)
    option.font = viewer.grid_table.font()
    if selected:
        option.state |= QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus
    painter = QPainter(image)
    viewer.grid_table.itemDelegate().paint(painter, option, viewer.grid_table.indexFromItem(item))
    painter.end()
    return image


def test_grid_retains_full_text_exact_times_and_course_markers(viewer):
    assignments, _ = populate(viewer)
    first, second = item_for(viewer, 'QUI-G1'), item_for(viewer, 'GEN-G1')
    assert first.row() + viewer.grid_table.rowSpan(first.row(), first.column()) == second.row()
    assert first.data(COURSE_CARD_ROLE).style == course_style('QUI')
    assert second.data(COURSE_CARD_ROLE).style == course_style('GEN')
    assert first.data(COURSE_CARD_ROLE).style.marker != second.data(COURSE_CARD_ROLE).style.marker
    assert '08:30–08:40' in second.text()
    assert '<BIO>' in second.text()
    assert second.toolTip() == second.text() == second.data(Qt.ItemDataRole.AccessibleTextRole)
    assert 'Fijada' in item_for(viewer, 'BIO-G1').text()
    assert viewer._assignments == assignments


def test_style_survives_room_filter_sort_reloading_and_language(viewer):
    assignments, groups = populate(viewer)
    expected = item_for(viewer, 'QUI-G1').data(COURSE_CARD_ROLE).style
    viewer.classroom_selector.setCurrentText('A2')
    assert item_for(viewer, 'QUI-G2').data(COURSE_CARD_ROLE).style == expected
    viewer._list_search.setText('QUI')
    viewer.list_table.sortItems(0, Qt.SortOrder.DescendingOrder)
    assert item_for(viewer, 'QUI-G2').data(COURSE_CARD_ROLE).style == expected
    manager = language_manager()
    original = manager.language
    try:
        manager.set_language('en', persist=False)
        assert item_for(viewer, 'QUI-G2').data(COURSE_CARD_ROLE).style == expected
        viewer.display_schedule(dict(reversed(list(assignments.items()))), TimeModel.default(), groups)
        assert item_for(viewer, 'QUI-G1').data(COURSE_CARD_ROLE).style == expected
    finally:
        manager.set_language(original, persist=False)


def test_real_paint_has_white_gutters_and_selection_preserves_fill(viewer):
    populate(viewer)
    item = item_for(viewer, 'QUI-G1')
    plain, selected = paint_card(viewer, item), paint_card(viewer, item, selected=True)
    for image in (plain, selected):
        assert image.pixelColor(1, 60).name() == COLORS['surface'].lower()
        assert image.pixelColor(198, 60).name() == COLORS['surface'].lower()
        assert image.pixelColor(160, 105).name() == '#' + course_style('QUI').fill.lower()
    assert selected.pixelColor(100, 3).name() == COLORS['focus'].lower()
    assert plain.pixelColor(7, 65).name() == '#' + course_style('QUI').accent.lower()


def test_conflict_keeps_reserved_treatment_and_all_session_ids(viewer):
    viewer.display_schedule({'BIO-G1': ('A1', 1, 480, 500),
                             'QUI-G1': ('A1', 1, 490, 510)}, TimeModel.default())
    viewer.tabs.setCurrentIndex(1)
    item = next(viewer.grid_table.item(row, 1) for row in range(viewer.grid_table.rowCount())
                if viewer.grid_table.item(row, 1)
                and len(viewer.grid_table.item(row, 1).data(Qt.ItemDataRole.UserRole)) == 2)
    card = item.data(COURSE_CARD_ROLE)
    assert isinstance(card, CourseCard) and card.conflict_label == 'Conflicto de aula'
    assert {'BIO-G1', 'QUI-G1'} <= set(item.data(Qt.ItemDataRole.UserRole))
    image = paint_card(viewer, item)
    assert image.pixelColor(160, 105).name() == COLORS['danger_soft'].lower()


def test_selection_identity_survives_repaint_and_native_keyboard_navigation(viewer):
    populate(viewer)
    viewer.show()
    QApplication.processEvents()
    first = item_for(viewer, 'QUI-G1')
    viewer.grid_table.setCurrentItem(first)
    viewer.grid_table.setFocus()
    viewer._request_grid_render()
    assert viewer.grid_table.currentItem().data(Qt.ItemDataRole.UserRole) == ('QUI-G1',)
    QTest.keyClick(viewer.grid_table, Qt.Key.Key_Down)
    assert viewer.grid_table.currentItem().data(Qt.ItemDataRole.UserRole) == ('GEN-G1',)
    QTest.keyClick(viewer.grid_table, Qt.Key.Key_Tab)
    assert not viewer.grid_table.hasFocus()
    viewer._list_search.setText('no matching course')
    assert not viewer.grid_table.selectedItems()
    assert 'Sin sesiones' in viewer._grid_hint.text()


def test_split_session_selection_preserves_exact_block_across_repaint(viewer):
    viewer.display_schedule({'BIO-G1': ('A1', 1, 480, 540),
                             'CHEM-G1': ('A1', 1, 510, 525)}, TimeModel.default())
    viewer.tabs.setCurrentIndex(1)
    expected_blocks = [
        (1, 480, 510, ('BIO-G1',)),
        (1, 510, 525, ('BIO-G1', 'CHEM-G1')),
        (1, 525, 540, ('BIO-G1',)),
    ]
    for identity in expected_blocks:
        item = next(viewer.grid_table.item(row, 1)
                    for row in range(viewer.grid_table.rowCount())
                    if viewer.grid_table.item(row, 1)
                    and viewer.grid_table.item(row, 1).data(GRID_BLOCK_ROLE) == identity)
        viewer.grid_table.setCurrentItem(item)
        row = item.row()
        for _ in range(2):
            viewer._request_grid_render()
            assert viewer.grid_table.currentItem().data(GRID_BLOCK_ROLE) == identity
            assert viewer.grid_table.currentRow() == row
            assert viewer.grid_table.currentItem().isSelected()
