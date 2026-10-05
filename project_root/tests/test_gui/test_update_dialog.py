"""Offline native updater lifecycle, consent, localization and layout regressions."""
import ast
from dataclasses import replace
from pathlib import Path
import re
from threading import Event
import time
from types import SimpleNamespace

import pytest
from PyQt6 import sip
from PyQt6.QtCore import QCoreApplication, QEvent, QSize, QThread, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QStyleFactory, QWidget

from src.application import app_updates
from src.gui import theme, update_dialog
from src.gui.i18n import language_manager, msg
from src.gui.i18n_widgets import QDialogButtonBox, QMessageBox
from src.gui.locales import LANGUAGES
from src.gui.theme_contract import validate_theme
from src.gui.update_dialog import UpdateDialog
from src.gui.update_operation import UpdateOperation


def wait_until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(.002)
    assert predicate(), 'Updater did not reach its expected terminal state'


def flush_deletions():
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()


def settle_layout(dialog, timeout=3):
    previous, stable = None, 0
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        snapshot = (dialog.size(), dialog.scroll.viewport().size(), dialog.scroll.widget().size(),
                    dialog.scroll.horizontalScrollBar().maximum(),
                    tuple((b.text(), b.size(), b.minimumSizeHint()) for b in dialog._responsive.controls))
        pending = dialog._responsive.timer.isActive() or dialog.buttons._metric_timer.isActive()
        stable = stable + 1 if snapshot == previous and not pending else 0
        if stable >= 2:
            return snapshot
        previous = snapshot
        QTest.qWait(1)
    pytest.fail(f'Updater layout did not settle: {snapshot!r}')


@pytest.fixture(autouse=True)
def isolated_backend(monkeypatch):
    """Any forgotten threaded mock must fail safely, never contact a service."""
    unexpected = []
    def forbidden(*args, **kwargs):
        unexpected.append('unexpected backend/network call')
        raise AssertionError(unexpected[-1])
    for name in ('check_updates', 'download_installer', 'verify_download', '_stream'):
        monkeypatch.setattr(app_updates, name, forbidden)
    monkeypatch.setattr(app_updates, 'current_identity',
                        lambda: SimpleNamespace(version='2.0.0', build_id=None))
    monkeypatch.setattr(app_updates, 'current_app_version', lambda: '2.0.0')
    discarded, opened = [], []
    monkeypatch.setattr(app_updates, 'discard_download', discarded.append)
    monkeypatch.setattr(update_dialog.QDesktopServices, 'openUrl',
                        lambda url: opened.append(url.toString()) or True)
    manager = language_manager()
    previous = manager.language
    manager.set_language('es', persist=False)
    yield SimpleNamespace(discarded=discarded, opened=opened)
    manager.set_language(previous, persist=False)
    assert unexpected == []


@pytest.fixture
def release():
    installer = app_updates.InstallerAsset(
        name='SORTH-2.1.0-aaaaaaaaaaaa-windows-x64-unsigned-setup.exe',
        url='https://github.com/RodrigoUC/SORTH-AI/releases/download/v2.1.0/fixture.exe',
        size=1024, sha256='a' * 64)
    return app_updates.Release('2.1.0', 'v2.1.0', 'Synthetic stable release',
                               'Synthetic changes only. No session data.',
                               'https://github.com/RodrigoUC/SORTH-AI/releases/tag/v2.1.0', installer)


@pytest.fixture
def make_dialog():
    created = []
    def create():
        owner = QWidget()
        owner._pending_update_installer = None
        dialog = UpdateDialog(owner)
        created.append((owner, dialog))
        return dialog
    yield create
    for owner, dialog in created:
        if not sip.isdeleted(dialog):
            if dialog.operation.active:
                dialog.operation.cancel()
                wait_until(lambda: not dialog.operation.active)
            dialog.reject()
            dialog.deleteLater()
        if not sip.isdeleted(owner):
            owner.deleteLater()
    flush_deletions()


def show_result(dialog, release, state='available'):
    dialog._show_release(app_updates.UpdateResult(state, '2.0.0', release))


def packaged_windows(monkeypatch):
    monkeypatch.setattr(UpdateDialog, '_can_install', staticmethod(lambda: True))


