"""Save/cancel/retry and picker-overwrite consent leave the session untouched."""
from copy import deepcopy

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from src.gui import excel_template
from src.gui.i18n import language_manager
from src.infrastructure.excel_reader import ExcelReader
from tests.test_gui.test_export_feedback import window


@pytest.mark.parametrize('language', ['es', 'en'])
def test_template_button_cancel_save_failure_retry(window, tmp_path, monkeypatch, language):
    manager = language_manager()
    previous_language = manager.language
    paths = iter(['', str(tmp_path / 'template'), str(tmp_path / 'directory.xlsx'), str(tmp_path / 'retry.XLSX')])
    (tmp_path / 'directory.xlsx').mkdir()
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (next(paths), ''))
    errors = []
    monkeypatch.setattr(excel_template._InfoDialog, 'exec', lambda dialog: errors.append(dialog.windowTitle()))
    schedule = deepcopy(window.current_schedule)
    session = (tmp_path / 'session.db').read_bytes()
    try:
        manager.set_language(language, persist=False)
        QApplication.processEvents()
        button = window.btn_template
        assert button.isEnabled() and button.isVisible()
        button.setFocus()
        QApplication.processEvents()
        assert button.width() >= button.sizeHint().width()
        assert button.geometry().right() <= window.width()
        window.status_bar.showMessage('previous outcome')
        QTest.keyClick(button, Qt.Key.Key_Space)
        assert window.status_bar.currentMessage() == 'previous outcome'
        QTest.keyClick(button, Qt.Key.Key_Space)
        assert ExcelReader(tmp_path / 'template.xlsx').load_validated().warnings == []
        success = window.status_bar.currentMessage()
        assert 'template.xlsx' in success
        QTest.keyClick(button, Qt.Key.Key_Space)
        assert len(errors) == 1
        assert 'directory.xlsx' in window.status_bar.currentMessage()
        assert 'Could not' in window.status_bar.currentMessage() if language == 'en' else 'No se pudo' in window.status_bar.currentMessage()
        QTest.keyClick(button, Qt.Key.Key_Space)
        assert ExcelReader(tmp_path / 'retry.XLSX').load_validated().warnings == []
        assert 'retry.XLSX' in window.status_bar.currentMessage()
        assert window.current_schedule == schedule
        assert (tmp_path / 'session.db').read_bytes() == session
    finally:
        manager.set_language(previous_language, persist=False)


@pytest.mark.parametrize('answer', [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes])
@pytest.mark.parametrize('filename', ['template', 'template.v2'])
def test_resolved_template_overwrite_needs_consent(window, tmp_path, monkeypatch, answer, filename):
    target = tmp_path / f'{filename}.xlsx'
    target.write_bytes(b'original')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (str(tmp_path / filename), ''))
    prompts = []
    def confirm(dialog):
        assert str(target) in dialog.text()
        assert dialog.defaultButton() == dialog.button(QMessageBox.StandardButton.No)
        assert target.read_bytes() == b'original'
        prompts.append(dialog.text())
        return answer
    monkeypatch.setattr(QMessageBox, 'exec', confirm)
    excel_template.save_import_template(window)
    assert len(prompts) == 1
    if answer == QMessageBox.StandardButton.Yes:
        assert ExcelReader(target).load_validated().warnings == []
    else:
        assert target.read_bytes() == b'original'


def test_explicit_xlsx_keeps_native_picker_consent(window, tmp_path, monkeypatch):
    target = tmp_path / 'existing.xlsx'
    target.write_bytes(b'original approved in native picker')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (str(target), ''))
    monkeypatch.setattr(QMessageBox, 'exec', lambda *a: pytest.fail('Double confirmation'))
    excel_template.save_import_template(window)
    assert ExcelReader(target).load_validated().warnings == []
