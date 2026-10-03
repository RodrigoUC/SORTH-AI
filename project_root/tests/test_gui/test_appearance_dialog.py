"""Native preview, local import, explicit commit and compact keyboard contracts."""
import json
from pathlib import Path

import pytest
from PyQt6.QtCore import QCoreApplication, QEvent, QSettings, QSize, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog, QStyleFactory, QWidget

from src.gui import theme
from src.gui.appearance_dialog import AppearanceDialog
from src.gui.i18n import language_manager, msg
from src.gui.main_window import MainWindow
from src.gui.settings_dialog import SettingsDialog
from src.gui.theme_contract import MAX_THEME_BYTES
from src.gui.theme_preferences import ThemePersistenceError, ThemePreferences
from src.infrastructure.session_repository import SessionRepository
from tests.test_gui.test_mcp_setup_ux import settle_settings_layout


@pytest.fixture
def manager(tmp_path):
    app = QApplication.instance()
    previous = getattr(app, '_sorth_theme_manager', None)
    runtime = theme.ThemeManager(app, ThemePreferences(tmp_path / 'appearance.json'))
    app._sorth_theme_manager = runtime
    yield runtime
    for widget in app.topLevelWidgets():
        if isinstance(widget, AppearanceDialog):
            widget.close()
            widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    runtime._apply(theme.builtin_themes()[0].spec)
    app._sorth_theme_manager = previous


@pytest.fixture
def window(tmp_path, manager):
    settings = QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat)
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')),
                        restore_session=False, feature_settings=settings)
    yield window
    window.close()


def show(manager, parent=None):
    dialog = AppearanceDialog(parent, manager=manager)
    dialog.show()
    settle_settings_layout(dialog)
    return dialog


def record_appearance_geometry(dialog, case):
    """Retain untruncated native control/font diagnostics in CI artifacts."""
    from tests.test_gui.test_mcp_setup_ux import settings_layout_snapshot
    snapshot = settings_layout_snapshot(dialog)
    snapshot['widgets'] = [
        {'class': type(widget).__name__, 'name': widget.objectName(),
         'text': widget.text() if hasattr(widget, 'text') else '',
         'size': (widget.width(), widget.height()),
         'minimum': (widget.minimumSizeHint().width(), widget.minimumSizeHint().height()),
         'font': widget.font().toString(), 'dpi': widget.logicalDpiX(),
         'accessible_name': widget.accessibleName()}
        for widget in dialog.findChildren(QWidget) if widget.isVisible()
    ]
    report_dir = Path(__file__).resolve().parents[2] / 'build' / 'reports'
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f'appearance-geometry-{case}.json').write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    return snapshot


def select(dialog, key):
    dialog.selector.setCurrentIndex(dialog.selector.findData(key))
    settle_settings_layout(dialog)


def write_theme(path, data=None):
    if data is None:
        data = theme.builtin_themes()[1].spec.to_dict()
        data['name'] = 'Mi tema & "local"'
        data['description'] = 'A' * 240
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return path


def test_selection_only_previews_and_cancel_reopens_committed_theme(manager):
    dialog = show(manager)
    previous_stylesheet = QApplication.instance().styleSheet()
    select(dialog, 'nocturno')
    assert dialog.candidate.mode == 'dark'
    assert manager.current_key == 'original'
    assert theme.current_theme() == manager.current
    assert QApplication.instance().styleSheet() == previous_stylesheet
    assert dialog.preview.palette().color(dialog.preview.backgroundRole()).name() == dialog.candidate.colors['canvas'].lower()
    assert not manager.preferences.path.exists()
    dialog.reject()
    reopened = show(manager)
    assert reopened.candidate_key == 'original'
    assert not manager.preferences.path.exists()
    reopened.reject()