def test_open_is_passive_and_shows_identity_without_network(make_dialog):
    dialog = make_dialog()
    dialog.show()
    QApplication.processEvents()
    assert not dialog.operation.active
    assert dialog.release is None and dialog.download is None
    assert '2.0.0' in dialog.identity_label.text()
    assert 'Código fuente' in dialog.identity_label.text()
    assert dialog.download_button.isHidden() and dialog.install_button.isHidden()
    assert dialog.check_button.isEnabled()


@pytest.mark.parametrize('state', ['no_releases', 'current', 'available'])
def test_release_states_require_manual_check(make_dialog, monkeypatch, release, state):
    packaged_windows(monkeypatch)
    result = app_updates.UpdateResult(state, '2.0.0', None if state == 'no_releases' else release)
    calls, threads = [], []
    def check(version, *, cancelled):
        calls.append(version)
        threads.append(QThread.currentThread())
        return result
    monkeypatch.setattr(app_updates, 'check_updates', check)
    dialog = make_dialog()
    dialog.show()
    dialog.check_button.click()
    wait_until(lambda: not dialog.operation.active)
    assert calls == ['2.0.0']
    assert all(thread != QApplication.instance().thread() for thread in threads)
    assert dialog.download_button.isVisible() is (state == 'available')
    assert dialog.page_button.isVisible() is (state != 'no_releases')
    assert dialog.install_button.isHidden() and dialog.download is None
    expected = {'no_releases': 'Todavía no hay publicaciones',
                'current': 'No hay una versión estable', 'available': 'Hay una actualización disponible'}
    assert expected[state] in dialog.status_label.text()


@pytest.mark.parametrize('platform,frozen,allowed', [
    ('linux', False, False), ('linux', True, False), ('win32', False, False),
    ('win32', True, True), ('darwin', True, False)])
def test_only_frozen_windows_offers_in_app_installation(make_dialog, monkeypatch, release,
                                                        platform, frozen, allowed):
    monkeypatch.setattr(update_dialog.sys, 'platform', platform)
    monkeypatch.setattr(update_dialog.sys, 'frozen', frozen, raising=False)
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, release)
    assert dialog._can_install() is allowed
    assert dialog.download_button.isVisible() is allowed
    if not allowed:
        dialog._download()
        dialog.download = object()
        dialog._verify_for_install()
        assert not dialog.operation.active


def test_missing_installer_keeps_official_release_readable(make_dialog, monkeypatch, release):
    packaged_windows(monkeypatch)
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, replace(release, installer=None))
    assert dialog.notes.toPlainText() == release.body
    assert dialog.download_button.isHidden()
    assert 'SHA-256' in dialog.status_label.text()
    dialog._download()
    assert not dialog.operation.active


def test_untrusted_release_title_and_notes_are_literal_plain_text(make_dialog, release, isolated_backend):
    body = '<script>alert(1)</script>\n<img src="https://evil.example/pixel">\n[run](file:///tmp/setup.exe)'
    title = '<b>Not a trusted signature</b>'
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, replace(release, body=body, title=title))
    assert dialog.release_label.textFormat() == Qt.TextFormat.PlainText
    assert title in dialog.release_label.text()
    assert dialog.notes.isReadOnly() and dialog.notes.tabChangesFocus()
    assert dialog.notes.toPlainText() == body
    assert isolated_backend.opened == []
    dialog.page_button.click()
    assert isolated_backend.opened == [release.page_url]


@pytest.mark.parametrize('code', ['offline', 'network_error', 'timeout', 'rate_limited',
                                  'invalid_metadata', 'unsafe_url', 'integrity_error',
                                  'storage_error', 'unexpected_sensitive_details'])
def test_backend_failures_are_safe_localized_and_retryable(make_dialog, monkeypatch, code):
    def fail(*args, **kwargs):
        raise app_updates.UpdateError(code)
    monkeypatch.setattr(app_updates, 'check_updates', fail)
    dialog = make_dialog()
    dialog.show()
    dialog.check()
    wait_until(lambda: not dialog.operation.active)
    expected = update_dialog.ERROR_MESSAGES.get(code, update_dialog.ERROR_MESSAGES['runtime_error'])
    assert dialog.status_label.text() == str(msg(expected))
    assert code not in dialog.status_label.text()
    assert dialog.check_button.isEnabled()
    assert dialog.download is None and dialog.install_button.isHidden()
    monkeypatch.setattr(app_updates, 'check_updates', lambda *a, **kw:
                        app_updates.UpdateResult('no_releases', '2.0.0'))
    dialog.check()
    wait_until(lambda: not dialog.operation.active)
    assert 'Todavía no hay publicaciones' in dialog.status_label.text()


