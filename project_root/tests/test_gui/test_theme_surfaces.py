"""Real Qt surface regressions: live brushes and fixed course-card identities."""
from copy import deepcopy
from pathlib import Path

import pytest
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPalette
from PyQt6.QtTest import QSignalSpy, QTest
from PyQt6.QtWidgets import QApplication, QLabel, QFrame, QStyle, QStyleOptionViewItem

from src.gui import schedule_grid_delegate, schedule_viewer_widget
from src.gui.course_manager_widget import CourseDialog, CourseManagerWidget
from src.gui.dialogs import ClassroomRestrictionsDialog, _InfoDialog
from src.gui.schedule_grid_delegate import (
    COURSE_CARD_ROLE, COURSE_CONFLICT_ACCENT, COURSE_CONFLICT_FILL,
    ScheduleGridDelegate,
)
from src.gui.schedule_viewer_widget import ScheduleViewerWidget, SummaryDialog
from src.gui.theme_contract import load_theme_file
from src.gui.course_presentation import course_presentation
from src.gui.theme import ThemeManager, builtin_themes, current_theme
from src.gui.theme_preferences import ThemePreferences
from src.scheduling.course_style import course_style
from src.scheduling.group import Group
from src.scheduling.time_model import TimeModel


ASSETS = Path(__file__).resolve().parents[3] / '.agents/skills/sorth-theme-designer/assets'
LIGHT = load_theme_file(ASSETS / 'academic-light.sorth-theme.json')
DARK = load_theme_file(ASSETS / 'midnight-dark.sorth-theme.json')


@pytest.fixture
def viewer(monkeypatch):
    # Exercise the public refresh hook independently of application persistence.
    monkeypatch.setattr(schedule_viewer_widget, 'COLORS', LIGHT.colors)
    monkeypatch.setattr(schedule_grid_delegate, 'COLORS', LIGHT.colors)
    widget = ScheduleViewerWidget()
    widget.resize(960, 640)
    yield widget
    widget.close()


def _populate(viewer):
    assignments = {
        f'BIO-G{i + 1}': ('A1', 1 + i % 6, 480 + i // 6 * 30, 510 + i // 6 * 30)
        for i in range(48)
    }
    assignments['BIO-G50'] = assignments['BIO-G1']
    groups = [Group(f'BIO-G{i}', 30, 'REGULAR', course_code='BIO',
                    course_name='Biología de prueba') for i in range(1, 51)]
    viewer.display_schedule(assignments, TimeModel.default(), groups)
    viewer.tabs.setCurrentIndex(1)
    return assignments, groups


def _items(table):
    return tuple(table.item(row, column)
                 for row in range(table.rowCount()) for column in range(table.columnCount()))


def _table_state(table):
    return (table.currentItem(), tuple(table.selectedItems()),
            tuple(table.isRowHidden(row) for row in range(table.rowCount())),
            table.horizontalHeader().sortIndicatorSection(),
            table.horizontalHeader().sortIndicatorOrder(),
            table.horizontalScrollBar().value(), table.verticalScrollBar().value())


def _paint(viewer, item, *, selected=False, delegate=None):
    image = QImage(220, 150, QImage.Format.Format_ARGB32)
    image.fill(QColor('magenta'))
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 220, 150)
    option.font = viewer.grid_table.font()
    if selected:
        option.state |= QStyle.StateFlag.State_Selected | QStyle.StateFlag.State_HasFocus
    painter = QPainter(image)
    (delegate or viewer.grid_table.itemDelegate()).paint(
        painter, option, viewer.grid_table.indexFromItem(item))
    painter.end()
    return image


