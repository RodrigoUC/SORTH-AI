"""Overwrite consent must cover the resolved destination, not just picker input."""
from copy import deepcopy

import pytest
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QFileDialog, QDialog, QMessageBox

from src.gui.i18n import language_manager
from src.gui.main_window import _InfoDialog
from src.infrastructure.schedule_exporter import ScheduleExporter
from tests.test_gui.test_export_feedback import window


@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf'])
@pytest.mark.parametrize('filtered', [False, True])
@pytest.mark.parametrize('answer', [QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.Cancel,
                                   QMessageBox.StandardButton.Yes])
def test_resolved_collision_needs_consent(window, tmp_path, monkeypatch,
                                         extension, filtered, answer):
    selected = tmp_path / 'report'
    target = tmp_path / f'report.{extension}'
    original = b'IMPORTANT ORIGINAL CONTENT'
    target.write_bytes(original)
    before = deepcopy(window.current_schedule)
    session_bytes = (tmp_path / 'session.db').read_bytes()
    window.status_bar.showMessage('Previous export outcome')
    if filtered:
        window.schedule_viewer._list_search.setText('BIO')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        lambda *a: (str(selected), f'Format (*.{extension})'))
    prompts = []
    def confirm(*args):
        prompts.append(args)
        assert str(target) in str(args[2])
        assert args[3] == QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        assert args[4] == QMessageBox.StandardButton.No
        assert target.read_bytes() == original
        return answer
    monkeypatch.setattr(QMessageBox, 'question', confirm)
    modals = []
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: modals.append(self.windowTitle()))
    window._export_schedule(filtered=filtered)
    assert len(prompts) == 1
    assert window.current_schedule == before
    assert (tmp_path / 'session.db').read_bytes() == session_bytes
    assert not selected.exists()
    assert not list(tmp_path.glob('.sorth-export-*'))
    if answer == QMessageBox.StandardButton.Yes:
        assert target.read_bytes() != original
        assert target.name in window.status_bar.currentMessage()
        assert len(modals) == 1
        if extension == 'xlsx':
            from openpyxl import load_workbook
            book = load_workbook(target)
            assert len(list(book['Asignaciones'].values)) == (2 if filtered else 3)
            book.close()
        elif extension == 'csv':
            import csv
            with target.open(encoding='utf-8-sig', newline='') as stream:
                assert len(list(csv.reader(stream))) == (2 if filtered else 3)
        else:
            from pypdf import PdfReader
            text = '\n'.join(p.extract_text() for p in PdfReader(target).pages)
            assert 'BIO-G1' in text
            assert ('QUI-G1' in text) is not filtered
    else:
        assert target.read_bytes() == original
        assert window.status_bar.currentMessage() == 'Previous export outcome'
        assert not modals


@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf'])
@pytest.mark.parametrize('existing', [False, True])
@pytest.mark.parametrize('name', ['report.{ext}', 'report.{upper}',
                                  'report.release.{ext}', 'report.csv', 'report.other'])
def test_explicit_destination_keeps_picker_approval_and_dispatch(
        window, tmp_path, monkeypatch, extension, existing, name):
    path = tmp_path / name.format(ext=extension, upper=extension.upper())
    if existing:
        path.write_bytes(b'Previously approved by the picker')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        lambda *a: (str(path), f'Format (*.{extension})'))
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: pytest.fail('Double confirmation'))
    called = []
    for kind in ('excel', 'csv', 'pdf'):
        monkeypatch.setattr(ScheduleExporter, f'to_{kind}',
                            lambda self, assignments, output, _kind=kind, **kwargs:
                            called.append((_kind, output)))
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
    window._export_schedule()
    expected = {'xlsx': 'excel', 'csv': 'csv', 'pdf': 'pdf'}.get(path.suffix[1:].lower(), 'excel')
    assert called == [(expected, str(path))]


@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf'])
def test_missing_resolved_target_and_picker_cancel_do_not_prompt(
        window, tmp_path, monkeypatch, extension):
    selected = tmp_path / 'report'
    paths = iter(['', str(selected)])
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        lambda *a: (next(paths), f'Format (*.{extension})'))
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: pytest.fail('Unexpected confirmation'))
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
    window.status_bar.showMessage('Previous outcome')
    window._export_schedule()
    assert window.status_bar.currentMessage() == 'Previous outcome'
    assert not list(tmp_path.glob('report*'))
    window._export_schedule()
    assert (tmp_path / f'report.{extension}').stat().st_size