def test_unexpected_worker_exception_never_exposes_details(make_dialog, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('https://token:secret@example.invalid/private-path')
    monkeypatch.setattr(app_updates, 'check_updates', fail)
    dialog = make_dialog()
    dialog.check()
    wait_until(lambda: not dialog.operation.active)
    assert dialog.status_label.text() == str(msg(update_dialog.ERROR_MESSAGES['runtime_error']))
    assert 'secret' not in dialog.status_label.text()


@pytest.mark.parametrize('kind', ['check', 'download', 'verify'])
def test_cancel_suppresses_late_success_and_discards_late_download(monkeypatch, release,
                                                                 isolated_backend, kind):
    entered, released = Event(), Event()
    result = object()
    def blocked(*args, **kwargs):
        entered.set()
        assert released.wait(2)
        return result
    method = {'check': 'check_updates', 'download': 'download_installer', 'verify': 'verify_download'}[kind]
    monkeypatch.setattr(app_updates, method, blocked)
    operation = UpdateOperation()
    finished = []
    operation.finished.connect(lambda *values: finished.append(values))
    assert operation.start(kind, release)
    try:
        wait_until(entered.is_set)
        assert not operation.start(kind, release)
        operation.cancel()
        operation.cancel()
        assert operation.active and finished == []
    finally:
        released.set()
        wait_until(lambda: not operation.active)
    assert finished == [('cancelled', None)]
    assert isolated_backend.discarded == ([result] if kind == 'download' else [])
    operation.deleteLater()


@pytest.mark.parametrize('dismiss', ['reject', 'close', 'escape'])
def test_close_and_destruction_wait_until_worker_cleanup(make_dialog, monkeypatch, dismiss):
    entered, allow_cleanup, cleanup_finished = Event(), Event(), Event()
    def slow_check(*args, cancelled):
        entered.set()
        wait_end = time.monotonic() + 2
        while not cancelled() and time.monotonic() < wait_end:
            time.sleep(.002)
        assert cancelled()
        assert allow_cleanup.wait(2)
        cleanup_finished.set()
        raise app_updates.UpdateError('cancelled')
    monkeypatch.setattr(app_updates, 'check_updates', slow_check)
    dialog = make_dialog()
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    destroyed = []
    dialog.destroyed.connect(lambda: destroyed.append(cleanup_finished.is_set()))
    dialog.show()
    dialog.check()
    try:
        wait_until(entered.is_set)
        if dismiss == 'escape':
            QTest.keyClick(dialog, Qt.Key.Key_Escape)
        else:
            getattr(dialog, dismiss)()
        QApplication.processEvents()
        assert dialog.isVisible() and dialog.operation.active
        assert dialog._pending_close is not None
        assert not cleanup_finished.is_set() and destroyed == []
        dialog.check()
        assert not dialog.buttons.isEnabled()
    finally:
        allow_cleanup.set()
        wait_until(lambda: sip.isdeleted(dialog) or not dialog.operation.active)
        flush_deletions()
    assert destroyed == [True]
    assert sip.isdeleted(dialog)


def test_repeated_checks_downloads_and_disposal_do_not_reuse_stale_files(
        make_dialog, monkeypatch, release, isolated_backend):
    packaged_windows(monkeypatch)
    checks, downloads = [], []
    monkeypatch.setattr(UpdateDialog, '_confirm_download', lambda self: True)
    def check(*args, **kwargs):
        checks.append(True)
        return app_updates.UpdateResult('available', '2.0.0', release)
    def download(*args, progress, **kwargs):
        value = object()
        downloads.append(value)
        progress(5, 10)
        return value
    monkeypatch.setattr(app_updates, 'check_updates', check)
    monkeypatch.setattr(app_updates, 'download_installer', download)
    dialog = make_dialog()
    dialog.show()
    for _ in range(2):
        dialog.check()
        wait_until(lambda: not dialog.operation.active)
        dialog._download()
        wait_until(lambda: not dialog.operation.active)
        assert dialog.download is downloads[-1]
        assert dialog.install_button.isVisible()
        assert dialog.window._pending_update_installer is None
    assert isolated_backend.discarded == downloads[:1]
    dialog._download()
    wait_until(lambda: not dialog.operation.active)
    assert isolated_backend.discarded == downloads[:2]
    dialog.reject()
    assert isolated_backend.discarded == downloads
    assert len(checks) == 2


def test_progress_is_bounded_and_ignored_after_cancellation(make_dialog):
    dialog = make_dialog()
    for received, total, expected in [(25, 100, 25), (500, 100, 100), (-1, 100, 0), (50, 0, 0)]:
        dialog._progress(received, total)
        assert dialog.progress_bar.value() == expected
    dialog._cancelling = True
    dialog._progress(50, 100)
    assert dialog.progress_bar.value() == 0
    dialog._cancelling = False
    dialog._pending_close = 0
    dialog._progress(50, 100)
    assert dialog.progress_bar.value() == 0
    dialog._pending_close = None


@pytest.mark.parametrize('approved', [False, True])
def test_verified_installer_transfers_only_after_explicit_confirmation(
        make_dialog, monkeypatch, release, isolated_backend, approved):
    packaged_windows(monkeypatch)
    verified, prompted = [], []
    download = object()
    def verify(value, *, cancelled):
        assert value is download
        verified.append(value)
        return value
    def confirm(box):
        prompted.append(box)
        assert verified == [download]
        assert box.textFormat() == Qt.TextFormat.PlainText
        assert box.defaultButton() is box.button(QMessageBox.StandardButton.Cancel)
        assert box.standardButtons() == (QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        assert '2.1.0' in box.text() and 'SHA-256' in box.text()
        assert 'SmartScreen' in box.text() and 'SQLite' in box.text()
        assert 'Guardar, cerrar e instalar' in box.button(QMessageBox.StandardButton.Yes).text()
        assert dialog.window._pending_update_installer is None
        assert dialog.download is download
        return QMessageBox.StandardButton.Yes if approved else QMessageBox.StandardButton.Cancel
    monkeypatch.setattr(app_updates, 'verify_download', verify)
    monkeypatch.setattr(QMessageBox, 'exec', confirm)
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, release)
    dialog.download = download
    dialog.install_button.show()
    dialog._verify_for_install()
    assert dialog.window._pending_update_installer is None
    wait_until(lambda: not dialog.operation.active)
    assert len(prompted) == 1
    if approved:
        assert dialog.window._pending_update_installer is download
        assert dialog.download is None and not dialog.isVisible()
        assert dialog.result() == dialog.DialogCode.Accepted
        assert isolated_backend.discarded == []
    else:
        assert dialog.window._pending_update_installer is None
        assert dialog.download is download and dialog.isVisible()
        assert 'Instalación cancelada' in dialog.status_label.text()
        dialog.reject()
        assert isolated_backend.discarded == [download]


def test_integrity_failure_never_prompts_and_forgets_installer(make_dialog, monkeypatch,
                                                              release, isolated_backend):
    packaged_windows(monkeypatch)
    download = object()
    def fail(*args, **kwargs):
        raise app_updates.UpdateError('integrity_error')
    monkeypatch.setattr(app_updates, 'verify_download', fail)
    monkeypatch.setattr(QMessageBox, 'exec', lambda box: pytest.fail('Unverified installer prompted'))
    dialog = make_dialog()
    show_result(dialog, release)
    dialog.download = download
    dialog._verify_for_install()
    wait_until(lambda: not dialog.operation.active)
    assert dialog.window._pending_update_installer is None
    assert dialog.download is None
    assert isolated_backend.discarded == [download]


def test_live_locale_switch_preserves_release_focus_and_plain_notes(make_dialog, release):
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, release)
    dialog.page_button.setFocus()
    QApplication.processEvents()
    manager = language_manager()
    for locale in ('en', 'es', 'en'):
        manager.set_language(locale, persist=False)
        settle_layout(dialog)
        assert dialog.page_button.hasFocus()
        assert dialog.release is release
        assert dialog.notes.toPlainText() == release.body
        assert dialog.check_button.accessibleName() == str(msg('Buscar actualizaciones'))
        assert dialog.status_label.text() == str(msg('Hay una actualización disponible: {version}', version='2.1.0'))
        assert str(msg('Código fuente')) in dialog.identity_label.text()
        assert dialog.buttons.button(QDialogButtonBox.StandardButton.Close).text().replace('&', '') in ('Cerrar', 'Close')


