"""First-show native seed focus must preserve the complete caption and size."""
import pytest
from PyQt6.QtCore import Qt, QSettings, QSize
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QStyle, QStyleOptionButton

from src.gui.i18n import language_manager
from src.gui.main_window import MainWindow
from src.gui.smoke_rendering import settle_capture_layout
from src.gui.theme import COLORS, builtin_themes, theme_manager
from src.infrastructure.session_repository import SessionRepository


def text_ink(image, color):
    """Normalize only the themed text ink, excluding border and indicator."""
    points = [(x, y) for y in range(image.height()) for x in range(image.width())
              if image.pixelColor(x, y).name() == color.lower()]
    assert points, 'The native caption must contain readable text ink.'
    left = min(x for x, _ in points)
    top = min(y for _, y in points)
    return {(x - left, y - top) for x, y in points}


@pytest.mark.parametrize('style', ['Fusion', 'Windows'])
@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('theme', ['original', 'nocturno', 'high_contrast'])
def test_seed_first_focus_keeps_native_caption_and_reading_budget(tmp_path, style, language, theme):
    app = QApplication.instance()
    manager, appearance = language_manager(), theme_manager()
    original_language, original_theme, original_style = manager.language, appearance.current, app.style().objectName()
    window = None
    try:
        app.setStyle(style)
        manager.set_language(language, persist=False)
        appearance._apply(next(choice.spec for choice in builtin_themes() if choice.key == theme))
        window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False,
                            feature_settings=QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat))
        window.resize(960, 640)
        window.show()
        window.activateWindow()
        app.processEvents()
        settle_capture_layout(window)
        checkbox = window.chk_random_seed
        resting_size = checkbox.size()
        checkbox.setFocus()
        app.processEvents()
        settle_capture_layout(window)
        assert checkbox.hasFocus()
        assert checkbox.size() == resting_size
        option = QStyleOptionButton()
        checkbox.initStyleOption(option)
        caption = checkbox.fontMetrics().size(Qt.TextFlag.TextShowMnemonic, checkbox.text())
        required = checkbox.style().sizeFromContents(QStyle.ContentsType.CT_CheckBox, option, caption, checkbox)
        contents = checkbox.style().subElementRect(QStyle.SubElement.SE_CheckBoxContents, option, checkbox)
        assert checkbox.width() >= required.width()
        assert checkbox.height() >= required.height()
        assert contents.width() >= caption.width()
        assert contents.height() >= caption.height()
        # Compare the actual native paint with a deliberately ample reference.
        # Four logical pixels preserve subpixel alignment at 1x/1.5x/2x scale.
        actual_size = checkbox.size()
        actual_ink = text_ink(checkbox.grab().toImage(), COLORS['text'])
        checkbox.resize(actual_size + QSize(4, 4))
        reference_ink = text_ink(checkbox.grab().toImage(), COLORS['text'])
        checkbox.resize(actual_size)
        assert actual_ink == reference_ink
        seed = window.seed_input.value()
        QTest.keyClick(checkbox, Qt.Key.Key_Space)
        assert checkbox.isChecked() and not window.seed_input.isEnabled()
        QTest.keyClick(checkbox, Qt.Key.Key_Space)
        assert not checkbox.isChecked() and window.seed_input.isEnabled()
        assert window.seed_input.value() == seed
        window.tabs.setCurrentIndex(1)
        for index, table in enumerate((window.schedule_viewer.list_table,
                                       window.schedule_viewer.grid_table,
                                       window.schedule_viewer.classroom_table)):
            window.schedule_viewer.tabs.setCurrentIndex(index)
            app.processEvents()
            settle_capture_layout(window)
            assert window.size() == QSize(960, 640)
            assert table.viewport().height() >= 120
    finally:
        if window is not None:
            window.close()
        appearance._apply(original_theme)
        manager.set_language(original_language, persist=False)
        app.setStyle(original_style)
