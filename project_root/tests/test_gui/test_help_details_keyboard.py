"""Help/details preserve fresh native metrics and keyboard visibility."""
from pathlib import Path
import time
import pytest
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QStyle, QStyleFactory, QStyleOptionButton
from src.gui.i18n import language_manager
from src.gui.mcp_client_help import McpClientHelp, client_configuration
from src.gui.schedule_viewer_widget import GridSessionDetailsDialog, ScheduleViewerWidget
from src.gui.theme import builtin_themes, theme_manager
from src.gui.theme_contract import load_theme_file
from src.scheduling.time_model import TimeModel

CUSTOM = load_theme_file(Path(__file__).resolve().parents[3] /
    '.agents/skills/sorth-theme-designer/assets/midnight-dark.sorth-theme.json')
COMMAND = [r'C:\Users\Synthetic Name\SORTH\SORTH-MCP.exe', '--serve']


@pytest.fixture
def presentation():
    app, manager = QApplication.instance(), theme_manager()
    original = app.style().objectName(), language_manager().language, manager.current
    yield app, manager
    app.setStyle(original[0])
    language_manager().set_language(original[1], persist=False)
    manager._apply(original[2])


def settle(dialog):
    previous, stable = None, 0
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        QApplication.processEvents()
        boxes = dialog.findChildren(QDialogButtonBox)
        snapshot = (dialog.size(), tuple((box.geometry(), tuple((b.text(), b.geometry())
                    for b in box.buttons())) for box in boxes))
        if isinstance(dialog, McpClientHelp):
            snapshot += (dialog.scroll.viewport().size(), dialog.scroll.widget().size(),
                         dialog.scroll.verticalScrollBar().value())
        active = any(timer.isActive() for timer in dialog.findChildren(QTimer))
        stable = stable + 1 if snapshot == previous and not active else 0
        if stable >= 2:
            return
        previous = snapshot
        QTest.qWait(1)
    pytest.fail('Help/details native layout did not settle')


def assert_fresh_button_size(button):
    # minimumSizeHint can cache the unfocused QSS border width.
    option = QStyleOptionButton()
    option.initFrom(button)
    option.text = button.text()
    if button.autoDefault():
        option.features |= QStyleOptionButton.ButtonFeature.AutoDefaultButton
    if button.isDefault():
        option.features |= QStyleOptionButton.ButtonFeature.DefaultButton
    text = button.fontMetrics().size(Qt.TextFlag.TextShowMnemonic, button.text())
    native = button.style().sizeFromContents(QStyle.ContentsType.CT_PushButton, option, text, button)
    assert button.width() >= native.width(), (button.text(), button.size(), native)
    assert button.height() >= native.height(), (button.text(), button.size(), native)


def assert_footer(dialog):
    for box in dialog.findChildren(QDialogButtonBox):
        assert dialog.rect().contains(box.geometry())
        for button in box.buttons():
            assert box.rect().contains(button.geometry())
            assert_fresh_button_size(button)


