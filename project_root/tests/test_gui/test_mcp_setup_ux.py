"""Native MCP setup keeps progress, permission and client steps distinct."""
import sys
import re
import time

import pytest
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QScrollArea

from src.gui.i18n import language_manager
from src.gui.main_window import MainWindow
from src.gui.mcp_availability import McpAvailabilityProbe
from src.gui.mcp_client_help import McpClientHelp, client_configuration
from src.gui.settings_dialog import SettingsDialog
from src.infrastructure.session_repository import SessionRepository


def caption_preserved_across_soft_breaks(display, source):
    # A new display line may start in the same source word or after original
    # whitespace. Spaces *inside* each line remain exact and cannot disappear.
    pattern = r'\s*'.join(re.escape(line) for line in display.split('\n'))
    return re.fullmatch(pattern, source) is not None


def settings_width_for_unwrapped_captions(dialog):
    """Measure full native captions at the current font/style, not a pixel guess."""
    scroll = dialog.findChild(QScrollArea)
    full_width = 0
    for control in dialog._responsive_actions.controls:
        source = control._messages['setText'][1][0].render()
        probe = type(control)(source, dialog)
        probe.setObjectName(control.objectName())
        probe.setFont(control.font())
        probe.ensurePolished()
        full_width = max(full_width, probe.minimumSizeHint().width())
        probe.deleteLater()
    margins = scroll.widget().layout().contentsMargins()
    gutters = dialog.width() - scroll.viewport().width() + margins.left() + margins.right()
    # Retain room for the focus border and the wrapping safety inset.
    return max(900, full_width + gutters + 16)


def settings_layout_snapshot(dialog):
    scroll = dialog.findChild(QScrollArea)
    return {
        'dialog': (dialog.width(), dialog.height()),
        'viewport': (scroll.viewport().width(), scroll.viewport().height()),
        'content': (scroll.widget().width(), scroll.widget().height()),
        'content_minimum': scroll.widget().minimumSizeHint().width(),
        'horizontal_maximum': scroll.horizontalScrollBar().maximum(),
        'timer_active': dialog._responsive_actions.timer.isActive(),
        'footer_timer_active': dialog.buttons._metric_timer.isActive(),
        'footer': (dialog.buttons.width(), dialog.buttons.height(),
                   dialog.buttons.minimumSizeHint().width(), dialog.buttons.orientation().name),
        'actions': [(button.text(), button.minimumSizeHint().width(),
                     button.minimumSizeHint().height(), button.width(), button.height())
                    for button in dialog._responsive_actions.controls],
    }


def settle_settings_layout(dialog, timeout=2):
    """Observe stable native layout; never force wrapping or change dimensions."""
    deadline = time.monotonic() + timeout
    previous = None
    stable_turns = 0
    while time.monotonic() < deadline:
        QApplication.processEvents()
        snapshot = settings_layout_snapshot(dialog)
        stable_turns = (stable_turns + 1 if snapshot == previous
                        and not snapshot['timer_active'] and not snapshot['footer_timer_active'] else 0)
        if stable_turns >= 2:
            return snapshot
        previous = snapshot
        # processEvents alone does not promise delivery of newly queued native
        # layout requests or zero timers. Yield a real bounded Qt event turn.
        QTest.qWait(1)
    pytest.fail(f'Native Settings layout did not settle: {settings_layout_snapshot(dialog)!r}')


@pytest.fixture
def window(tmp_path):
    q = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    w = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False, feature_settings=q)
    yield w
    w.close()


@pytest.fixture
def english():
    manager = language_manager()
    original = manager.language
    manager.set_language('en', persist=False)
    yield
    manager.set_language(original, persist=False)


def test_saved_and_pending_permission_are_distinct(window, monkeypatch, english):
    monkeypatch.setattr(McpAvailabilityProbe, 'start', lambda self: self.finished.emit('available'))
    dialog = SettingsDialog(window)
    assert 'Saved permission: off' in dialog.mcp_permission_label.text()
    dialog.controls['mcp_server'].setChecked(True)
    assert 'Unsaved change' in dialog.mcp_permission_label.text()
    assert not window._features.enabled('mcp_server')
    dialog.accept()
    dialog = SettingsDialog(window)
    assert 'Saved permission: on' in dialog.mcp_permission_label.text()
    dialog.controls['mcp_server'].setChecked(False)
    assert 'Permission stays on' in dialog.mcp_permission_label.text()
    assert 'pending results are discarded' in dialog.mcp_permission_label.text()
    assert window._features.enabled('mcp_server')
    dialog.reject()
    assert window._features.enabled('mcp_server')