def test_custom_apply_owns_copy_after_source_deletion_and_reopen(manager, tmp_path):
    source = write_theme(tmp_path / 'custom.sorth-theme.json')
    dialog = show(manager)
    assert dialog.import_file(source)
    assert not manager.preferences.path.exists()
    source.unlink()
    dialog.apply_candidate()
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert manager.current_key == 'custom'
    assert manager.preferences.path.exists()
    loaded = ThemePreferences(manager.preferences.path)
    assert loaded.current.to_dict() == manager.current.to_dict()
    assert loaded.current.name == 'Mi tema & "local"'
    reopened = show(manager)
    assert reopened.candidate_key == 'custom'
    assert reopened.selector.currentText() == loaded.current.name
    assert reopened.metadata.textFormat() == Qt.TextFormat.PlainText
    reopened.reject()


@pytest.mark.parametrize('fault, reason', [
    ('missing', 'missing required'), ('version', 'schema_version'),
    ('duplicate', 'duplicate JSON'), ('oversize', '16 KiB'),
    ('contrast', 'below'), ('html', 'plain text'), ('qss', 'unknown fields'),
    ('malformed', 'UTF-8 JSON'),
])
def test_invalid_import_is_selectable_plain_text_and_preserves_candidate(manager, tmp_path, fault, reason):
    dialog = show(manager)
    original = dialog.candidate.to_dict()
    data = theme.builtin_themes()[0].spec.to_dict()
    payload = None
    if fault == 'missing':
        del data['colors']
    elif fault == 'version':
        data['schema_version'] = 2
    elif fault == 'duplicate':
        payload = '{"schema_version":1,"schema_version":1}'
    elif fault == 'oversize':
        payload = ' ' * (MAX_THEME_BYTES + 1)
    elif fault == 'contrast':
        data['colors']['text'] = data['colors']['surface']
    elif fault == 'html':
        data['name'] = '<img src="https://invalid.example/pixel">'
    elif fault == 'qss':
        data['stylesheet'] = 'QWidget { image: url(https://invalid.example/pixel); }'
    elif fault == 'malformed':
        payload = '{'
    path = tmp_path / 'invalid.json'
    path.write_text(payload if payload is not None else json.dumps(data), encoding='utf-8')
    assert not dialog.import_file(path)
    assert dialog.candidate.to_dict() == original
    assert manager.current.to_dict() == original
    assert not manager.preferences.path.exists()
    assert reason in dialog.details.toPlainText()
    assert dialog.details.isReadOnly()
    assert dialog.details.tabChangesFocus()
    assert dialog.feedback.textFormat() == Qt.TextFormat.PlainText
    dialog.reject()


def test_apply_failure_never_accepts_or_claims_applied(manager, monkeypatch):
    dialog = show(manager)
    select(dialog, 'nocturno')
    before = manager.current.to_dict()
    def fail(*args, **kwargs):
        raise ThemePersistenceError('disk full <not markup>')
    monkeypatch.setattr(manager, 'save_and_apply', fail)
    dialog.apply_candidate()
    assert dialog.isVisible()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert manager.current.to_dict() == before
    assert not manager.preferences.path.exists()
    assert 'disk full <not markup>' == dialog.details.toPlainText()
    assert dialog.apply_button.isEnabled()
    assert dialog.feedback.text() == str(msg(
        'No se pudo aplicar el tema. El tema anterior sigue activo. Puedes volver a intentarlo.'))
    dialog.reject()


def test_restore_is_staged_and_requires_apply(manager):
    manager.save_and_apply(theme.builtin_themes()[1].spec, key='nocturno')
    before = manager.preferences.path.read_bytes()
    dialog = show(manager)
    dialog.restore_button.click()
    assert dialog.candidate_key == 'original'
    assert manager.current_key == 'nocturno'
    assert manager.preferences.path.read_bytes() == before
    dialog.reject()
    assert manager.current_key == 'nocturno'
    dialog = show(manager)
    dialog.restore_original()
    dialog.apply_candidate()
    assert manager.current_key == 'original'