@pytest.mark.parametrize('kind', ['help', 'details'])
@pytest.mark.parametrize('style_name', ['native-default', 'Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('large', [False, True])
@pytest.mark.parametrize('spec', [builtin_themes()[0].spec, builtin_themes()[1].spec, CUSTOM],
                         ids=['light', 'dark', 'custom'])
def test_help_details_focused_buttons_fit_fresh_native_metrics(
        presentation, kind, style_name, locale, large, spec):
    app, manager = presentation
    if style_name != 'native-default':
        if style_name not in QStyleFactory.keys():
            pytest.skip(f'{style_name} unavailable')
        app.setStyle(style_name)
    manager._apply(spec)
    language_manager().set_language(locale, persist=False)
    viewer = None
    if kind == 'help':
        dialog = McpClientHelp(COMMAND, permission_enabled=True)
    else:
        viewer = ScheduleViewerWidget()
        viewer.display_schedule({'BIO-G1': ('Aula 201', 1, 480, 540)}, TimeModel.default(),
                                course_name_by_code={'BIO': 'Biología celular ' * 8})
        dialog = GridSessionDetailsDialog(viewer, ('BIO-G1',))
    try:
        if large:
            dialog.setStyleSheet('QWidget { font-size: 20pt; }')
        dialog.show()
        dialog.activateWindow()
        buttons = [b for box in dialog.findChildren(QDialogButtonBox) for b in box.buttons()]
        if kind == 'help':
            buttons.append(dialog.copy_button)
        for size in (QSize(460, 420), QSize(920, 650), QSize(460, 420)):
            dialog.resize(size)
            settle(dialog)
            assert dialog.size() == size
            for button in buttons:
                button.setFocus(Qt.FocusReason.TabFocusReason)
                settle(dialog)
                assert button.hasFocus()
                assert_fresh_button_size(button)
                assert_footer(dialog)
            if kind == 'help':
                assert dialog.scroll.horizontalScrollBar().maximum() == 0
                assert dialog.scroll.viewport().height() >= 200
    finally:
        dialog.reject()
        if viewer is not None:
            viewer.close()


@pytest.mark.parametrize('client', ['opencode', 'claude', 'chatgpt', 'chatgpt_desktop'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('backwards', [False, True], ids=['Tab', 'Shift-Tab'])
def test_help_keyboard_reveals_controls_and_links(presentation, client, locale, backwards):
    language_manager().set_language(locale, persist=False)
    dialog = McpClientHelp(COMMAND, permission_enabled=False, pending_permission=True)
    dialog.setStyleSheet('QWidget { font-size: 20pt; }')
    dialog.client.setCurrentIndex(dialog.client.findData(client))
    dialog.resize(460, 420)
    dialog.show()
    dialog.activateWindow()
    settle(dialog)
    close = dialog.buttons.button(QDialogButtonBox.StandardButton.Close)
    dialog.client.setFocus()
    seen = []
    try:
        for _ in range(24):
            QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab,
                           Qt.KeyboardModifier.ShiftModifier if backwards else Qt.KeyboardModifier.NoModifier)
            settle(dialog)
            focused = QApplication.focusWidget()
            if focused is dialog.client:
                break
            seen.append(focused)
            if dialog.scroll.widget().isAncestorOf(focused):
                viewport = dialog.scroll.viewport()
                center = focused.mapTo(viewport, focused.rect().center())
                assert viewport.rect().contains(center), (type(focused).__name__, center)
                if focused.height() <= viewport.height():
                    assert viewport.rect().contains(focused.rect().translated(
                        focused.mapTo(viewport, focused.rect().topLeft())))
        else:
            pytest.fail('Help keyboard did not return to the client selector')
        expected = [dialog.permission_status, dialog.instructions, dialog.source, close]
        if client != 'chatgpt':
            expected += [dialog.configuration, dialog.copy_button]
        assert set(expected) <= set(seen)
        assert dialog.copy_status not in seen  # Empty feedback is not a tab stop.
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        assert not dialog.isVisible()
    finally:
        dialog.reject()


def test_help_copy_selection_and_live_reflow_preserve_native_behavior(presentation):
    dialog = McpClientHelp(COMMAND, permission_enabled=True)
    dialog.setStyleSheet('QWidget { font-size: 20pt; }')
    dialog.resize(460, 420)
    dialog.show()
    dialog.activateWindow()
    try:
        for client in ('opencode', 'claude', 'opencode'):
            dialog.client.setCurrentIndex(dialog.client.findData(client))
            for locale, size in [('en', QSize(460, 420)), ('es', QSize(1000, 700)), ('en', QSize(460, 420))]:
                language_manager().set_language(locale, persist=False)
                dialog.resize(size)
                settle(dialog)
                expected = client_configuration(client, COMMAND)
                assert dialog.configuration.toPlainText() == expected
                dialog.configuration.setFocus()
                QTest.keyClick(dialog.configuration, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
                selected = dialog.configuration.textCursor().selectedText()
                assert selected.replace('\u2029', '\n') == expected
                QTest.keyClick(dialog.configuration, Qt.Key.Key_Tab)
                settle(dialog)
                assert dialog.copy_button.hasFocus()
                QTest.keyClick(dialog.copy_button, Qt.Key.Key_Space)
                settle(dialog)
                assert QApplication.clipboard().text() == expected
                assert dialog.copy_status.text()
                QTest.keyClick(dialog.copy_button, Qt.Key.Key_Tab)
                settle(dialog)
                assert dialog.copy_status.hasFocus()
                assert dialog.configuration.textCursor().selectedText() == selected
                assert dialog.scroll.horizontalScrollBar().maximum() == 0
                assert_footer(dialog)
        close = dialog.buttons.button(QDialogButtonBox.StandardButton.Close)
        close.setFocus()
        QTest.keyClick(close, Qt.Key.Key_Space)
        assert not dialog.isVisible()
    finally:
        dialog.reject()


@pytest.mark.parametrize('backwards', [False, True], ids=['Tab', 'Shift-Tab'])
def test_native_link_boundary_keeps_distinct_anchors_and_exit(presentation, backwards):
    from PyQt6.QtWidgets import QVBoxLayout
    from src.gui.i18n_widgets import QDialog, QPushButton, KeyboardLinkLabel
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    before = QPushButton('Before')
    links = KeyboardLinkLabel('<a href="https://example.com/first">First</a><br>'
                              '<a href="https://example.com/last">Last</a>')
    links.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    after = QPushButton('After')
    for widget in (before, links, after):
        layout.addWidget(widget)
    activated = []
    links.linkActivated.connect(activated.append)
    dialog.show()
    dialog.activateWindow()
    settle(dialog)
    start, end = (after, before) if backwards else (before, after)
    start.setFocus()
    seen = []
    try:
        for _ in range(8):
            QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab,
                           Qt.KeyboardModifier.ShiftModifier if backwards else Qt.KeyboardModifier.NoModifier)
            settle(dialog)
            if links.hasFocus() and links.selectedText() and links.selectedText() not in seen:
                seen.append(links.selectedText())
            if end.hasFocus():
                break
        assert end.hasFocus()
        assert seen == (['Last', 'First'] if backwards else ['First', 'Last'])
        assert not activated
    finally:
        dialog.reject()


def test_help_width_only_font_changes_refit_copy_and_preserve_configuration(presentation):
    dialog = McpClientHelp(COMMAND, permission_enabled=True)
    dialog.resize(460, 420)
    dialog.show()
    dialog.activateWindow()
    try:
        for stretch, size in [(180, 20), (100, 10), (180, 20)]:
            font = dialog.font()
            font.setPointSize(size)
            font.setStretch(stretch)
            dialog.setFont(font)
            # The app's font QSS owns point size; stretching remains a native
            # width-only change and must not require a changed window size.
            dialog.setStyleSheet(f'QWidget {{ font-size: {size}pt; }}')
            settle(dialog)
            dialog.copy_button.setFocus()
            settle(dialog)
            assert dialog.size() == QSize(460, 420)
            assert dialog.scroll.horizontalScrollBar().maximum() == 0
            assert_fresh_button_size(dialog.copy_button)
            assert_footer(dialog)
            assert dialog.configuration.toPlainText() == client_configuration('opencode', COMMAND)
    finally:
        dialog.reject()


def test_responsive_focus_reservations_preserve_caller_minima_and_can_shrink(presentation):
    from PyQt6.QtWidgets import QVBoxLayout
    from src.gui.i18n_widgets import QDialog, ResponsiveDialogButtonBox
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    footer = ResponsiveDialogButtonBox(QDialogButtonBox.StandardButton.Save |
                                       QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(footer)
    dialog.resize(460, 200)
    dialog.show()
    dialog.activateWindow()
    settle(dialog)
    try:
        dialog.setStyleSheet('QWidget { font-size: 20pt; }')
        settle(dialog)
        large = [b.minimumHeight() for b in footer.buttons()]
        dialog.setStyleSheet('QWidget { font-size: 10pt; }')
        settle(dialog)
        assert all(b.minimumHeight() < height for b, height in zip(footer.buttons(), large))
        for button in footer.buttons():
            button.setMinimumSize(250, 65)
        settle(dialog)
        assert footer.orientation() == Qt.Orientation.Vertical
        assert all(b.minimumSize() == QSize(250, 65) for b in footer.buttons())
        assert_footer(dialog)
        for button in footer.buttons():
            button.setMinimumSize(0, 0)
        settle(dialog)
        assert footer.orientation() == Qt.Orientation.Horizontal
        assert all(b.minimumHeight() < 65 and b.minimumWidth() < 250 for b in footer.buttons())
        assert_footer(dialog)
    finally:
        dialog.reject()
