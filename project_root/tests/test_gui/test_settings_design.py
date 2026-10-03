"""Native section navigation preserves one transaction and accessible geometry."""
import json
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QScrollArea, QStyleFactory, QStyle, QStyleOptionComboBox, QWidget

from src.gui.features import FEATURES
from src.gui.i18n import language_manager
from src.gui.settings_dialog import SettingsDialog
from tests.test_gui.test_mcp_setup_ux import window, settle_settings_layout, caption_preserved_across_soft_breaks


def test_sections_cover_each_feature_once_and_open_general(window):
    dialog = SettingsDialog(window)
    dialog.show()
    settle_settings_layout(dialog)
    assert dialog.section_selector.currentData() == 'general'
    keys = [key for group in dialog.section_features.values() for key in group]
    assert len(keys) == len(set(keys)) == len(FEATURES)
    assert set(keys) == {feature.key for feature in FEATURES}
    assert len(dialog.findChildren(QScrollArea)) == 1
    for section, features in dialog.section_features.items():
        dialog.select_section(section)
        settle_settings_layout(dialog)
        assert dialog.sections[section].isVisible()
        assert all(not panel.isVisible() for key, panel in dialog.sections.items() if key != section)
        assert all(dialog.controls[key].isVisible() for key in features)
    assert all(not control.isChecked() for control in dialog.controls.values())
    assert not window._features.path.exists()
    dialog.reject()


def test_navigation_and_retranslation_preserve_pending_choices_and_cancel(window):
    manager = language_manager()
    original = manager.language
    manager.set_language('en', persist=False)
    dialog = SettingsDialog(window)
    try:
        dialog.show()
        settle_settings_layout(dialog)
        assert dialog.save_state.text() == 'No unsaved changes'
        dialog.controls['undo_redo'].click()
        dialog.section_selector.setFocus()
        QTest.keyClick(dialog.section_selector, Qt.Key.Key_Down)
        settle_settings_layout(dialog)
        assert dialog.section_selector.currentData() == 'resources'
        dialog.controls['teacher'].click()
        assert dialog.save_state.text() == 'Unsaved changes: 2'
        dialog.select_section('advanced')
        assert dialog.controls['undo_redo'].isChecked()
        dialog.section_selector.setFocus()
        manager.set_language('es', persist=False)
        settle_settings_layout(dialog)
        assert dialog.section_selector.currentData() == 'advanced'
        assert dialog.section_selector.currentText() == 'Herramientas avanzadas'
        assert dialog.section_selector.hasFocus()
        assert dialog.save_state.text() == 'Cambios sin guardar: 2'
        dialog.select_section('general')
        dialog.controls['undo_redo'].click()
        assert dialog.save_state.text() == 'Cambios sin guardar: 1'
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        assert not dialog.isVisible()
        assert not window._features.path.exists()
        assert not window.resources.catalog('teacher').enabled
    finally:
        dialog.reject()
        manager.set_language(original, persist=False)