def test_ready_state_avoids_redundant_preparation_but_can_recheck(window, english):
    dialog = SettingsDialog(window)
    dialog._show_mcp_status('prepared')
    assert not dialog.mcp_prepare_button.isEnabled()
    assert 'already available' in dialog.mcp_prepare_button.toolTip()
    assert dialog.mcp_check_button.isEnabled()
    assert dialog.mcp_help_button.isEnabled()
    assert not dialog.controls['mcp_server'].isChecked()
    dialog._show_mcp_status('missing_component')
    assert dialog.mcp_prepare_button.isEnabled()
    assert not dialog.mcp_prepare_button.toolTip()
    dialog.reject()


def test_check_can_be_cancelled_without_closing_settings(window, monkeypatch, english):
    dialog = SettingsDialog(window)
    dialog.show()
    original = dialog.mcp_probe.process.start
    monkeypatch.setattr(dialog.mcp_probe.process, 'start', lambda *args: original(sys.executable, ['-c', 'import time; time.sleep(10)']))
    dialog._check_mcp()
    assert dialog.mcp_cancel_button.isVisible()
    assert dialog.section_selector.currentData() == 'mcp'
    assert not dialog.section_selector.isEnabled()
    assert dialog.mcp_cancel_button.text() == 'Cancel MCP check'
    dialog.mcp_cancel_button.click()
    deadline = time.monotonic() + 2
    while dialog.mcp_probe.active and time.monotonic() < deadline:
        QApplication.processEvents()
    assert not dialog.mcp_probe.active
    assert dialog.isVisible() and dialog.mcp_status == 'cancelled'
    assert dialog.mcp_cancel_button.isHidden()
    assert dialog.section_selector.isEnabled()
    assert dialog.mcp_check_button.isEnabled()
    assert not window._features.path.exists()
    dialog.reject()


@pytest.mark.parametrize('saved,pending,phrase', [(True, False, 'Saved local permission: on'),
                                                  (False, False, 'Before connecting'),
                                                  (False, True, 'unsaved permission change'),
                                                  (True, True, 'unsaved permission change')])
def test_guide_does_not_mistake_pending_permission_for_authorization(english, saved, pending, phrase):
    dialog = McpClientHelp(None, permission_enabled=saved, pending_permission=pending)
    assert phrase in dialog.permission_status.text()
    assert not dialog.copy_button.isEnabled()
    assert not dialog.configuration.toPlainText()
    dialog.reject()


@pytest.mark.parametrize('locale', ['es', 'en'])
def test_guide_small_window_keeps_close_accessible_and_code_tabbable(locale):
    manager = language_manager()
    original = manager.language
    manager.set_language(locale, persist=False)
    command = [r'C:\Users\Renée Name\SORTH\SORTH-MCP.exe', '--serve']
    dialog = McpClientHelp(command, permission_enabled=True)
    try:
        dialog.resize(460, 420)
        dialog.show()
        QApplication.processEvents()
        assert dialog.size().width() <= 460
        assert dialog.size().height() <= 420
        close = dialog.buttons.button(QDialogButtonBox.StandardButton.Close)
        assert dialog.rect().contains(close.mapTo(dialog, close.rect().center()))
        assert dialog.scroll.verticalScrollBar().maximum() > 0
        assert dialog.scroll.horizontalScrollBar().maximum() == 0
        dialog.scroll.ensureWidgetVisible(dialog.configuration)
        dialog.configuration.setFocus()
        QTest.keyClick(dialog.configuration, Qt.Key.Key_Tab)
        assert QApplication.focusWidget() == dialog.copy_button
        QTest.keyClick(dialog.copy_button, Qt.Key.Key_Space)
        assert QApplication.clipboard().text() == client_configuration('opencode', command)
        assert dialog.copy_status.text()
        dialog.client.setCurrentIndex(2)
        assert dialog.configuration.isHidden() and dialog.copy_button.isHidden()
        assert 'HTTPS' in dialog.instructions.text()
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        assert not dialog.isVisible()
    finally:
        dialog.reject()
        manager.set_language(original, persist=False)


