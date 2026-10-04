"""Successful exports finish without acknowledgment; details remain in F6."""
from copy import deepcopy

import pytest
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPlainTextEdit

from src.gui.i18n import language_manager, msg
from src.gui.main_window import MainWindow, _InfoDialog
from src.infrastructure.schedule_exporter import ScheduleExporter
from src.scheduling.time_model import TimeModel
from tests.test_gui.test_export_feedback import f6_status, window
from tests.test_gui.test_export_filenames import assert_export_content


@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf'])
@pytest.mark.parametrize('filtered', [False, True])
@pytest.mark.parametrize('partial', [False, True])
def test_success_has_no_acknowledgment_and_keeps_export_focus(
        window, tmp_path, monkeypatch, language, extension, filtered, partial):
    manager, old_language = language_manager(), language_manager().language
    if partial:
        window.current_schedule.pop('QUI-G1')
        window.schedule_viewer.display_schedule(
            window.current_schedule, TimeModel.from_calendar(window.calendar), window.current_groups)
    if filtered:
        window.schedule_viewer._list_search.setText('BIO')
    window._update_export_actions()
    window.tabs.setCurrentWidget(window.schedule_viewer)
    before_schedule = deepcopy(window.current_schedule)
    before_session = (tmp_path / 'session.db').read_bytes()
    target = tmp_path / ('horario & revisión.' + extension)
    choices = []
    def choose(*args):
        choices.append(args[1])
        return str(target), ''
    def no_acknowledgment(*args):
        pytest.fail('Successful export opened an unexpected acknowledgment')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', choose)
    monkeypatch.setattr(_InfoDialog, 'exec', no_acknowledgment)
    monkeypatch.setattr(QMessageBox, 'exec', no_acknowledgment)
    monkeypatch.setattr(QMessageBox, 'information', no_acknowledgment)
    try:
        manager.set_language(language, persist=False)
        button = window.btn_export_filtered if filtered else window.btn_export
        window.activateWindow()
        button.setFocus()
        QApplication.processEvents()
        QTest.keyClick(button, Qt.Key.Key_Space)
        assert len(choices) == 1
        assert target.is_file() and target.stat().st_size
        assert QApplication.activeModalWidget() is None
        assert QApplication.focusWidget() is button
        assert button.isEnabled()
        status = window.status_bar.currentMessage()
        assert target.name in status and str(tmp_path) not in status
        scope = msg('filtrado') if filtered else msg('todas las asignaciones')
        if partial:
            scope = msg('{scope} · horario parcial, {pending} pendientes', scope=scope, pending=1)
        count = 1 if filtered or partial else 2
        assert status == str(msg('Horario {p1}: {p3} sesiones exportadas a {p5}',
                                 p1=scope, p3=count, p5=target.name))
        snapshot = f6_status(window)
        assert str(target) in snapshot
        assert ('Last export:' if language == 'en' else 'Última exportación:') in snapshot
        assert str(scope) in snapshot
        assert window.current_schedule == before_schedule
        assert (tmp_path / 'session.db').read_bytes() == before_session
        if not partial and not filtered:
            assert_export_content(target, extension)
    finally:
        manager.set_language(old_language, persist=False)


@pytest.mark.parametrize('language', ['es', 'en'])
def test_last_export_survives_other_status_cancel_and_language_change(
        window, tmp_path, monkeypatch, language):
    manager, old_language = language_manager(), language_manager().language
    target = tmp_path / 'literal & informe.csv'
    paths = iter([str(target), ''])
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (next(paths), ''))
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: pytest.fail('Unexpected acknowledgment'))
    try:
        manager.set_language(language, persist=False)
        window._export_schedule()
        original = target.read_bytes()
        window.status_bar.showMessage(msg('Datos actualizados. Genere un nuevo horario para exportar.'))
        window._export_schedule()  # Canceling the native picker has no new outcome.
        for current in (language, 'en' if language == 'es' else 'es'):
            manager.set_language(current, persist=False)
            snapshot = f6_status(window)
            assert str(target) in snapshot
            assert ('Last export:' if current == 'en' else 'Última exportación:') in snapshot
            assert ('sessions exported' if current == 'en' else 'sesiones exportadas') in snapshot
            assert ('Generate a new schedule' if current == 'en' else 'Genere un nuevo horario') in snapshot
        assert target.read_bytes() == original
        # Export paths belong only to this window, not to the stored session.
        reopened = MainWindow(window._repo, restore_session=False)
        try:
            assert reopened._last_export_detail is None
        finally:
            reopened.close()
    finally:
        manager.set_language(old_language, persist=False)


@pytest.mark.parametrize('language', ['es', 'en'])
def test_f6_full_literal_path_is_scrollable_and_keyboard_copyable(
        window, tmp_path, monkeypatch, language):
    manager, old_language = language_manager(), language_manager().language
    # Presentation-only path avoids filesystem and Windows MAX_PATH assumptions.
    target = tmp_path.joinpath(*(['synthetic long directory & revisión'] * 200),
                               '<b>literal & informe.xlsx')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(target), ''))
    monkeypatch.setattr(ScheduleExporter, 'to_excel', lambda *args, **kwargs: None)
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: pytest.fail('Unexpected acknowledgment'))
    observed = []
    clipboard = QApplication.clipboard()
    original_clipboard = clipboard.text()
    def inspect():
        dialog = QApplication.activeModalWidget()
        text = dialog.findChild(QPlainTextEdit)
        text.setFocus()
        QTest.keyClick(text, Qt.Key.Key_Home, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(text, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
        keyboard_selection = text.textCursor().selectedText()
        QTest.keyClick(text, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(text, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        copied = clipboard.text()
        QTest.keyClick(text, Qt.Key.Key_End, Qt.KeyboardModifier.ControlModifier)
        scrolled = text.verticalScrollBar().value()
        QTest.keyClick(text, Qt.Key.Key_Tab)
        observed.append((text.toPlainText(), copied, text.isReadOnly(), scrolled,
                         QApplication.focusWidget() is not text, keyboard_selection))
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
    try:
        manager.set_language(language, persist=False)
        window._export_schedule()
        window._update_export_actions()
        window.activateWindow()
        window.btn_export.setFocus()
        QApplication.processEvents()
        QTimer.singleShot(30, inspect)
        QTest.keyClick(window, Qt.Key.Key_F6)
        QApplication.processEvents()
        assert len(observed) == 1
        text, copied, readonly, scrolled, tab_left, keyboard_selection = observed[0]
        assert str(target) in text and '<b>literal & informe.xlsx' in text
        assert copied == text and readonly and scrolled > 0 and tab_left
        assert keyboard_selection == text[0]
        assert QApplication.activeModalWidget() is None
        # Offscreen window managers may not globally reactivate the owner;
        # its remembered focus matches the shared native-dialog contract.
        assert window.focusWidget() is window.btn_export
    finally:
        clipboard.setText(original_clipboard)
        manager.set_language(old_language, persist=False)