def test_empty_notes_retranslate_when_locale_changes(make_dialog, release):
    dialog = make_dialog()
    show_result(dialog, replace(release, body=''))
    language_manager().set_language('en', persist=False)
    QApplication.processEvents()
    assert dialog.notes.toPlainText() == str(msg('Esta publicación no incluye notas de cambios.'))


def test_updater_catalog_keys_exist_in_both_locales():
    tree = ast.parse(Path(update_dialog.__file__).read_text(encoding='utf-8'))
    keys = {node.args[0].value for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'msg'
            and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)}
    keys.update(update_dialog.ERROR_MESSAGES.values())
    for locale in ('es', 'en'):
        assert keys <= set(LANGUAGES[locale].messages), (locale, sorted(keys - set(LANGUAGES[locale].messages)))


@pytest.mark.parametrize('locale', ['es', 'en'])
@pytest.mark.parametrize('style_name', ['Fusion', 'Windows'])
@pytest.mark.parametrize('expanded', [False, True])
def test_compact_window_keeps_complete_actions_and_keyboard_focus_visible(
        make_dialog, monkeypatch, release, locale, style_name, expanded):
    packaged_windows(monkeypatch)
    app = QApplication.instance()
    original_style = app.style().objectName()
    if style_name not in QStyleFactory.keys():
        pytest.skip(f'{style_name} is unavailable')
    app.setStyle(style_name)
    language_manager().set_language(locale, persist=False)
    dialog = make_dialog()
    try:
        if expanded:
            dialog.setStyleSheet('QPushButton, QLabel, QPlainTextEdit { font-size: 20pt; }')
        dialog.resize(460, 420)
        dialog.show()
        show_result(dialog, release)
        dialog.install_button.show()
        snapshot = settle_layout(dialog)
        assert dialog.size() == QSize(460, 420), snapshot
        assert dialog.scroll.horizontalScrollBar().maximum() == 0, snapshot
        assert dialog.scroll.viewport().height() > 100
        actions = [dialog.check_button, dialog.page_button, dialog.download_button, dialog.install_button]
        for action in actions:
            source = action._messages['setText'][1][0].render()
            pattern = r'\s*'.join(re.escape(line) for line in action.text().split('\n'))
            assert re.fullmatch(pattern, source)
            assert action.accessibleName() == source
            assert action.width() >= action.minimumSizeHint().width(), snapshot
            assert action.height() >= action.minimumSizeHint().height(), snapshot
        close = dialog.buttons.button(QDialogButtonBox.StandardButton.Close)
        assert dialog.rect().contains(close.mapTo(dialog, close.rect().topLeft()))
        assert dialog.rect().contains(close.mapTo(dialog, close.rect().bottomRight()))
        for backwards in (False, True):
            dialog.check_button.setFocus()
            settle_layout(dialog)
            seen = set()
            modifier = Qt.KeyboardModifier.ShiftModifier if backwards else Qt.KeyboardModifier.NoModifier
            for _ in range(30):
                focused = app.focusWidget()
                assert focused is not None and focused.isVisible()
                seen.add(focused)
                if dialog.scroll.widget().isAncestorOf(focused):
                    assert dialog.scroll.viewport().rect().contains(
                        focused.mapTo(dialog.scroll.viewport(), focused.rect().center()))
                QTest.keyClick(focused, Qt.Key.Key_Tab, modifier)
                settle_layout(dialog)
                if app.focusWidget() is dialog.check_button:
                    break
            else:
                pytest.fail('Keyboard focus failed to complete its native tab cycle')
            assert all(action in seen for action in actions)
            assert dialog.notes in seen and close in seen and dialog.status_label in seen
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        assert not dialog.isVisible()
    finally:
        dialog.reject()
        app.setStyle(original_style)