@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('style_name', ['Fusion', 'Windows'])
@pytest.mark.parametrize('expanded', [False, True])
def test_each_section_fits_small_native_window_with_large_fonts(window, locale, style_name, expanded):
    app = QApplication.instance()
    original_style = app.style().objectName()
    manager = language_manager()
    original_language = manager.language
    if style_name not in QStyleFactory.keys():
        pytest.skip(f'{style_name} is unavailable')
    app.setStyle(style_name)
    manager.set_language(locale, persist=False)
    dialog = SettingsDialog(window)
    try:
        if expanded:
            dialog.setStyleSheet('QPushButton, QCheckBox, QLabel, QComboBox { font-size: 20pt; }')
        dialog.resize(460, 420)
        dialog.show()
        for section, feature_keys in dialog.section_features.items():
            dialog.select_section(section)
            snapshot = settle_settings_layout(dialog)
            snapshot['section'] = section
            snapshot['chrome'] = [
                {'name': widget.objectName() or type(widget).__name__,
                 'visible': widget.isVisible(), 'width': widget.width(), 'height': widget.height(),
                 'minimum_width': widget.minimumSizeHint().width(),
                 'minimum_height': widget.minimumSizeHint().height()}
                for widget in (dialog.header, dialog.section_selector, dialog.scroll,
                               dialog.save_state, dialog.buttons)]
            snapshot['body_widgets'] = sorted([
                {'name': widget.objectName() or type(widget).__name__,
                 'text': widget.text() if hasattr(widget, 'text') else '',
                 'width': widget.width(), 'height': widget.height(),
                 'minimum_width': widget.minimumSizeHint().width(),
                 'minimum_height': widget.minimumSizeHint().height(),
                 'font_points': widget.font().pointSizeF(), 'logical_dpi': widget.logicalDpiX()}
                for widget in dialog.scroll.widget().findChildren(QWidget) if widget.isVisible()],
                key=lambda item: item['minimum_width'], reverse=True)
            # Native CI retains this untruncated report even when pytest shortens
            # an assertion's dictionary representation.
            report_dir = Path(__file__).resolve().parents[2] / 'build' / 'reports'
            report_dir.mkdir(parents=True, exist_ok=True)
            report_path = report_dir / f'settings-geometry-{style_name}-{locale}-{expanded}-{section}.json'
            report_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
            assert dialog.size() == QSize(460, 420), snapshot
            assert dialog.scroll.horizontalScrollBar().maximum() == 0, snapshot
            assert dialog.scroll.viewport().height() > 100, snapshot
            assert dialog.intro_label.isHidden()
            assert dialog.section_selector.isVisible()
            assert dialog.section_selector.width() >= dialog.section_selector.minimumSizeHint().width()
            # A combo's minimum-content hint deliberately permits long future
            # locales to elide. Current ES/EN section titles must fit in full
            # inside the actual native edit field, including its arrow gutter.
            selector = dialog.section_selector
            option = QStyleOptionComboBox()
            selector.initStyleOption(option)
            text_rect = selector.style().subControlRect(
                QStyle.ComplexControl.CC_ComboBox, option,
                QStyle.SubControl.SC_ComboBoxEditField, selector)
            assert selector.fontMetrics().horizontalAdvance(selector.currentText()) <= text_rect.width()
            actions = [dialog.controls[key] for key in feature_keys]
            if section == 'advanced':
                actions.append(dialog.calendar_button)
            if section == 'mcp':
                actions += [dialog.mcp_check_button, dialog.mcp_prepare_button, dialog.mcp_help_button]
            for action in actions:
                assert action.isVisible()
                assert action.width() >= action.minimumSizeHint().width(), snapshot
                assert action.height() >= action.minimumSizeHint().height(), snapshot
                source = action._messages['setText'][1][0].render()
                assert caption_preserved_across_soft_breaks(action.text(), source)
                assert action.accessibleName() == source
                dialog.scroll.ensureWidgetVisible(action)
                QApplication.processEvents()
                assert dialog.scroll.viewport().rect().contains(action.mapTo(dialog.scroll.viewport(), action.rect().center()))
            for action in dialog.buttons.buttons():
                assert action.width() >= action.minimumSizeHint().width(), snapshot
                assert action.height() >= action.minimumSizeHint().height(), snapshot
                assert dialog.rect().contains(action.mapTo(dialog, action.rect().topLeft())), snapshot
                assert dialog.rect().contains(action.mapTo(dialog, action.rect().bottomRight())), snapshot
    finally:
        dialog.reject()
        app.setStyle(original_style)
        manager.set_language(original_language, persist=False)


def test_saved_summary_resets_on_reopen(window):
    dialog = SettingsDialog(window)
    dialog.controls['undo_redo'].setChecked(True)
    dialog.controls['pinned_sessions'].setChecked(True)
    assert dialog.save_state.property('pending') is True
    dialog.accept()
    dialog = SettingsDialog(window)
    assert dialog.controls['undo_redo'].isChecked()
    assert dialog.controls['pinned_sessions'].isChecked()
    assert dialog.save_state.property('pending') is False
    dialog.reject()


@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('style_name', ['Fusion', 'Windows'])
@pytest.mark.parametrize('backwards', [False, True], ids=['Tab', 'Shift-Tab'])
def test_keyboard_navigation_scrolls_every_section_control_into_view(window, locale, style_name, backwards):
    app = QApplication.instance()
    original_style = app.style().objectName()
    manager = language_manager()
    original_language = manager.language
    if style_name not in QStyleFactory.keys():
        pytest.skip(f'{style_name} is unavailable')
    app.setStyle(style_name)
    manager.set_language(locale, persist=False)
    dialog = SettingsDialog(window)
    try:
        dialog.setStyleSheet('QPushButton, QCheckBox, QLabel, QComboBox { font-size: 20pt; }')
        dialog.resize(460, 420)
        dialog.show()
        for section, feature_keys in dialog.section_features.items():
            dialog.select_section(section)
            settle_settings_layout(dialog)
            dialog.section_selector.setFocus()
            seen = []
            modifiers = Qt.KeyboardModifier.ShiftModifier if backwards else Qt.KeyboardModifier.NoModifier
            for _ in range(35):
                QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab, modifiers)
                settle_settings_layout(dialog)
                focused = QApplication.focusWidget()
                assert focused is not None and focused.isVisible()
                if focused is dialog.section_selector:
                    break
                seen.append(focused)
                if dialog.scroll.widget().isAncestorOf(focused):
                    # No test-side ensureWidgetVisible: actual Tab/Shift+Tab must
                    # make a focused action readable without mouse scrolling.
                    assert dialog.scroll.viewport().rect().contains(
                        focused.mapTo(dialog.scroll.viewport(), focused.rect().center()))
            else:
                pytest.fail(f'Keyboard traversal never returned to the {section} selector')
            expected = [dialog.controls[key] for key in feature_keys]
            if section == 'mcp':
                expected += [dialog.mcp_status_label, dialog.mcp_check_button,
                             dialog.mcp_prepare_button, dialog.mcp_permission_label,
                             dialog.mcp_help_button]
            assert all(widget in seen for widget in expected)
            assert dialog.save_state in seen
            assert all(not panel.isAncestorOf(widget)
                       for key, panel in dialog.sections.items() if key != section
                       for widget in seen)
    finally:
        dialog.reject()
        app.setStyle(original_style)
        manager.set_language(original_language, persist=False)