def test_settings_small_window_reaches_guide_and_keeps_save_visible(window):
    dialog = SettingsDialog(window)
    dialog.resize(460, 420)
    dialog.show()
    QApplication.processEvents()
    snapshot = settle_settings_layout(dialog)
    assert dialog.width() <= 460 and dialog.height() <= 420, snapshot
    scroll = dialog.findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum() == 0, snapshot
    scroll.ensureWidgetVisible(dialog.mcp_help_button)
    assert scroll.viewport().rect().contains(dialog.mcp_help_button.mapTo(scroll.viewport(), dialog.mcp_help_button.rect().center()))
    save = dialog.buttons.button(QDialogButtonBox.StandardButton.Save)
    assert dialog.rect().contains(save.mapTo(dialog, save.rect().center()))
    dialog.reject()


def test_enter_on_check_runs_check_without_saving_or_closing(window, monkeypatch):
    calls = []
    def check(probe):
        calls.append(True)
        probe.finished.emit('available')
    monkeypatch.setattr(McpAvailabilityProbe, 'start', check)
    dialog = SettingsDialog(window)
    dialog.show()
    QApplication.processEvents()
    dialog.mcp_check_button.setFocus()
    QTest.keyClick(dialog.mcp_check_button, Qt.Key.Key_Return)
    assert calls == [True]
    assert dialog.isVisible()
    assert not window._features.path.exists()
    dialog.reject()


def test_external_revocation_before_guide_preserves_save_conflict_and_other_edits(window, monkeypatch, english):
    from src.application.mcp_preferences import enabled, set_enabled
    from src.gui import settings_dialog
    from PyQt6.QtWidgets import QMessageBox
    values = window._features.values()
    values['mcp_server'] = True
    window._features.save(values)
    dialog = SettingsDialog(window)
    dialog.controls['import_diff_preview'].setChecked(True)
    original_record = window._features._record.copy()
    set_enabled(window._features.path, False)
    seen = []
    class Guide:
        def __init__(self, command, parent, **kwargs):
            seen.append(kwargs)
        def exec(self):
            return 0
    monkeypatch.setattr(settings_dialog, 'McpClientHelp', Guide)
    dialog._show_mcp_help()
    assert seen == [{'permission_enabled': False, 'pending_permission': True}]
    assert window._features._record == original_record
    assert dialog.controls['mcp_server'].isChecked()
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    dialog.accept()
    assert warnings and not enabled(window._features.path)
    assert not dialog.controls['mcp_server'].isChecked()
    assert dialog.controls['import_diff_preview'].isChecked()
    assert 'Saved permission: off' in dialog.mcp_permission_label.text()
    dialog.accept()
    assert not enabled(window._features.path)
    assert window._features.enabled('import_diff_preview')


def test_enable_save_waits_for_check_but_disabling_never_requires_success(window, monkeypatch, english):
    from src.application.mcp_preferences import enabled
    from PyQt6.QtWidgets import QMessageBox
    dialog = SettingsDialog(window)
    original = dialog.mcp_probe.process.start
    monkeypatch.setattr(dialog.mcp_probe.process, 'start', lambda *args: original(sys.executable, ['-c', 'import time; time.sleep(10)']))
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: warnings.append(args))
    dialog._show_mcp_status('prepared')
    dialog.controls['mcp_server'].setChecked(True)
    save = dialog.buttons.button(QDialogButtonBox.StandardButton.Save)
    assert dialog.mcp_status == 'checking' and not save.isEnabled()
    assert 'Wait for the MCP check' in save.toolTip()
    save.click()
    dialog.accept()
    assert not warnings and not enabled(window._features.path)
    dialog.controls['mcp_server'].setChecked(False)
    assert save.isEnabled()  # OFF does not depend on a successful health check.
    dialog.accept()
    assert not enabled(window._features.path)
    assert not dialog.mcp_probe.active


def test_read_only_status_observes_external_permission_without_changing_baseline(window, english):
    from src.application.mcp_preferences import set_enabled
    values = window._features.values()
    values['mcp_server'] = True
    window._features.save(values)
    dialog = SettingsDialog(window)
    baseline = window._features._record.copy()
    set_enabled(window._features.path, False)
    dialog._refresh_mcp_permission()
    assert 'Unsaved change' in dialog.mcp_permission_label.text()
    assert window._features._record == baseline
    dialog.reject()