def test_corrupt_record_requires_explicit_preserve_and_replace(tmp_path):
    path = tmp_path / 'broken.json'
    path.write_bytes(b'broken exact bytes')
    manager = theme.ThemeManager(QApplication.instance(), ThemePreferences(path))
    dialog = show(manager)
    assert dialog.recover.isVisible() and not dialog.recover.isChecked()
    assert not dialog.apply_button.isEnabled()
    dialog.apply_candidate()
    assert path.read_bytes() == b'broken exact bytes'
    dialog.recover.setChecked(True)
    dialog.apply_candidate()
    assert manager.preferences.last_backup_path.read_bytes() == b'broken exact bytes'
    assert ThemePreferences(path).recovery_issue is None


def test_import_file_picker_is_explicit_and_cancellation_writes_nothing(manager, monkeypatch, tmp_path):
    calls = []
    def picker(*args):
        calls.append(args)
        return '', ''
    monkeypatch.setattr('src.gui.appearance_dialog.QFileDialog.getOpenFileName', picker)
    dialog = show(manager)
    assert not calls
    dialog.import_button.click()
    assert len(calls) == 1
    assert not manager.preferences.path.exists()
    dialog.reject()


def test_custom_metadata_is_literal_across_languages_and_long_words_wrap(manager, tmp_path):
    language = language_manager()
    previous = language.language
    data = theme.builtin_themes()[0].spec.to_dict()
    data.update(name='Configuración', description='A' * 240)
    path = write_theme(tmp_path / 'literal.json', data)
    dialog = show(manager)
    try:
        assert dialog.import_file(path)
        dialog.resize(460, 420)
        for locale in ('es', 'en'):
            language.set_language(locale, persist=False)
            settle_settings_layout(dialog)
            assert dialog.selector.currentText() == 'Configuración'
            assert 'A' * 240 in dialog.metadata.text()
            assert dialog.scroll.horizontalScrollBar().maximum() == 0
            assert dialog.size() == QSize(460, 420)
    finally:
        dialog.reject()
        language.set_language(previous, persist=False)


@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('style', ['Fusion', 'Windows'])
@pytest.mark.parametrize('expanded', [False, True])
def test_compact_preview_footer_and_keyboard_reveal(manager, locale, style, expanded):
    app = QApplication.instance()
    previous_style = app.style().objectName()
    language = language_manager()
    previous_language = language.language
    if style not in QStyleFactory.keys():
        pytest.skip('native style is unavailable')
    app.setStyle(style)
    language.set_language(locale, persist=False)
    dialog = show(manager)
    try:
        select(dialog, 'nocturno')
        if expanded:
            fonts = 'QWidget { font-size: 20pt; }'
            dialog.setStyleSheet(dialog.styleSheet() + fonts)
            dialog.preview.setStyleSheet(dialog.preview.styleSheet() + fonts)
        dialog.resize(460, 420)
        settle_settings_layout(dialog)
        snapshot = record_appearance_geometry(dialog, f'compact-{style}-{locale}-{expanded}')
        assert dialog.size() == QSize(460, 420), snapshot
        assert dialog.scroll.horizontalScrollBar().maximum() == 0, snapshot
        assert dialog.scroll.viewport().height() > 100, snapshot
        for button in dialog.buttons.buttons():
            assert button.width() >= button.minimumSizeHint().width(), snapshot
            assert button.height() >= button.minimumSizeHint().height(), snapshot
            assert dialog.rect().contains(button.mapTo(dialog, button.rect().topLeft())), snapshot
            assert dialog.rect().contains(button.mapTo(dialog, button.rect().bottomRight())), snapshot
        for backwards in (False, True):
            seen = []
            dialog.selector.setFocus()
            modifier = Qt.KeyboardModifier.ShiftModifier if backwards else Qt.KeyboardModifier.NoModifier
            for _ in range(30):
                QTest.keyClick(app.focusWidget(), Qt.Key.Key_Tab, modifier)
                settle_settings_layout(dialog)
                focused = app.focusWidget()
                assert focused is not None and focused.isVisible()
                if focused is dialog.selector:
                    break
                seen.append(focused)
                if dialog.scroll.widget().isAncestorOf(focused):
                    assert dialog.scroll.viewport().rect().contains(
                        focused.mapTo(dialog.scroll.viewport(), focused.rect().center())), focused
            else:
                pytest.fail('Native tab traversal never returned to the theme selector')
            for control in (dialog.import_button, dialog.preview.input, dialog.preview.focus_button,
                            dialog.preview.primary, dialog.preview.table, dialog.preview.course,
                            dialog.restore_button, dialog.cancel_button, dialog.apply_button):
                assert control in seen
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        assert not dialog.isVisible()
        assert not manager.preferences.path.exists()
    finally:
        dialog.reject()
        app.setStyle(previous_style)
        language.set_language(previous_language, persist=False)


