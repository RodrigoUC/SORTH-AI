"""Explicit main commands survive native caption/mnemonic replacement."""
from collections import Counter

import pytest
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QVBoxLayout

from src.gui.i18n import language_manager
from src.gui.i18n_widgets import QDialog, QLineEdit
from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def commands(tmp_path, monkeypatch):
    calls = Counter()
    monkeypatch.setattr(MainWindow, '_load_excel', lambda self: calls.update(['load']))
    monkeypatch.setattr(MainWindow, '_generate_schedule', lambda self: calls.update(['generate']))
    monkeypatch.setattr(MainWindow, '_export_schedule', lambda self, **kwargs: calls.update(['export']))
    window = MainWindow(SessionRepository(str(tmp_path / 'session.db')), restore_session=False,
                        feature_settings=QSettings(str(tmp_path / 'preferences.ini'),
                                                   QSettings.Format.IniFormat))
    window._classrooms = {'R': Classroom('R', 30, 'REGULAR')}
    window.course_manager.load_courses_from_excel([Course('C', 1, 60, 'REGULAR')])
    window.current_groups = window.course_manager.courses[0].generate_groups()
    window.current_schedule = {'C-G1': ('R', 1, 480, 540)}
    window._update_export_actions()
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    yield window, calls
    window._unsaved = False
    window.close()


def press_commands(target):
    for key in (Qt.Key.Key_O, Qt.Key.Key_Return, Qt.Key.Key_S):
        QTest.keyClick(target, key, Qt.KeyboardModifier.ControlModifier)
    # Native QPushButton shortcuts animate before emitting clicked; allow that
    # path too so these assertions test command availability, not timing.
    QTest.qWait(120)
    QApplication.processEvents()


@pytest.mark.parametrize('focus', ['field', 'table', 'button'])
def test_explicit_commands_survive_language_roundtrips(commands, focus):
    window, calls = commands
    manager = language_manager()
    original = manager.language
    target = {'field': window.course_manager._search,
              'table': window.course_manager.table,
              'button': window.btn_load}[focus]
    try:
        target.setFocus()
        for index, language in enumerate(('es', 'en', 'es', 'en'), start=1):
            manager.set_language(language, persist=False)
            QApplication.processEvents()
            assert target.hasFocus()
            press_commands(target)
            assert calls == Counter(load=index, generate=index, export=index)
    finally:
        manager.set_language(original, persist=False)


def test_commands_survive_busy_labels_and_preserve_enabled_gates(commands):
    window, calls = commands
    window.btn_load.setFocus()
    press_commands(window)
    assert calls == Counter(load=1, generate=1, export=1)
    # Import deliberately keeps only Load available, to supersede its reader.
    window._set_import_busy(True)
    press_commands(window)
    assert calls == Counter(load=2, generate=1, export=1)
    window._set_import_busy(False)
    press_commands(window)
    assert calls == Counter(load=3, generate=2, export=2)
    window._set_busy(True)
    press_commands(window)
    assert calls == Counter(load=3, generate=2, export=2)
    window._set_busy(False)
    press_commands(window)
    assert calls == Counter(load=4, generate=3, export=3)
    window.btn_export.setEnabled(False)
    press_commands(window)
    assert calls == Counter(load=5, generate=4, export=3)


def test_child_modal_blocks_parent_commands_and_restores_invoker(commands):
    window, calls = commands
    window.btn_load.setFocus()
    dialog = QDialog(window)
    field = QLineEdit(dialog)
    QVBoxLayout(dialog).addWidget(field)
    dialog.setModal(True)
    dialog.show()
    dialog.activateWindow()
    field.setFocus()
    QApplication.processEvents()
    press_commands(field)
    assert calls == Counter()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    QApplication.processEvents()
    assert not dialog.isVisible()
    assert window.focusWidget() is window.btn_load
    window.activateWindow()
    QApplication.processEvents()
    press_commands(window)
    assert calls == Counter(load=1, generate=1, export=1)


def test_hidden_controls_and_windows_do_not_receive_commands(commands):
    window, calls = commands
    window.btn_load.hide()
    press_commands(window)
    assert calls == Counter(generate=1, export=1)
    window.btn_load.show()
    other = QDialog()
    field = QLineEdit(other)
    QVBoxLayout(other).addWidget(field)
    window.hide()
    other.show()
    other.activateWindow()
    field.setFocus()
    QApplication.processEvents()
    press_commands(field)
    assert calls == Counter(generate=1, export=1)
    other.close()
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    press_commands(window)
    assert calls == Counter(load=1, generate=2, export=2)
    # A single action owns each sequence; native button text owns no duplicate.
    for button, sequence in ((window.btn_load, 'Ctrl+O'),
                             (window.btn_generate, 'Ctrl+Return'),
                             (window.btn_export, 'Ctrl+S')):
        assert button.shortcut().isEmpty()
        assert [action.shortcut().toString() for action in button.actions()] == [sequence]