def test_refresh_recolors_pending_and_time_cells_without_domain_or_view_changes(viewer, monkeypatch):
    assignments, groups = _populate(viewer)
    viewer._list_search.setText('bio')
    viewer._list_search.setSelection(1, 2)
    viewer.list_table.sortItems(2, Qt.SortOrder.DescendingOrder)
    viewer.classroom_table.sortItems(1, Qt.SortOrder.DescendingOrder)
    viewer.list_table.setCurrentCell(3, 2)
    viewer.classroom_table.setCurrentCell(2, 1)
    grid_item = next(item for item in _items(viewer.grid_table)
                     if item and item.data(COURSE_CARD_ROLE))
    viewer.grid_table.setCurrentItem(grid_item)
    viewer.show()
    QTest.qWait(20)
    viewer._list_search.setFocus()
    viewer._list_search.setSelection(1, 2)
    tables = (viewer.list_table, viewer.classroom_table, viewer.grid_table)
    for table in tables:
        table.verticalScrollBar().setValue(3)
    old_items = tuple(_items(table) for table in tables)
    old_states = tuple(_table_state(table) for table in tables)
    old_summary = deepcopy(viewer.summary_data)
    old_groups = {group.group_id: deepcopy(vars(group)) for group in groups}
    old_cache = viewer._course_colors
    old_colors = dict(viewer._course_colors)
    old_filters = viewer._filter_spec()
    old_matching = set(viewer._matching_gids)
    old_search = (viewer._list_search.text(), viewer._list_search.selectionStart(),
                  viewer._list_search.selectedText(), viewer._list_search.cursorPosition())
    signals = [QSignalSpy(signal) for signal in (
        viewer.edit_course_requested, viewer.manual_assignment_requested,
        viewer.placement_options_requested, viewer.group_removed, viewer.pin_requested,
        viewer.schedule_cleared, viewer.filters_changed,
        *(table.itemChanged for table in tables),
        *(table.itemSelectionChanged for table in tables),
    )]

    def no_rebuild(*_args, **_kwargs):
        pytest.fail('A color refresh must not rebuild views or run domain/filter actions')

    for name in ('_render_grid', '_display_list', '_display_classroom_view',
                 '_apply_filters', '_clear', 'display_schedule'):
        monkeypatch.setattr(viewer, name, no_rebuild)

    pending = next(viewer.list_table.item(row, 0) for row in range(viewer.list_table.rowCount())
                   if viewer.list_table.item(row, 0).data(Qt.ItemDataRole.UserRole) == 'BIO-G49')
    gutter = viewer.grid_table.item(0, 0)
    for theme in (DARK, LIGHT, DARK):
        monkeypatch.setattr(schedule_viewer_widget, 'COLORS', theme.colors)
        monkeypatch.setattr(schedule_grid_delegate, 'COLORS', theme.colors)
        viewer.refresh_theme()
        QApplication.processEvents()
        assert pending.background().color().name() == theme.colors['danger_soft'].lower()
        assert pending.foreground().color().name() == theme.colors['danger'].lower()
        assert gutter.background().color().name() == theme.colors['primary_soft'].lower()
        assert gutter.foreground().color().name() == theme.colors['on_primary_soft'].lower()
        assert tuple(_items(table) for table in tables) == old_items
        assert tuple(_table_state(table) for table in tables) == old_states
        assert viewer._filter_spec() == old_filters
        assert viewer._matching_gids == old_matching
        assert viewer.tabs.currentIndex() == 1
        assert (viewer._list_search.text(), viewer._list_search.selectionStart(),
                viewer._list_search.selectedText(), viewer._list_search.cursorPosition()) == old_search
        assert viewer._assignments == assignments
        assert viewer.summary_data == old_summary
        assert {group.group_id: vars(group) for group in groups} == old_groups
        assert viewer._course_colors is old_cache
        assert viewer._course_colors == {
            code: QColor(course_presentation(course_style(code), theme.colors["surface"]).fill)
            for code in old_colors
        }
        assert all(not spy for spy in signals)


def test_courses_conflicts_and_separators_follow_interface_themes(viewer, monkeypatch):
    _populate(viewer)
    cards = [item for item in _items(viewer.grid_table) if item and item.data(COURSE_CARD_ROLE)]
    ordinary = next(item for item in cards if not item.data(COURSE_CARD_ROLE).conflict_label)
    conflict = next(item for item in cards if item.data(COURSE_CARD_ROLE).conflict_label)
    images = {item.text(): _paint(viewer, item) for item in (ordinary, conflict)}
    for theme in (DARK, LIGHT):
        monkeypatch.setattr(schedule_viewer_widget, 'COLORS', theme.colors)
        monkeypatch.setattr(schedule_grid_delegate, 'COLORS', theme.colors)
        viewer.refresh_theme()
        for item in (ordinary, conflict):
            assert (_paint(viewer, item) == images[item.text()]) == (theme is LIGHT)
            selected = _paint(viewer, item, selected=True)
            assert selected.pixelColor(1, 75).name() == theme.colors["surface"].lower()
            assert selected.pixelColor(110, 4).name() == theme.colors["surface"].lower()
            assert selected.pixelColor(110, 3).name() == theme.colors['focus'].lower()
        assert ordinary.background().color().name() == course_presentation(course_style('BIO'), theme.colors['surface']).fill.lower()
        assert conflict.background().color().name() == theme.colors["danger_soft"].lower()
        assert conflict.foreground().color().name() == theme.colors["danger"].lower()
        assert _paint(viewer, conflict).pixelColor(190, 130).name() == theme.colors["danger_soft"].lower()