def test_dialog_reuses_live_light_dark_high_contrast_and_custom_themes(make_dialog, release, tmp_path):
    from src.gui.theme_preferences import ThemePreferences
    app = QApplication.instance()
    original_spec = theme.current_theme()
    prepared = (theme.stylesheet_for(original_spec), theme.palette_for(original_spec))
    manager = theme.ThemeManager(app, ThemePreferences(tmp_path / 'appearance.json'))
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, release)
    dialog.page_button.setFocus()
    payload = theme.builtin_themes()[1].spec.to_dict()
    payload['name'] = 'Synthetic custom theme'
    custom = validate_theme(payload)
    try:
        for spec in [choice.spec for choice in theme.builtin_themes()] + [custom]:
            manager._apply(spec)
            settle_layout(dialog)
            assert not dialog.styleSheet()
            assert dialog.palette().color(QPalette.ColorRole.Window).name() == spec.colors['canvas'].lower()
            assert dialog.notes.palette().color(QPalette.ColorRole.Base).name() == spec.colors['surface'].lower()
            assert dialog.page_button.hasFocus()
            assert dialog.release is release and dialog.notes.toPlainText() == release.body
        assert not manager.preferences.path.exists()
    finally:
        dialog.reject()
        manager._apply(original_spec, prepared=prepared)
        manager.deleteLater()