@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf'])
def test_real_qt_picker_suffixless_collision_preserves_bytes(
        window, tmp_path, monkeypatch, language, extension):
    """Actual Qt save acceptance does not approve the later suffixed path."""
    manager, old_language = language_manager(), language_manager().language
    manager.set_language(language, persist=False)
    target = tmp_path / f'report.{extension}'
    target.write_bytes(b'original')
    picker = QFileDialog(window, 'Save', str(tmp_path), f'Format (*.{extension})')
    picker.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    picker.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    picker.selectFile('report')
    def select(*args):
        assert all(f'*.{ext}' in args[3] for ext in ['xlsx', 'csv', 'pdf'])
        QTimer.singleShot(0, picker.accept)
        assert picker.exec() == QDialog.DialogCode.Accepted
        assert picker.defaultSuffix() == ''
        assert picker.selectedFiles() == [str(tmp_path / 'report')]
        return picker.selectedFiles()[0], picker.selectedNameFilter()
    prompts = []
    def decline(*args):
        prompts.append(str(args[2]))
        return QMessageBox.StandardButton.No
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', select)
    monkeypatch.setattr(QMessageBox, 'question', decline)
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
    try:
        window._export_schedule()
        assert target.read_bytes() == b'original'
        assert len(prompts) == 1
        assert ('already exists' if language == 'en' else 'ya existe') in prompts[0]
    finally:
        manager.set_language(old_language, persist=False)


@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf'])
@pytest.mark.parametrize('action', ['enter', 'escape', 'yes'])
def test_real_overwrite_prompt_default_and_dismissal(
        window, tmp_path, monkeypatch, extension, action):
    from PyQt6.QtCore import Qt
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QApplication

    target = tmp_path / f'report.{extension}'
    target.write_bytes(b'original')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        lambda *a: (str(tmp_path / 'report'), f'Format (*.{extension})'))
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
    observations = []
    def respond():
        dialog = QApplication.activeModalWidget()
        observations.append((isinstance(dialog, QMessageBox), str(target) in dialog.text(),
                             dialog.defaultButton() == dialog.button(QMessageBox.StandardButton.No)))
        if action == 'yes':
            dialog.button(QMessageBox.StandardButton.Yes).click()
        else:
            QTest.keyClick(dialog, Qt.Key.Key_Return if action == 'enter' else Qt.Key.Key_Escape)
    QTimer.singleShot(0, respond)
    window._export_schedule()
    assert observations == [(True, True, True)]
    assert (target.read_bytes() == b'original') is (action != 'yes')


@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf'])
def test_approved_resolved_overwrite_still_preserves_bytes_on_atomic_failure(
        window, tmp_path, monkeypatch, extension):
    import os

    target = tmp_path / f'report.{extension}'
    target.write_bytes(b'original')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        lambda *a: (str(tmp_path / 'report'), f'Format (*.{extension})'))
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
    def fail_replace(source, destination):
        raise PermissionError('synthetic locked export')
    monkeypatch.setattr(os, 'replace', fail_replace)
    window._export_schedule()
    assert target.read_bytes() == b'original'
    assert not list(tmp_path.glob('.sorth-export-*'))
    assert target.name in window.status_bar.currentMessage()
    assert ('No se pudo exportar' in window.status_bar.currentMessage()
            or 'Could not export' in window.status_bar.currentMessage())


@pytest.mark.parametrize('extension', ['xlsx', 'csv', 'pdf'])
@pytest.mark.parametrize('dangling', [False, True])
@pytest.mark.parametrize('approve', [False, True])
def test_resolved_symlink_destination_needs_consent(
        window, tmp_path, monkeypatch, extension, dangling, approve):
    referent = tmp_path / f'linked.{extension}'
    if not dangling:
        referent.write_bytes(b'linked original')
    target = tmp_path / f'report.{extension}'
    try:
        target.symlink_to(referent)
    except (OSError, NotImplementedError):
        pytest.skip('Creating symlinks is unavailable on this host')
    monkeypatch.setattr(QFileDialog, 'getSaveFileName',
                        lambda *a: (str(tmp_path / 'report'), f'Format (*.{extension})'))
    prompts = []
    def confirm(*args):
        prompts.append(str(args[2]))
        return QMessageBox.StandardButton.Yes if approve else QMessageBox.StandardButton.No
    monkeypatch.setattr(QMessageBox, 'question', confirm)
    monkeypatch.setattr(_InfoDialog, 'exec', lambda self: 0)
    window._export_schedule()
    assert len(prompts) == 1 and str(target) in prompts[0]
    if approve:
        assert not target.is_symlink() and target.stat().st_size
    else:
        assert target.is_symlink() and target.readlink() == referent
    assert referent.exists() is not dangling
    if not dangling:
        assert referent.read_bytes() == b'linked original'