def test_delegate_candidate_palette_is_isolated_from_live_theme(viewer, monkeypatch):
    _populate(viewer)
    item = next(item for item in _items(viewer.grid_table)
                if item and item.data(COURSE_CARD_ROLE) and not item.data(COURSE_CARD_ROLE).conflict_label)
    preview = ScheduleGridDelegate(viewer.grid_table, colors=DARK.colors)
    monkeypatch.setattr(schedule_grid_delegate, 'COLORS', LIGHT.colors)
    candidate = _paint(viewer, item, selected=True, delegate=preview)
    live = _paint(viewer, item, selected=True)
    assert candidate.pixelColor(110, 3).name() == DARK.colors['focus'].lower()
    assert live.pixelColor(110, 3).name() == LIGHT.colors['focus'].lower()
    assert candidate.pixelColor(190, 130) != live.pixelColor(190, 130)
    assert candidate.pixelColor(1, 75).name() == DARK.colors["surface"].lower()
    assert live.pixelColor(1, 75).name() == LIGHT.colors["surface"].lower()


def test_status_labels_and_summary_cards_use_canonical_selectors(viewer):
    _populate(viewer)
    course = CourseDialog()
    manager = CourseManagerWidget()
    restriction = ClassroomRestrictionsDialog(None, {'A1': ['BIO', 'QUIL']})
    info = _InfoDialog(None, 'Listo', 'Información')
    warning = _InfoDialog(None, 'Atención', 'Advertencia', warning=True)
    summary = SummaryDialog(viewer, viewer.summary_data)
    try:
        assert restriction.findChild(QLabel, 'helpText').styleSheet() == ''
        assert info.findChild(QLabel, 'dialogInfoHeader').styleSheet() == ''
        assert warning.findChild(QLabel, 'dialogWarningHeader').styleSheet() == ''
        assert manager._empty_label.objectName() == 'mutedText'
        course.code_edit.setText('QUIL')
        assert course.room_type_label.objectName() == 'headingText'
        course.code_edit.setText('BIO')
        assert course.room_type_label.objectName() == 'successText'
        assert course.room_type_label.styleSheet() == ''
        cards = summary.findChildren(QFrame, 'summaryCard')
        assert [card.property('tone') for card in cards] == ['success', 'danger', 'primary', 'accent']
        for card in cards:
            assert card.styleSheet() == ''
            assert card.findChild(QLabel, 'summaryValue').styleSheet() == ''
            assert card.findChild(QLabel, 'summaryCaption').styleSheet() == ''
        assert summary.findChild(QLabel, 'dangerText')
    finally:
        for widget in (course, manager, restriction, info, warning, summary):
            widget.close()