def test_update_preference_has_full_bilingual_disclosure_and_starts_off(tmp_path):
    from src.application.optional_features import FEATURES
    from src.gui.features import FeaturePreferences
    from PyQt6.QtCore import QSettings
    feature = next(item for item in FEATURES if item.key == 'auto_update_check')
    for locale in ('es', 'en'):
        assert feature.title in LANGUAGES[locale].messages
        assert feature.description in LANGUAGES[locale].messages
    preferences = FeaturePreferences(QSettings(str(tmp_path / 'preferences.ini'), QSettings.Format.IniFormat))
    assert not preferences.enabled('auto_update_check')
    assert not preferences.path.exists()


@pytest.mark.parametrize('kind', ['download', 'verify'])
def test_closing_during_late_result_never_installs_or_prompts(make_dialog, monkeypatch,
                                                           release, isolated_backend, kind):
    packaged_windows(monkeypatch)
    monkeypatch.setattr(UpdateDialog, '_confirm_download', lambda self: True)
    entered, released = Event(), Event()
    download = object()
    def blocked(*args, **kwargs):
        entered.set()
        assert released.wait(2)
        return download
    monkeypatch.setattr(app_updates, {'download': 'download_installer', 'verify': 'verify_download'}[kind], blocked)
    monkeypatch.setattr(QMessageBox, 'exec', lambda box: pytest.fail('Cancelled verification prompted'))
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, release)
    if kind == 'verify':
        dialog.download = download
        dialog._verify_for_install()
    else:
        dialog._download()
    try:
        wait_until(entered.is_set)
        dialog.reject()
        dialog.reject()
        assert dialog.operation.active and dialog.isVisible()
        assert not dialog.cancel_button.isEnabled()
    finally:
        released.set()
        wait_until(lambda: not dialog.operation.active)
    assert not dialog.isVisible()
    assert dialog.window._pending_update_installer is None
    assert dialog.download is None
    assert isolated_backend.discarded == [download]


def test_cancel_then_retry_check_ignores_old_release_and_duplicate_clicks(make_dialog, monkeypatch, release):
    entered, released = Event(), Event()
    calls = []
    def blocked(*args, **kwargs):
        calls.append(True)
        entered.set()
        assert released.wait(2)
        return app_updates.UpdateResult('available', '2.0.0', release)
    monkeypatch.setattr(app_updates, 'check_updates', blocked)
    dialog = make_dialog()
    dialog.show()
    dialog.check()
    try:
        wait_until(entered.is_set)
        dialog.check()
        dialog.cancel_button.click()
        dialog.check()
        assert dialog.operation.active
        assert not dialog.check_button.isEnabled()
        assert not dialog.cancel_button.isEnabled()
    finally:
        released.set()
        wait_until(lambda: not dialog.operation.active)
    assert calls == [True]
    assert dialog.release is None and dialog.notes.isHidden()
    assert dialog.check_button.isEnabled()
    monkeypatch.setattr(app_updates, 'check_updates', lambda *a, **kw:
                        app_updates.UpdateResult('no_releases', '2.0.0'))
    dialog.check()
    wait_until(lambda: not dialog.operation.active)
    assert dialog.release is None and 'Todavía no hay publicaciones' in dialog.status_label.text()