@pytest.mark.parametrize('locale', ['es', 'en'])
def test_short_shell_preserves_full_meanings_and_restores_wide_labels(window, locale):
    manager = language_manager()
    original = manager.language
    manager.set_language(locale, persist=False)
    dialog = SettingsDialog(window)
    try:
        dialog.resize(460, 420)
        dialog.show()
        settle_settings_layout(dialog)
        assert dialog.header.isHidden()
        assert dialog.intro_label.isHidden()
        assert dialog.scroll.viewport().height() > 100
        dialog.select_section('advanced')
        assert dialog.section_selector.currentText() == ('Avanzado' if locale == 'es' else 'Advanced')
        assert dialog.save_state.accessibleDescription() == ('Sin cambios por guardar' if locale == 'es' else 'No unsaved changes')
        dialog.controls['undo_redo'].setChecked(True)
        assert dialog.save_state.text() == ('Sin guardar: 1' if locale == 'es' else 'Unsaved: 1')
        assert dialog.save_state.accessibleDescription() == ('Cambios sin guardar: 1' if locale == 'es' else 'Unsaved changes: 1')
        dialog.resize(680, 620)
        settle_settings_layout(dialog)
        assert dialog.header.isVisible() and dialog.intro_label.isVisible()
        assert dialog.section_selector.currentData() == 'advanced'
        assert dialog.section_selector.currentText() == ('Herramientas avanzadas' if locale == 'es' else 'Advanced tools')
        assert dialog.save_state.text() == dialog.save_state.accessibleDescription()
        assert dialog.controls['undo_redo'].isChecked()
        dialog.reject()
        assert not window._features.path.exists()
    finally:
        dialog.reject()
        manager.set_language(original, persist=False)


@pytest.mark.parametrize('style_name', ['Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('expanded', [False, True])
def test_checkbox_focus_keeps_fresh_native_height_after_retranslation(window, style_name, locale, expanded):
    from PyQt6.QtCore import QRect
    from PyQt6.QtWidgets import QStyleOptionButton

    app = QApplication.instance()
    original_style = app.style().objectName()
    manager = language_manager()
    original_language = manager.language
    if style_name not in QStyleFactory.keys():
        pytest.skip(f'{style_name} is unavailable')
    app.setStyle(style_name)
    manager.set_language(locale, persist=False)
    dialog = SettingsDialog(window)
    try:
        if expanded:
            dialog.setStyleSheet('QPushButton, QCheckBox { font-size: 20pt; }')
        dialog.resize(460, 420)
        dialog.show()
        dialog.select_section('advanced')
        settle_settings_layout(dialog)
        checkbox = dialog.controls['project_scenarios']
        checkbox.setFocus()
        QTest.keyClick(checkbox, Qt.Key.Key_Space)
        font_before = checkbox.font()
        manager.set_language('en' if locale == 'es' else 'es', persist=False)
        settle_settings_layout(dialog)
        assert checkbox.hasFocus() and checkbox.isChecked()
        caption = checkbox.text()
        required_heights = []
        for target in (checkbox, dialog.section_selector, checkbox):
            target.setFocus()
            snapshot = settle_settings_layout(dialog)
            option = QStyleOptionButton()
            checkbox.initStyleOption(option)
            style = checkbox.style()
            text_size = style.itemTextRect(
                checkbox.fontMetrics(), QRect(), Qt.TextFlag.TextShowMnemonic,
                False, checkbox.text()).size()
            # minimumSizeHint can retain the previous focused state's cache.
            # Ask the current native style afresh so Linux cannot mask the same
            # one-pixel focused/unfocused delta observed by Windows CI.
            native_size = style.sizeFromContents(
                QStyle.ContentsType.CT_CheckBox, option, text_size, checkbox)
            contents = style.subElementRect(QStyle.SubElement.SE_CheckBoxContents, option, checkbox)
            required_heights.append(native_size.height())
            assert checkbox.height() >= native_size.height(), snapshot
            assert checkbox.height() >= checkbox.minimumSizeHint().height(), snapshot
            assert contents.height() >= text_size.height(), snapshot
            assert checkbox.text() == caption and checkbox.font() == font_before
            assert checkbox.isChecked()
            assert dialog.size() == QSize(460, 420), snapshot
            assert dialog.scroll.horizontalScrollBar().maximum() == 0, snapshot
        assert len(set(required_heights)) == 1
        source = checkbox._messages['setText'][1][0].render()
        assert caption_preserved_across_soft_breaks(caption, source)
        assert checkbox.accessibleName() == source
        dialog.reject()
        assert not window._features.path.exists()
    finally:
        dialog.reject()
        app.setStyle(original_style)
        manager.set_language(original_language, persist=False)