def test_application_switch_updates_open_dialogs_without_touching_editor_drafts(tmp_path, monkeypatch):
    app = QApplication.instance()
    previous = current_theme()
    manager = ThemeManager(app, preferences=ThemePreferences(tmp_path / 'appearance.json'))
    monkeypatch.setattr(app, '_sorth_theme_manager', manager, raising=False)
    viewer = ScheduleViewerWidget()
    viewer.resize(960, 640)
    _populate(viewer)
    viewer._list_search.setText('bio')
    viewer.list_table.sortItems(2, Qt.SortOrder.DescendingOrder)
    viewer.list_table.setCurrentCell(3, 2)
    viewer.grid_table.setCurrentItem(next(item for item in _items(viewer.grid_table)
                                         if item and item.data(COURSE_CARD_ROLE)))
    course = CourseDialog(viewer)
    course.code_edit.setText('QUIL')
    course.name_edit.setText('Nombre sin guardar')
    course.groups_spin.setValue(7)
    course.classroom_edit.setText('Aula nueva')
    restriction = ClassroomRestrictionsDialog(viewer, {'A1': ['BIO', 'QUIL']})
    restriction.course_list.item(0).setCheckState(Qt.CheckState.Unchecked)
    restriction.cls_list.item(0).setCheckState(Qt.CheckState.Checked)
    summary = SummaryDialog(viewer, viewer.summary_data)
    info = _InfoDialog(viewer, 'Listo', 'Información')
    warning = _InfoDialog(viewer, 'Atención', 'Advertencia', warning=True)
    widgets = (viewer, course, restriction, summary, info, warning)
    try:
        viewer.show()
        restriction.show()
        summary.show()
        info.show()
        warning.show()
        course.show()
        QTest.qWait(20)
        QApplication.processEvents()
        course.name_edit.setFocus()
        course.name_edit.setSelection(2, 6)
        tables = (viewer.list_table, viewer.classroom_table, viewer.grid_table)
        for table in tables:
            table.verticalScrollBar().setValue(3)
        old_states = tuple(_table_state(table) for table in tables)
        old_filters = viewer._filter_spec()
        old_name = (course.name_edit.text(), course.name_edit.selectionStart(),
                    course.name_edit.selectedText(), course.name_edit.cursorPosition())
        old_restrictions = restriction.get_restrictions()
        old_groups = deepcopy([vars(group) for group in viewer._groups.values()])
        old_items = tuple(_items(table) for table in
                          (viewer.list_table, viewer.classroom_table, viewer.grid_table))
        old_summary = deepcopy(viewer.summary_data)
        old_cache = viewer._course_colors
        course_changes = QSignalSpy(course.name_edit.textChanged)
        restriction_changes = QSignalSpy(restriction.course_list.itemChanged)
        selected_course = viewer.grid_table.currentItem()
        for choice in (*builtin_themes()[1:], builtin_themes()[0]):
            manager.save_and_apply(choice.spec, key=choice.key)
            QApplication.processEvents()
            colors = choice.spec.colors
            assert tuple(_items(table) for table in
                         (viewer.list_table, viewer.classroom_table, viewer.grid_table)) == old_items
            assert viewer.grid_table.currentItem() is selected_course
            assert tuple(_table_state(table) for table in tables) == old_states
            assert viewer._filter_spec() == old_filters
            assert viewer._course_colors is old_cache
            assert viewer.summary_data == old_summary
            assert [vars(group) for group in viewer._groups.values()] == old_groups
            assert (course.name_edit.text(), course.name_edit.selectionStart(),
                    course.name_edit.selectedText(), course.name_edit.cursorPosition()) == old_name
            assert course.code_edit.text() == 'QUIL'
            assert course.groups_spin.value() == 7
            assert course.classroom_edit.text() == 'Aula nueva'
            assert restriction.get_restrictions() == old_restrictions
            assert not course_changes and not restriction_changes
            expected_labels = [(course.room_type_label, 'heading'),
                (restriction.findChild(QLabel, 'helpText'), 'text'),
                (info.findChild(QLabel, 'dialogInfoHeader'), 'on_primary_soft'),
                (warning.findChild(QLabel, 'dialogWarningHeader'), 'warning')]
            for card in summary.findChildren(QFrame, 'summaryCard'):
                foreground = {'success': 'success', 'danger': 'danger',
                              'primary': 'on_primary_soft', 'accent': 'text'}[card.property('tone')]
                expected_labels.extend((label, foreground) for label in card.findChildren(QLabel))
            for label, role in expected_labels:
                assert label.palette().color(QPalette.ColorRole.WindowText).name() == colors[role].lower()
            time_cell = viewer.grid_table.item(0, 0)
            assert time_cell.foreground().color().name() == colors['on_primary_soft'].lower()
            pending = next(viewer.list_table.item(row, 0) for row in range(viewer.list_table.rowCount())
                           if viewer.list_table.item(row, 0).data(Qt.ItemDataRole.UserRole) == 'BIO-G49')
            assert pending.background().color().name() == colors['danger_soft'].lower()
    finally:
        for widget in reversed(widgets):
            widget.close()
        manager._apply(previous)


def test_dark_course_fill_changes_without_replacing_identity(viewer, monkeypatch):
    _populate(viewer)
    item = next(item for item in _items(viewer.grid_table)
                if item and item.data(COURSE_CARD_ROLE) and not item.data(COURSE_CARD_ROLE).conflict_label)
    card = item.data(COURSE_CARD_ROLE)
    before = _paint(viewer, item).pixelColor(190, 130)
    viewer.grid_table.setCurrentItem(item)
    monkeypatch.setattr(schedule_viewer_widget, 'COLORS', DARK.colors)
    monkeypatch.setattr(schedule_grid_delegate, 'COLORS', DARK.colors)
    viewer.refresh_theme()
    after = _paint(viewer, item).pixelColor(190, 130)
    assert after != before, 'Dark theme must adapt the session fill to its background'
    assert viewer.grid_table.currentItem() is item
    assert item.data(COURSE_CARD_ROLE) == card
    assert item.background().color() == after