def test_saved_permission_can_be_revoked_while_health_check_is_running(window, monkeypatch):
    from src.application.mcp_preferences import enabled
    values = window._features.values()
    values['mcp_server'] = True
    window._features.save(values)
    dialog = SettingsDialog(window)
    original = dialog.mcp_probe.process.start
    monkeypatch.setattr(dialog.mcp_probe.process, 'start', lambda *args: original(sys.executable, ['-c', 'import time; time.sleep(10)']))
    dialog._check_mcp()
    assert dialog.mcp_probe.active and enabled(window._features.path)
    dialog.controls['mcp_server'].setChecked(False)
    assert dialog.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled()
    dialog.accept()
    assert not enabled(window._features.path)
    assert not dialog.mcp_probe.active


@pytest.mark.parametrize('style_name', [None, 'Fusion', 'Windows'], ids=['native-default', 'Fusion', 'Windows'])
@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('expanded_metrics', [False, True], ids=['normal-font', 'expanded-font'])
def test_settings_native_action_labels_reflow_without_horizontal_overflow(window, style_name, locale, expanded_metrics):
    from PyQt6.QtWidgets import QStyleFactory
    from src.gui.i18n import msg
    app = QApplication.instance()
    original_style = app.style().objectName()
    manager = language_manager()
    original_language = manager.language
    if style_name is not None and style_name not in QStyleFactory.keys():
        pytest.skip(f'{style_name} is unavailable')
    if style_name is not None:
        app.setStyle(style_name)
    manager.set_language(locale, persist=False)
    dialog = SettingsDialog(window)
    try:
        # Exercise wider native font metrics without depending on a CI machine's
        # installed fonts or DPI. The application itself never shrinks its text.
        if expanded_metrics:
            dialog.setStyleSheet('QPushButton, QCheckBox { font-size: 20pt; }')
        dialog.recovery_label.show()
        dialog.recover_button.show()
        dialog.mcp_cancel_button.setText(msg('Cancelar verificación MCP'))
        dialog.mcp_cancel_button.show()
        dialog.resize(460, 420)
        dialog.show()
        QApplication.processEvents()
        scroll = dialog.findChild(QScrollArea)
        controls = dialog._responsive_actions.controls

        def inspect_geometry():
            snapshot = settle_settings_layout(dialog)
            assert dialog.width() == 460 and dialog.height() == 420, snapshot
            assert scroll.horizontalScrollBar().maximum() == 0, snapshot
            for button in controls:
                source = button._messages['setText'][1][0]
                assert caption_preserved_across_soft_breaks(button.text(), source.render()), (button.text(), source.render())
                assert button.accessibleName() == source.render()
                assert button.width() >= button.minimumSizeHint().width()
                assert button.height() >= button.minimumSizeHint().height()
            for action in dialog.buttons.buttons():
                assert action.width() >= action.minimumSizeHint().width(), snapshot
                assert action.height() >= action.minimumSizeHint().height(), snapshot
                assert dialog.rect().contains(action.mapTo(dialog, action.rect().topLeft())), snapshot
                assert dialog.rect().contains(action.mapTo(dialog, action.rect().bottomRight())), snapshot

        inspect_geometry()
        if expanded_metrics:
            assert caption_preserved_across_soft_breaks(dialog.calendar_button.text(),
                                                        dialog.calendar_button._messages['setText'][1][0].render())
        checkbox = dialog.controls['project_scenarios']
        checkbox.setFocus()
        QTest.keyClick(checkbox, Qt.Key.Key_Space)
        assert checkbox.isChecked()
        # Retranslation keeps the original Message, checked state and focus.
        manager.set_language('en' if locale == 'es' else 'es', persist=False)
        QApplication.processEvents()
        inspect_geometry()
        assert checkbox.isChecked() and checkbox.hasFocus()
        dialog.resize(900, 420)
        snapshot = settle_settings_layout(dialog)
        assert snapshot['horizontal_maximum'] == 0, snapshot
        assert caption_preserved_across_soft_breaks(dialog.calendar_button.text(),
                                                    dialog.calendar_button._messages['setText'][1][0].render())
        dialog.resize(settings_width_for_unwrapped_captions(dialog), 420)
        settle_settings_layout(dialog)
        assert dialog.calendar_button.text() == dialog.calendar_button._messages['setText'][1][0].render()
        dialog.resize(460, 420)
        QApplication.processEvents()
        inspect_geometry()
    finally:
        dialog.reject()
        app.setStyle(original_style)
        manager.set_language(original_language, persist=False)


