"""Mandatory positional-identity consent uses the real modal and durable import."""
import pandas as pd
import pytest
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialogButtonBox

from src.application.edit_history import encoded
from src.gui.i18n import language_manager
from src.gui.i18n_widgets import QDialog
from src.gui.import_identity_dialog import ImportIdentityDialog
from src.gui.import_replacement_dialog import ImportReplacementDialog
from src.gui.import_preview_dialog import ImportPreviewDialog
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from src.scheduling.time_model import TimeModel
from tests.test_gui.import_helpers import wait_for_import
from tests.test_gui.test_background_import import window


def workbook(path, order=(0, 1), hours=None):
    rows = [
        {'Curso': 'BIO', 'Horas': '0800-0900', 'Aula': 'R1', 'Días': 'L'},
        {'Curso': 'BIO', 'Horas': '1000-1100', 'Aula': 'R2', 'Días': 'I'},
        {'Curso': 'BIO', 'Horas': '1200-1300', 'Aula': 'R1', 'Días': 'M'},
    ]
    if hours:
        for row in rows:
            row['Horas'] = hours
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'# DE AULA': ['R1', 'R2'], 'CAPACIDAD': [30, 30]}).to_excel(writer, sheet_name='Aulas', index=False)
        pd.DataFrame([rows[index] for index in order]).to_excel(writer, sheet_name='Cursos', index=False)
    return str(path)


def prepare(window, tmp_path):
    path = workbook(tmp_path / 'same-source.xlsx')
    window.pinned_group_ids.clear()
    window._import.start(path)
    wait_for_import(window)
    groups = [g for course in window.course_manager.get_courses() for g in course.generate_groups()]
    window.current_schedule = {'BIO-G1': ('R1', 1, 480, 540), 'BIO-G2': ('R2', 2, 600, 660)}
    window.pinned_group_ids = {'BIO-G1'}
    for group in groups:
        group.assignment = window.current_schedule[group.group_id]
        group.pinned = group.group_id in window.pinned_group_ids
    window.current_groups = groups
    window.resources = SchedulingResources(tuple(ResourceCatalog(kind, kind != 'student_group',
        (Resource(f'{kind}-a', '<b>Alpha & literal</b>'), Resource(f'{kind}-b', 'Beta')),
        (('BIO-G1', (f'{kind}-a',)), ('BIO-G2', (f'{kind}-b',))))
        for kind in ('teacher', 'student_group', 'student')))
    window.schedule_viewer.display_schedule(window.current_schedule, TimeModel.default(), groups)
    assert window._save_session()
    return path


def snapshot(window, tmp_path):
    return (encoded(window._capture_edit_state()), encoded(vars(window._history)),
            (tmp_path / 'session.db').read_bytes())


@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('preview', [False, True])
@pytest.mark.parametrize('action', ['cancel', 'return', 'escape', 'accept'])
def test_reordered_linked_rows_require_explicit_native_review(window, tmp_path, monkeypatch, language, preview, action):
    path = prepare(window, tmp_path)
    window._features.save({**window._features.values(), 'import_diff_preview': preview})
    before = snapshot(window, tmp_path)
    resources = window.resources.to_data()
    manager, original_language = language_manager(), language_manager().language
    observed = []
    monkeypatch.setattr(ImportPreviewDialog, 'exec', lambda self: QDialog.DialogCode.Accepted)

    def review(dialog):
        def interact():
            cancel = dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel)
            observed.append({'text': dialog.details.toPlainText(), 'default': cancel.isDefault(),
                             'focus': dialog.details.hasFocus(), 'visible': dialog.isVisible(),
                             'ids': dialog._affected_ids})
            if action in ('return', 'escape'):
                QTest.keyClick(dialog.details, Qt.Key.Key_Return if action == 'return' else Qt.Key.Key_Escape)
            else:
                button = QDialogButtonBox.StandardButton.Ok if action == 'accept' else QDialogButtonBox.StandardButton.Cancel
                QTest.mouseClick(dialog.buttons.button(button), Qt.MouseButton.LeftButton)
            if dialog.isVisible():
                dialog.reject()
        QTimer.singleShot(30, interact)
        return QDialog.exec(dialog)

    monkeypatch.setattr(ImportIdentityDialog, 'exec', review)
    try:
        manager.set_language(language, persist=False)
        window.show()
        workbook(path, (1, 0))
        window._import.start(path)
        wait_for_import(window)
        assert len(observed) == 1
        item = observed[0]
        assert item['default'] and item['focus'] and item['visible']
        assert item['ids'] == ('BIO-G1', 'BIO-G2')
        assert '<b>Alpha & literal</b> [teacher-a]' in item['text']
        assert 'student_group-a' in item['text'] and 'student-a' in item['text']
        assert ('Inactive' if language == 'en' else 'Inactivo') in item['text']
        assert ('Pinned: R1' if language == 'en' else 'Fijada: R1') in item['text']
        assert '08:00' in item['text'] and '10:00' in item['text']
        if action == 'accept':
            assert window.resources.to_data() == resources
            assert window.pinned_group_ids == {'BIO-G1'}
            assert window.current_schedule == {'BIO-G1': ('R1', 1, 480, 540)}
            assert window.course_manager.get_courses()[0].group_suggestions[0]['aula'] == 'R2'
            restored = SessionRepository(str(tmp_path / 'session.db')).load_session()
            assert restored['resources'].to_data() == resources
            assert restored['pinned_group_ids'] == {'BIO-G1'}
            assert restored['assignments'] == window.current_schedule
        else:
            assert snapshot(window, tmp_path) == before
    finally:
        manager.set_language(original_language, persist=False)