def test_general_entry_keeps_theme_commit_separate_from_optional_preferences(window, manager, monkeypatch):
    settings = SettingsDialog(window)
    settings.show()
    settle_settings_layout(settings)
    assert settings.appearance_button.isVisible()
    settings.controls['undo_redo'].setChecked(True)
    before = window._features.path.read_bytes() if window._features.path.exists() else None
    def apply_dark(dialog):
        select(dialog, 'nocturno')
        dialog.apply_candidate()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(AppearanceDialog, 'exec', apply_dark)
    settings.appearance_button.click()
    assert manager.current_key == 'nocturno'
    assert settings.controls['undo_redo'].isChecked()
    settings.reject()
    assert not window._features.enabled('undo_redo')
    assert (window._features.path.read_bytes() if window._features.path.exists() else None) == before
    assert manager.current_key == 'nocturno'


def test_reopening_after_external_change_refreshes_review_without_live_apply(manager):
    dialog = show(manager)
    external = ThemePreferences(manager.preferences.path)
    external.save(theme.builtin_themes()[1].spec, key='nocturno')
    select(dialog, 'high_contrast')
    dialog.apply_candidate()
    assert dialog.isVisible()
    assert manager.current_key == 'original'
    assert 'changed externally' in dialog.details.toPlainText()
    dialog.reject()
    reopened = show(manager)
    assert reopened.candidate_key == 'nocturno'
    assert manager.current_key == 'original'
    reopened.reject()
    reopened_again = show(manager)
    assert reopened_again.candidate_key == 'nocturno'
    assert manager.current_key == 'original'
    reopened_again.apply_candidate()
    assert manager.current_key == 'nocturno'
    assert reopened_again.result() == QDialog.DialogCode.Accepted


def test_postcommit_widget_refresh_error_reports_saved_theme_honestly(manager):
    from PyQt6.QtWidgets import QWidget
    class BrokenRefresh(QWidget):
        def refresh_theme(self):
            raise OSError('sample presentation failure')
    broken = BrokenRefresh()
    dialog = show(manager)
    select(dialog, 'nocturno')
    dialog.apply_candidate()
    assert dialog.isVisible()
    assert manager.current_key == 'nocturno'
    assert ThemePreferences(manager.preferences.path).current_key == 'nocturno'
    assert dialog.feedback.text() == str(msg(
        'El tema se guardó, pero la interfaz no pudo actualizarse por completo. Reinicia SORTH para terminar de aplicarlo.'))
    assert 'sample presentation failure' in dialog.details.toPlainText()
    # A corrected renderer can be retried without a second preference conflict.
    broken.refresh_theme = lambda: None
    dialog.apply_candidate()
    assert dialog.result() == QDialog.DialogCode.Accepted
    broken.close()