@pytest.mark.parametrize('kind', ['QPushButton', 'QCheckBox'])
def test_wrapped_native_captions_keep_supplementary_unicode_characters(kind):
    from src.gui import i18n_widgets
    from src.gui.i18n import msg
    caption = 'Preparar 🚀 conexión del cliente 𠮷 y verificar todos los componentes'
    button = getattr(i18n_widgets, kind)(msg(caption))
    button.wrapPresentationText(120)
    assert '\n' in button.text()
    assert caption_preserved_across_soft_breaks(button.text(), caption)
    assert button.accessibleName() == caption
    assert button._messages['setText'][1][0].render() == caption
    button.wrapPresentationText(2000)
    assert button.text() == caption
    button.deleteLater()



def test_settings_show_and_resize_reflow_without_zero_timer_delivery(window, monkeypatch):
    from src.gui.i18n_widgets import ResponsiveActionLabels
    monkeypatch.setattr(ResponsiveActionLabels, '_schedule', lambda *args: None)
    dialog = SettingsDialog(window)
    try:
        dialog.setStyleSheet('QPushButton, QCheckBox { font-size: 20pt; }')
        dialog.resize(460, 420)
        dialog.show()
        snapshot = settle_settings_layout(dialog)
        assert not dialog._responsive_actions.timer.isActive()
        assert snapshot['horizontal_maximum'] == 0, snapshot
        assert '\n' in dialog.calendar_button.text()
        dialog.resize(900, 420)
        snapshot = settle_settings_layout(dialog)
        assert snapshot['horizontal_maximum'] == 0, snapshot
        assert caption_preserved_across_soft_breaks(dialog.calendar_button.text(),
                                                    dialog.calendar_button._messages['setText'][1][0].render())
        dialog.resize(settings_width_for_unwrapped_captions(dialog), 420)
        settle_settings_layout(dialog)
        assert dialog.calendar_button.text() == dialog.calendar_button._messages['setText'][1][0].render()
        dialog.resize(460, 420)
        snapshot = settle_settings_layout(dialog)
        assert snapshot['horizontal_maximum'] == 0, snapshot
    finally:
        dialog.reject()


def test_settings_footer_stacks_without_enlarging_or_clipping(window):
    dialog = SettingsDialog(window)
    try:
        # Isolate the native footer's width constraint from content wrapping.
        for action in dialog.buttons.buttons():
            action.setMinimumWidth(250)
        dialog.resize(460, 420)
        dialog.show()
        snapshot = settle_settings_layout(dialog)
        assert dialog.width() == 460 and dialog.height() == 420, snapshot
        assert dialog.buttons.orientation() == Qt.Orientation.Vertical, snapshot
        for action in dialog.buttons.buttons():
            assert action.width() >= action.minimumSizeHint().width(), snapshot
            assert dialog.rect().contains(action.mapTo(dialog, action.rect().topLeft())), snapshot
            assert dialog.rect().contains(action.mapTo(dialog, action.rect().bottomRight())), snapshot
        dialog.resize(900, 420)
        snapshot = settle_settings_layout(dialog)
        assert dialog.buttons.orientation() == Qt.Orientation.Horizontal, snapshot
    finally:
        dialog.reject()