def test_changed_bytes_require_new_identity_consent_and_cancel_preserves_all(window, tmp_path, monkeypatch):
    path = prepare(window, tmp_path)
    before = snapshot(window, tmp_path)
    workbook(path, (1, 0))
    reviews = []
    def review(dialog):
        reviews.append(dialog.details.toPlainText())
        if len(reviews) == 1:
            workbook(path, (2, 0, 1))
            return QDialog.DialogCode.Accepted
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(ImportIdentityDialog, 'exec', review)
    window._import.start(path)
    wait_for_import(window)
    assert len(reviews) == 2 and reviews[0] != reviews[1]
    assert snapshot(window, tmp_path) == before


def test_failed_save_after_identity_consent_preserves_all(window, tmp_path, monkeypatch):
    path = prepare(window, tmp_path)
    before = snapshot(window, tmp_path)
    workbook(path, (1, 0))
    seen = []
    monkeypatch.setattr(ImportIdentityDialog, 'exec', lambda dialog: seen.append(dialog._affected_ids) or QDialog.DialogCode.Accepted)
    def fail(**kwargs):
        raise OSError('synthetic save failure')
    monkeypatch.setattr(window._repo, 'save_session', fail)
    window._import.start(path)
    wait_for_import(window)
    assert len(seen) == 1
    assert snapshot(window, tmp_path) == before


def test_superseded_candidate_cannot_reuse_identity_consent(window, tmp_path, monkeypatch):
    path = prepare(window, tmp_path)
    before = snapshot(window, tmp_path)
    replacement = workbook(tmp_path / 'newer.xlsx', (2, 0, 1))
    workbook(path, (1, 0))
    reviews = []
    def review(dialog):
        reviews.append(dialog._candidate.path)
        if len(reviews) == 1:
            window._import.start(replacement)
            return QDialog.DialogCode.Accepted
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(ImportIdentityDialog, 'exec', review)
    monkeypatch.setattr(ImportReplacementDialog, 'exec', review)
    window._import.start(path)
    wait_for_import(window)
    assert reviews == [path, replacement]
    assert snapshot(window, tmp_path) == before


def test_unchanged_rows_do_not_add_identity_review(window, tmp_path, monkeypatch):
    path = prepare(window, tmp_path)
    seen = []
    monkeypatch.setattr(ImportIdentityDialog, 'exec', lambda dialog: seen.append(dialog._affected_ids) or QDialog.DialogCode.Rejected)
    window._import.start(path)
    wait_for_import(window)
    assert not seen
    assert window.pinned_group_ids == {'BIO-G1'}
    assert window.current_schedule == {'BIO-G1': ('R1', 1, 480, 540)}


@pytest.mark.parametrize('change', ['delete', 'duration'])
def test_identity_acceptance_does_not_bypass_later_resource_or_pin_cancellation(window, tmp_path, monkeypatch, change):
    from PyQt6.QtWidgets import QMessageBox
    path = prepare(window, tmp_path)
    before = snapshot(window, tmp_path)
    if change == 'delete':
        workbook(path, (1,))
    else:
        workbook(path, hours='0800-1000')
    seen = []
    monkeypatch.setattr(ImportIdentityDialog, 'exec', lambda dialog: seen.append('identity') or QDialog.DialogCode.Accepted)
    monkeypatch.setattr(QMessageBox, 'exec', lambda dialog: seen.append('orphan') or QMessageBox.StandardButton.Cancel)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: seen.append('pin') or QMessageBox.StandardButton.Cancel)
    window._import.start(path)
    wait_for_import(window)
    assert seen == ['identity', 'orphan' if change == 'delete' else 'pin']
    assert snapshot(window, tmp_path) == before


def test_live_language_switch_preserves_safe_default_and_literal_associations(window, tmp_path, monkeypatch):
    path = prepare(window, tmp_path)
    before = snapshot(window, tmp_path)
    workbook(path, (1, 0))
    manager, previous = language_manager(), language_manager().language
    observed = []
    def review(dialog):
        def interact():
            manager.set_language('en', persist=False)
            observed.append((dialog.windowTitle(), dialog.details.toPlainText(),
                             dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel).isDefault()))
            QTest.keyClick(dialog.details, Qt.Key.Key_Return)
            if dialog.isVisible():
                dialog.reject()
        QTimer.singleShot(30, interact)
        return QDialog.exec(dialog)
    monkeypatch.setattr(ImportIdentityDialog, 'exec', review)
    try:
        manager.set_language('es', persist=False)
        window._import.start(path)
        wait_for_import(window)
        assert observed[0][0] == 'Review Excel associations'
        assert '<b>Alpha & literal</b>' in observed[0][1]
        assert observed[0][2]
        assert snapshot(window, tmp_path) == before
    finally:
        manager.set_language(previous, persist=False)