def test_html_like_entities_remain_literal_preview_metadata(manager, tmp_path):
    data = theme.builtin_themes()[0].spec.to_dict()
    data.update(name='&lt;b&gt;Literal&lt;/b&gt;',
                description='&lt;b&gt;Literal &amp; text&lt;/b&gt;')
    dialog = show(manager)
    assert dialog.import_file(write_theme(tmp_path / 'entities.json', data))
    assert dialog.selector.currentText() == data['name']
    assert data['description'] in dialog.metadata.text()
    assert dialog.metadata.textFormat() == Qt.TextFormat.PlainText
    dialog.reject()


@pytest.mark.parametrize('action', ['select', 'import', 'restore'])
def test_preview_preparation_failure_keeps_previous_candidate(manager, monkeypatch, tmp_path, action):
    dialog = show(manager)
    select(dialog, 'nocturno')
    before = dialog.candidate.to_dict()
    previous_style = dialog.preview.styleSheet()
    previous_palette = dialog.preview.palette()
    def fail(*args, **kwargs):
        raise OSError('temporary storage full')
    monkeypatch.setattr(theme, 'stylesheet_for', fail)
    if action == 'select':
        # The real signal path must never let a Python exception abort Qt.
        dialog.selector.setCurrentIndex(dialog.selector.findData('high_contrast'))
    elif action == 'restore':
        dialog.restore_button.click()
    else:
        assert not dialog.import_file(write_theme(tmp_path / 'valid.json'))
    assert dialog.candidate.to_dict() == before
    assert dialog.selector.currentData() == 'nocturno'
    assert dialog.preview.styleSheet() == previous_style
    assert dialog.preview.palette() == previous_palette
    assert 'temporary storage full' in dialog.details.toPlainText()
    assert manager.current_key == 'original'
    assert not manager.preferences.path.exists()
    dialog.reject()


def test_initial_preview_failure_opens_readable_error_with_apply_disabled(manager, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('temporary storage unavailable')
    monkeypatch.setattr(theme, 'stylesheet_for', fail)
    dialog = show(manager)
    assert not dialog.apply_button.isEnabled()
    assert dialog.preview.isHidden()
    assert dialog.details.isVisible()
    assert 'temporary storage unavailable' in dialog.details.toPlainText()
    assert not manager.preferences.path.exists()
    dialog.reject()


def test_native_preparation_failure_on_apply_stays_open_without_commit(manager, monkeypatch):
    dialog = show(manager)
    select(dialog, 'nocturno')
    def fail(*args, **kwargs):
        raise theme.ThemePreparationError('native resource preparation unavailable')
    monkeypatch.setattr(theme, 'stylesheet_for', fail)
    dialog.apply_button.click()
    assert dialog.isVisible()
    assert manager.current_key == 'original'
    assert not manager.preferences.path.exists()
    assert 'native resource preparation unavailable' in dialog.details.toPlainText()
    assert dialog.apply_button.isEnabled()
    dialog.reject()


@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('expanded', [False, True])
@pytest.mark.parametrize('style', ['Fusion', 'Windows'])
def test_focused_input_stays_revealed_after_resize_and_reflow(manager, tmp_path, locale, expanded, style):
    app = QApplication.instance()
    previous_style = app.style().objectName()
    if style not in QStyleFactory.keys():
        pytest.skip('native style is unavailable')
    app.setStyle(style)
    language = language_manager()
    previous_language = language.language
    language.set_language(locale, persist=False)
    dialog = show(manager)
    try:
        data = theme.builtin_themes()[0].spec.to_dict()
        data.update(name='Imported preview', description='A local theme for keyboard and resize testing.')
        assert dialog.import_file(write_theme(tmp_path / 'imported.json', data))
        if expanded:
            fonts = 'QWidget { font-size: 20pt; }'
            dialog.setStyleSheet(dialog.styleSheet() + fonts)
            dialog.preview.setStyleSheet(dialog.preview.styleSheet() + fonts)
        dialog.resize(820, 980)
        settle_settings_layout(dialog)
        dialog.selector.setFocus()
        for _ in range(12):
            QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Tab)
            if QApplication.focusWidget() is dialog.preview.input:
                break
        assert QApplication.focusWidget() is dialog.preview.input
        QTest.keyClicks(dialog.preview.input, 'My sample timetable')
        dialog.preview.input.setSelection(3, 6)
        expected_cursor = dialog.preview.input.cursorPosition()
        expected_selection = dialog.preview.input.selectedText()
        for width, height in ((460, 420), (820, 980), (460, 420)):
            dialog.resize(width, height)
            settle_settings_layout(dialog)
            assert QApplication.focusWidget() is dialog.preview.input
            assert dialog.preview.input.text() == 'My sample timetable'
            assert dialog.preview.input.cursorPosition() == expected_cursor
            assert dialog.preview.input.selectedText() == expected_selection
            viewport = dialog.scroll.viewport()
            assert viewport.rect().contains(dialog.preview.input.mapTo(viewport, dialog.preview.input.rect().topLeft()))
            assert viewport.rect().contains(dialog.preview.input.mapTo(viewport, dialog.preview.input.rect().bottomRight()))
            assert dialog.scroll.horizontalScrollBar().maximum() == 0
            for button in dialog.buttons.buttons():
                assert dialog.rect().contains(button.mapTo(dialog, button.rect().topLeft()))
                assert dialog.rect().contains(button.mapTo(dialog, button.rect().bottomRight()))
        # Locale wrapping also reflows the same focused control in place.
        language.set_language('en' if locale == 'es' else 'es', persist=False)
        settle_settings_layout(dialog)
        assert QApplication.focusWidget() is dialog.preview.input
        assert viewport.rect().contains(dialog.preview.input.mapTo(viewport, dialog.preview.input.rect().center()))
        assert dialog.preview.input.selectedText() == expected_selection
    finally:
        dialog.reject()
        language.set_language(previous_language, persist=False)
        app.setStyle(previous_style)