def test_settings_footer_reflows_on_width_only_font_metric_change(window):
    dialog = SettingsDialog(window)
    try:
        dialog.resize(460, 420)
        dialog.show()
        settle_settings_layout(dialog)
        from PyQt6.QtGui import QFont
        available = dialog.buttons.width()
        original_heights = [action.minimumSizeHint().height() for action in dialog.buttons.buttons()]
        for action in dialog.buttons.buttons():
            font = action.font()
            text_width = action.fontMetrics().size(Qt.TextFlag.TextShowMnemonic, action.text()).width()
            chrome = max(0, action.minimumSizeHint().width() - text_width)
            # Make each native action about 60% of the available row. This
            # deterministically crosses the horizontal threshold while each
            # complete caption still fits when stacked, without changing height.
            target_text_width = available * .6 - chrome
            spacing = max(0, (target_text_width - text_width) / max(1, len(action.text()))) + 2
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
            action.setFont(font)
        snapshot = settle_settings_layout(dialog)
        assert sum(action.minimumSizeHint().width() for action in dialog.buttons.buttons()) > available, snapshot
        assert [action.minimumSizeHint().height() for action in dialog.buttons.buttons()] == original_heights, snapshot
        assert dialog.width() == 460 and dialog.height() == 420, snapshot
        assert dialog.buttons.orientation() == Qt.Orientation.Vertical, snapshot
        for action in dialog.buttons.buttons():
            assert action.width() >= action.minimumSizeHint().width(), snapshot
            assert dialog.rect().contains(action.mapTo(dialog, action.rect().bottomRight())), snapshot
    finally:
        dialog.reject()


def test_native_reflow_survives_scroll_area_disposal():
    import subprocess
    script = """
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWidgets import QApplication, QWidget, QScrollArea, QVBoxLayout
from src.gui.i18n import msg
from src.gui.i18n_widgets import QPushButton, ResponsiveActionLabels
app = QApplication([])
root = QWidget()
outer = QVBoxLayout(root)
scroll = QScrollArea()
content = QWidget()
body = QVBoxLayout(content)
button = QPushButton(msg('Preparar complemento MCP'))
body.addWidget(button)
scroll.setWidget(content)
outer.addWidget(scroll)
helper = ResponsiveActionLabels(scroll, [button], root)
root.show()
app.processEvents()
scroll.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
app.processEvents()
root.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
app.processEvents()
print('disposed safely')
"""
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert 'disposed safely' in result.stdout



def test_footer_never_queries_native_metrics_during_global_style_replacement(window, monkeypatch):
    from PyQt6.QtWidgets import QStyleFactory
    from src.gui.i18n_widgets import ResponsiveDialogButtonBox
    app = QApplication.instance()
    original_style = app.style().objectName()
    dialog = SettingsDialog(window)
    dialog.resize(460, 420)
    dialog.show()
    settle_settings_layout(dialog)
    state = {'changing': False}
    unsafe_calls = []
    original_fit = ResponsiveDialogButtonBox._fit_actions

    def checked_fit(box):
        if state['changing']:
            # Record instead of raising through a Qt virtual call or querying
            # native buttons while the old style is being deleted.
            unsafe_calls.append('metrics requested during QApplication.setStyle')
            return
        original_fit(box)

    monkeypatch.setattr(ResponsiveDialogButtonBox, '_fit_actions', checked_fit)
    try:
        styles = [style for style in ('Windows', 'Fusion') if style in QStyleFactory.keys()]
        for style in [*styles, original_style, *styles, original_style]:
            state['changing'] = True
            try:
                app.setStyle(style)
            finally:
                state['changing'] = False
            snapshot = settle_settings_layout(dialog)
            assert snapshot['horizontal_maximum'] == 0, snapshot
            assert not unsafe_calls, unsafe_calls
    finally:
        dialog.reject()
        state['changing'] = True
        try:
            app.setStyle(original_style)
        finally:
            state['changing'] = False



@pytest.mark.parametrize('display,source,valid', [
    ('Verificar disponibilida\nd local de MCP', 'Verificar disponibilidad local de MCP', True),
    ('Save settings\nand edit calendar', 'Save settings and edit calendar', True),
    ('Preparar 🚀\nconexión 𠮷', 'Preparar 🚀 conexión 𠮷', True),
    ('sinpermiso', 'sin permiso', False),
    ('sin permiso', 'sin  permiso', False),
    ('sin  permiso', 'sin permiso', False),
    ('preparar cli\nte', 'preparar cliente', False),
    ('Preparar conexión 𠮷', 'Preparar 🚀 conexión 𠮷', False),
    ('preparar MCP', 'MCP preparar', False),
])
def test_caption_validation_distinguishes_soft_breaks_from_lost_content(display, source, valid):
    assert caption_preserved_across_soft_breaks(display, source) is valid