def test_enter_on_native_install_confirmation_defaults_to_cancel(make_dialog, monkeypatch, release):
    from PyQt6.QtCore import QTimer
    packaged_windows(monkeypatch)
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, release)
    def cancel_default():
        box = QApplication.activeModalWidget()
        assert isinstance(box, QMessageBox)
        QTest.keyClick(box, Qt.Key.Key_Return)
    QTimer.singleShot(0, cancel_default)
    assert not dialog._confirm_install()
    assert dialog.window._pending_update_installer is None and dialog.isVisible()


def test_failed_browser_open_stays_local_and_reports_retry(make_dialog, monkeypatch, release):
    dialog = make_dialog()
    show_result(dialog, release)
    monkeypatch.setattr(update_dialog.QDesktopServices, 'openUrl', lambda url: False)
    dialog._open_page()
    assert dialog.status_label.text() == str(msg('No se pudo abrir el navegador. Vuelve a intentarlo.'))
    assert not dialog.operation.active


@pytest.mark.parametrize('target', ['dialog', 'owner'])
@pytest.mark.parametrize('kind', ['check', 'download'])
def test_direct_native_destruction_cancels_and_drains_without_process_abort(target, kind):
    """Isolate the fatal QThread-owning-QObject regression from the test runner."""
    import os
    import subprocess
    import sys
    import textwrap
    source = textwrap.dedent('''
        import time
        from threading import Event
        from types import SimpleNamespace
        from PyQt6 import sip
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import QCoreApplication, QEvent
        from src.gui.update_dialog import UpdateDialog
        from src.application import app_updates
        app = QApplication([])
        entered, cancelled_seen, drained = Event(), Event(), Event()
        discarded = []
        result = object()
        def work(*args, cancelled, **kwargs):
            entered.set()
            deadline = time.monotonic() + 2
            while not cancelled() and time.monotonic() < deadline:
                time.sleep(.002)
            assert cancelled()
            cancelled_seen.set()
            time.sleep(.02)
            drained.set()
            return result
        def forbidden(*args, **kwargs):
            raise AssertionError('Network access is forbidden')
        app_updates._stream = forbidden
        app_updates.current_identity = lambda: SimpleNamespace(version='2.0.0', build_id=None)
        app_updates.current_app_version = lambda: '2.0.0'
        app_updates.check_updates = work
        app_updates.download_installer = work
        app_updates.discard_download = discarded.append
        owner = QWidget()
        dialog = UpdateDialog(owner)
        dialog.operation.start(KIND, '2.0.0')
        assert entered.wait(1)
        target = dialog if TARGET == 'dialog' else owner
        target.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and (not drained.is_set() or (KIND == 'download' and not discarded)):
            app.processEvents()
            time.sleep(.002)
        assert sip.isdeleted(target)
        assert cancelled_seen.is_set() and drained.is_set()
        if KIND == 'download':
            assert discarded == [result]
        print('Updater drained without crash or leaked download')
    ''')
    source = f'KIND = {kind!r}\nTARGET = {target!r}\n' + source
    result = subprocess.run([sys.executable, '-c', source], env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=8)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'without crash or leaked download' in result.stdout


@pytest.mark.parametrize('target', ['dialog', 'owner'])
def test_direct_deletion_discards_completed_untransferred_download(make_dialog, isolated_backend, target):
    dialog = make_dialog()
    download = object()
    dialog._finished('download', download)
    (dialog if target == 'dialog' else dialog.window).deleteLater()
    flush_deletions()
    assert sip.isdeleted(dialog)
    assert isolated_backend.discarded == [download]


@pytest.mark.parametrize('approved', [False, True])
def test_download_requires_separate_plain_text_default_cancel_confirmation(
        make_dialog, monkeypatch, release, approved):
    packaged_windows(monkeypatch)
    requested = []
    result = object()
    monkeypatch.setattr(app_updates, 'download_installer',
                        lambda *args, **kwargs: requested.append(args[0]) or result)
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, release)
    inspected = []
    def confirm(box):
        inspected.append(True)
        assert requested == [] and not dialog.operation.active
        assert box.textFormat() == Qt.TextFormat.PlainText
        assert box.defaultButton() is box.button(QMessageBox.StandardButton.Cancel)
        assert '2.1.0' in box.text() and str(release.installer.size) in box.text()
        assert 'RodrigoUC/SORTH-AI' in box.text() and 'SHA-256' in box.text()
        assert box.button(QMessageBox.StandardButton.Yes).text() == str(msg('Descargar instalador'))
        return QMessageBox.StandardButton.Yes if approved else QMessageBox.StandardButton.Cancel
    monkeypatch.setattr(QMessageBox, 'exec', confirm)
    dialog._download()
    wait_until(lambda: not dialog.operation.active)
    assert inspected == [True]
    assert requested == ([release] if approved else [])
    assert dialog.download is (result if approved else None)
    assert dialog.window._pending_update_installer is None