def test_reflow_does_not_scroll_for_footer_or_already_visible_focus(manager):
    dialog = show(manager)
    try:
        dialog.resize(460, 420)
        settle_settings_layout(dialog)
        dialog.restore_button.setFocus()
        scrollbar = dialog.scroll.verticalScrollBar()
        scrollbar.setValue(min(80, scrollbar.maximum()))
        before = scrollbar.value()
        dialog.resize(480, 420)
        settle_settings_layout(dialog)
        assert QApplication.focusWidget() is dialog.restore_button
        assert scrollbar.value() == before
        dialog.selector.setFocus()
        settle_settings_layout(dialog)
        before = scrollbar.value()
        dialog.resize(470, 420)
        settle_settings_layout(dialog)
        assert QApplication.focusWidget() is dialog.selector
        assert scrollbar.value() == before
    finally:
        dialog.reject()


def _widen_caption_metrics(button, target_width):
    """Exercise genuine native font metrics without changing the caption/font size."""
    from PyQt6.QtGui import QFont
    source = button._messages['setText'][1][0]
    button.setText(source)
    font = button.font()
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0)
    button.setFont(font)
    extra = max(0, target_width - button.minimumSizeHint().width())
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,
                          extra / max(1, len(button.text())) + 1)
    button.setFont(font)


