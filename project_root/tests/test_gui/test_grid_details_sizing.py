"""Native content sizing stays bounded without changing detail interaction."""
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QStyleFactory

from src.gui.i18n import language_manager
from src.gui.i18n_widgets import ResponsiveDialogButtonBox
from src.gui.schedule_viewer_widget import GridSessionDetailsDialog, ScheduleViewerWidget
from src.gui.theme import apply_theme
from src.scheduling.time_model import TimeModel


@pytest.fixture
def viewer():
    widget = ScheduleViewerWidget()
    apply_theme(widget)
    widget.display_schedule({'BIO-G1': ('Aula 201', 1, 480, 540)}, TimeModel.default(),
                            course_name_by_code={'BIO': 'Biología celular'})
    yield widget
    widget.close()
    language_manager().set_language('es', persist=False)


def open_details(viewer, expanded=False, gids=('BIO-G1',)):
    dialog = GridSessionDetailsDialog(viewer, gids)
    if expanded:
        dialog.setStyleSheet('QPlainTextEdit, QPushButton, QComboBox { font-size: 20pt; }')
    dialog.show()
    dialog.activateWindow()
    dialog.details.setFocus()
    QApplication.processEvents()
    return dialog


def assert_footer_inside(dialog):
    footer = dialog.findChild(ResponsiveDialogButtonBox)
    assert dialog.rect().contains(footer.geometry())
    for button in footer.buttons():
        assert button.isVisible()
        assert footer.rect().contains(button.geometry())
        assert button.width() >= button.minimumSizeHint().width()
        assert button.height() >= button.minimumSizeHint().height()


@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('style', ['Fusion', 'Windows'])
@pytest.mark.parametrize('expanded', [False, True])
@pytest.mark.parametrize('screen_size', [(1280, 960), (460, 420)])
def test_initial_size_fits_native_text_and_available_screen(viewer, monkeypatch,
                                                          language, style, expanded, screen_size):
    app = QApplication.instance()
    original_style = app.style().objectName()
    if style not in QStyleFactory.keys():
        pytest.skip(f'{style} is unavailable')
    available = QRect(40, 30, *screen_size)
    monkeypatch.setattr(GridSessionDetailsDialog, 'screen',
                        lambda self: SimpleNamespace(availableGeometry=lambda: available))
    app.setStyle(style)
    language_manager().set_language(language, persist=False)
    short = long = None
    try:
        short = open_details(viewer, expanded)
        assert available.contains(short.frameGeometry())
        assert short.details.verticalScrollBar().maximum() == 0
        assert short.details.horizontalScrollBar().maximum() == 0
        assert short.height() < 420
        if expanded:
            assert short.details.font().pointSizeF() == 20
        assert_footer_inside(short)
        short_height = short.height()
        short.reject()

        name = 'Álgebra <avanzada> & conservación de ecosistemas ' * 150
        viewer._name_map['BIO-G1'] = name
        long = open_details(viewer, expanded)
        assert available.contains(long.frameGeometry())
        assert long.height() > short_height
        assert long.details.verticalScrollBar().maximum() > 0
        assert long.details.horizontalScrollBar().maximum() == 0
        assert name in long.details.toPlainText()
        assert_footer_inside(long)
        assert long.details.hasFocus()
        scrollbar = long.details.verticalScrollBar()
        pages = 2 + scrollbar.maximum() // max(1, scrollbar.pageStep())
        for _ in range(pages):
            QTest.keyClick(long.details, Qt.Key.Key_PageDown)
        assert scrollbar.value() == scrollbar.maximum()
        QTest.keyClick(long.details, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        assert long.details.textCursor().selectedText().replace('\u2029', '\n') == long.details.toPlainText()
    finally:
        if short is not None:
            short.reject()
        if long is not None:
            long.reject()
        app.setStyle(original_style)


@pytest.mark.parametrize('language', ['es', 'en'])
def test_narrow_conflict_selector_and_footer_do_not_expand_screen(viewer, monkeypatch, language):
    available = QRect(0, 0, 300, 420)
    monkeypatch.setattr(GridSessionDetailsDialog, 'screen',
                        lambda self: SimpleNamespace(availableGeometry=lambda: available))
    language_manager().set_language(language, persist=False)
    assignments = {'BIO-G1': ('Aula 201', 1, 480, 540), 'QUI-G1': ('Aula 201', 1, 490, 550)}
    viewer.display_schedule(assignments, TimeModel.default(),
                            course_name_by_code={'BIO': 'Biología celular', 'QUI': 'Química general'})
    dialog = open_details(viewer, expanded=True, gids=tuple(assignments))
    try:
        assert available.contains(dialog.frameGeometry())
        assert dialog.rect().contains(dialog.session_selector.geometry())
        assert dialog.session_selector.isVisible()
        assert not dialog.view_in_list.isEnabled()
        assert_footer_inside(dialog)
        assert dialog.findChild(ResponsiveDialogButtonBox).orientation() == Qt.Orientation.Vertical
        initial_size = dialog.size()
        dialog.session_selector.setCurrentIndex(1)
        QApplication.processEvents()
        assert dialog.view_in_list.isEnabled()
        assert dialog.size() == initial_size
        assert 'BIO-G1' in dialog.details.toPlainText()
    finally:
        dialog.reject()


def test_manual_resize_survives_locale_content_and_repeat_show(viewer):
    dialog = open_details(viewer)
    try:
        manual_size = QSize(490, 320)
        dialog.resize(manual_size)
        language_manager().set_language('en', persist=False)
        viewer._name_map['BIO-G1'] = 'Full long course name ' * 100
        dialog.refresh_details()
        dialog.hide()
        dialog.show()
        QApplication.processEvents()
        assert dialog.size() == manual_size
        assert dialog.details.verticalScrollBar().maximum() > 0
        assert 'Session: BIO-G1' in dialog.details.toPlainText()
        assert_footer_inside(dialog)
    finally:
        dialog.reject()


def test_repeated_open_close_remeasures_without_changing_grid_focus(viewer):
    viewer.tabs.setCurrentIndex(1)
    viewer.resize(960, 640)
    viewer.show()
    viewer.activateWindow()
    QApplication.processEvents()
    item = next(viewer.grid_table.item(row, col)
                for row in range(viewer.grid_table.rowCount())
                for col in range(1, viewer.grid_table.columnCount())
                if viewer.grid_table.item(row, col) is not None
                and viewer.grid_table.item(row, col).data(Qt.ItemDataRole.UserRole) == ('BIO-G1',))
    sizes = []
    for _ in range(3):
        viewer.grid_table.setCurrentItem(item)
        viewer._show_grid_details()
        QApplication.processEvents()
        dialog = viewer._grid_details_dialog
        assert dialog is not None and dialog.details.hasFocus()
        sizes.append(dialog.size())
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        QApplication.processEvents()
        assert viewer._grid_details_dialog is None
        assert viewer.grid_table.hasFocus()
        assert viewer.grid_table.currentItem() is item
    assert sizes[0] == sizes[1] == sizes[2]