@pytest.mark.parametrize('kind', ['download', 'install'])
@pytest.mark.parametrize('dismiss', ['close', 'reject'])
def test_closing_during_nested_confirmation_rejects_stale_yes(
        make_dialog, monkeypatch, release, isolated_backend, kind, dismiss):
    packaged_windows(monkeypatch)
    dialog = make_dialog()
    dialog.show()
    show_result(dialog, release)
    download = object()
    prompts = []
    def confirm(box):
        prompts.append(box)
        assert dialog._confirmation is box
        getattr(dialog, dismiss)()
        assert not dialog.isVisible()
        # Emulate a queued affirmative arriving after dismissal.
        return QMessageBox.StandardButton.Yes
    monkeypatch.setattr(QMessageBox, 'exec', confirm)
    if kind == 'install':
        dialog._finished('download', download)
        monkeypatch.setattr(app_updates, 'verify_download', lambda *a, **kw: download)
        dialog._verify_for_install()
        wait_until(lambda: not dialog.operation.active)
        assert isolated_backend.discarded == [download]
    else:
        dialog._download()
        assert isolated_backend.discarded == []
    assert len(prompts) == 1
    assert dialog._confirmation is None
    assert not dialog.operation.active
    assert dialog.download is None
    assert dialog.window._pending_update_installer is None


@pytest.mark.parametrize('target', ['dialog', 'owner'])
@pytest.mark.parametrize('kind', ['download', 'install'])
def test_native_deletion_inside_real_confirmation_never_aborts_or_transfers(target, kind):
    import os
    import subprocess
    import sys
    import textwrap
    source = textwrap.dedent('''
        from types import SimpleNamespace
        from PyQt6 import sip
        from PyQt6.QtWidgets import QApplication, QWidget, QMessageBox
        from PyQt6.QtCore import QCoreApplication, QEvent, QTimer
        from src.gui.update_dialog import UpdateDialog
        from src.application import app_updates
        app = QApplication([])
        calls, discarded, prompted = [], [], []
        download = object()
        def forbidden(*args, **kwargs):
            calls.append(True)
            raise AssertionError('Network/install forbidden')
        for name in ('check_updates', 'download_installer', 'verify_download', '_stream'):
            setattr(app_updates, name, forbidden)
        app_updates.current_identity = lambda: SimpleNamespace(version='2.0.0', build_id=None)
        app_updates.current_app_version = lambda: '2.0.0'
        app_updates.discard_download = discarded.append
        UpdateDialog._can_install = staticmethod(lambda: True)
        owner = QWidget()
        owner._pending_update_installer = None
        dialog = UpdateDialog(owner)
        dialog.show()
        asset = app_updates.InstallerAsset('synthetic.exe', 'https://github.com/fixture.exe', 1024, 'a' * 64)
        release = app_updates.Release('2.1.0', 'v2.1.0', 'Synthetic release', 'Synthetic notes',
            'https://github.com/RodrigoUC/SORTH-AI/releases/tag/v2.1.0', asset)
        dialog._show_release(app_updates.UpdateResult('available', '2.0.0', release))
        def destroy():
            assert isinstance(app.activeModalWidget(), QMessageBox)
            prompted.append(True)
            (dialog if TARGET == 'dialog' else owner).deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QTimer.singleShot(0, destroy)
        if KIND == 'download':
            dialog._download()
        else:
            dialog._finished('download', download)
            dialog._finished('verify', download)
        app.processEvents()
        assert sip.isdeleted(dialog)
        assert prompted == [True] and not calls
        assert owner._pending_update_installer is None
        assert discarded == ([download] if KIND == 'install' else [])
        print('Native confirmation deletion safe')
    ''')
    source = f'KIND = {kind!r}\nTARGET = {target!r}\n' + source
    result = subprocess.run([sys.executable, '-c', source], env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=8)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Native confirmation deletion safe' in result.stdout