@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('style', ['Fusion', 'Windows'])
def test_nested_preview_and_single_footer_caption_fit_native_metrics(manager, locale, style, monkeypatch):
    app = QApplication.instance()
    previous_style = app.style().objectName()
    language = language_manager()
    previous_language = language.language
    if style not in QStyleFactory.keys():
        pytest.skip('native style is unavailable')
    app.setStyle(style)
    language.set_language(locale, persist=False)
    dialog = show(manager)
    try:
        for choice in theme.builtin_themes():
            select(dialog, choice.key)
            fonts = 'QWidget { font-size: 20pt; }'
            dialog.setStyleSheet(dialog.styleSheet() + fonts)
            dialog.preview.setStyleSheet(dialog.preview.styleSheet() + fonts)
            dialog.resize(460, 420)
            settle_settings_layout(dialog)
            # Reproduce the two Windows limits even with smaller Linux fonts:
            # a preview action fits the outer body but not its inset panel;
            # Restore exceeds the entire footer, so stacking alone cannot help.
            _widen_caption_metrics(dialog.preview.primary, 385)
            _widen_caption_metrics(dialog.restore_button, 464)
            dialog.preview.input.setText('Selected sample text')
            dialog.preview.input.setSelection(2, 8)
            dialog.preview.input.setFocus()
            for width, height in ((460, 420), (461, 420), (820, 980), (460, 420)):
                dialog.resize(width, height)
                snapshot = settle_settings_layout(dialog)
                assert dialog.size() == QSize(width, height), snapshot
                assert dialog.scroll.horizontalScrollBar().maximum() == 0, snapshot
                assert dialog.scroll.viewport().height() > 100, snapshot
                assert app.focusWidget() is dialog.preview.input
                assert dialog.preview.input.selectedText() == 'lected s'
                viewport = dialog.scroll.viewport()
                assert viewport.rect().contains(dialog.preview.input.mapTo(viewport, dialog.preview.input.rect().topLeft()))
                assert viewport.rect().contains(dialog.preview.input.mapTo(viewport, dialog.preview.input.rect().bottomRight()))
                for button in (*dialog.buttons.buttons(), dialog.preview.primary):
                    assert button.width() >= button.minimumSizeHint().width(), snapshot
                    assert button.height() >= button.minimumSizeHint().height(), snapshot
                from tests.test_gui.test_mcp_setup_ux import caption_preserved_across_soft_breaks
                for button in (dialog.preview.primary, dialog.restore_button):
                    source = button._messages['setText'][1][0].render()
                    assert caption_preserved_across_soft_breaks(button.text(), source)
                    assert button.accessibleName() == source
                    assert button.font().pointSizeF() == 20
                for button in dialog.buttons.buttons():
                    assert dialog.rect().contains(button.mapTo(dialog, button.rect().topLeft()))
                    assert dialog.rect().contains(button.mapTo(dialog, button.rect().bottomRight()))
            language.set_language('en' if locale == 'es' else 'es', persist=False)
            snapshot = settle_settings_layout(dialog)
            assert dialog.scroll.horizontalScrollBar().maximum() == 0, snapshot
            assert app.focusWidget() is dialog.preview.input
            assert dialog.preview.input.selectedText() == 'lected s'
            for button in (dialog.preview.primary, dialog.restore_button):
                assert button.width() >= button.minimumSizeHint().width(), snapshot
                source = button._messages['setText'][1][0].render()
                assert caption_preserved_across_soft_breaks(button.text(), source)
                assert button.accessibleName() == source
            language.set_language(locale, persist=False)
            # Width changes must restore the canonical one-line caption too.
            dialog.resize(1600, 980)
            settle_settings_layout(dialog)
            for button in (dialog.preview.primary, dialog.restore_button):
                assert button.text() == button._messages['setText'][1][0].render()
        record_appearance_geometry(dialog, f'metrics-{style}-{locale}')
        # Settled idle event turns must not keep rewrapping due to descendants'
        # Resize/LayoutRequest notifications.
        wrap_calls = []
        for button in (*dialog._responsive_actions.controls, dialog.restore_button):
            original = button.wrapPresentationText
            def tracked(width, original=original):
                wrap_calls.append(width)
                return original(width)
            monkeypatch.setattr(button, 'wrapPresentationText', tracked)
        QTest.qWait(40)
        assert not wrap_calls
        assert not dialog._responsive_actions.timer.isActive()
        assert not dialog.buttons._metric_timer.isActive()
    finally:
        dialog.reject()
        language.set_language(previous_language, persist=False)
        app.setStyle(previous_style)
