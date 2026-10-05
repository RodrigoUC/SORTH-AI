"""A new workbook replaces session data only after native consent."""
from copy import deepcopy
import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QMessageBox, QDialogButtonBox
from src.gui.i18n_widgets import QDialog
from src.gui.import_replacement_dialog import ImportReplacementDialog
from src.gui.import_identity_dialog import ImportIdentityDialog
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from src.scheduling.time_model import TimeModel
from tests.test_gui.test_background_import import window, workbook, session
from tests.test_gui.import_helpers import wait_for_import


def prepare(window, tmp_path):
    path = workbook(tmp_path / 'old.xlsx')
    window._import.start(path)
    wait_for_import(window)
    window.resources = SchedulingResources(tuple(ResourceCatalog(kind, kind != 'student_group',
        (Resource('resource-1', 'Resource', ((1, 480, 1000),)),),
        (('BIO-G1', ('resource-1',)),)) for kind in ('teacher', 'student_group', 'student')))
    window.classroom_restrictions = {'R': {'BIO'}}
    window._save_session()
    return path


def snapshot(window):
    return (session(window), window.resources.to_data(), deepcopy(vars(window._history)),
            open(window._repo._db_path, 'rb').read())


@pytest.mark.parametrize('clear', [False, True])
@pytest.mark.parametrize('action', ['accept', 'cancel', 'escape', 'return'])
def test_other_workbook_requires_consent_and_replaces_links(window, tmp_path, monkeypatch, clear, action):
    prepare(window, tmp_path)
    if clear:
        window.pinned_group_ids.clear()
        for group in window.current_groups:
            group.pinned = False
        monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.Yes)
        window.schedule_viewer._clear_schedule()
        assert window.current_schedule is None
    before = snapshot(window)
    catalogs = window.resources.catalogs
    path = workbook(tmp_path / 'new.xlsx', count=2)
    observed = []
    def review(dialog):
        def interact():
            observed.append(dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel).isDefault())
            if action in ('return', 'escape'):
                QTest.keyClick(dialog, Qt.Key.Key_Return if action == 'return' else Qt.Key.Key_Escape)
            else:
                button = QDialogButtonBox.StandardButton.Ok if action == 'accept' else QDialogButtonBox.StandardButton.Cancel
                QTest.mouseClick(dialog.buttons.button(button), Qt.MouseButton.LeftButton)
        QTimer.singleShot(10, interact)
        return QDialog.exec(dialog)
    monkeypatch.setattr(ImportReplacementDialog, 'exec', review)
    monkeypatch.setattr(ImportIdentityDialog, 'exec', lambda self: pytest.fail('Replacement must not retain identities'))
    window._import.start(path)
    wait_for_import(window)
    assert observed == [True]
    assert window.btn_load.isEnabled() and not window._busy
    if action != 'accept':
        assert snapshot(window) == before
        return
    assert window.excel_path == path
    assert window.course_manager.get_courses()[0].number_of_groups == 2
    assert not window.pinned_group_ids and window.current_schedule is None
    assert not window.classroom_restrictions
    for before_catalog, after_catalog in zip(catalogs, window.resources.catalogs):
        assert not after_catalog.memberships
        assert after_catalog.resources == before_catalog.resources
        assert after_catalog.enabled == before_catalog.enabled
    saved = SessionRepository(window._repo._db_path).load_session()
    assert saved['resources'] == window.resources
    assert not saved['pinned_group_ids'] and not saved['assignments']
    assert saved['excel_path'] == path


def test_repeated_clear_import_and_same_path_update(window, tmp_path, monkeypatch):
    old = prepare(window, tmp_path)
    monkeypatch.setattr(ImportReplacementDialog, 'exec', lambda self: pytest.fail('Same path is an update'))
    workbook(old, count=2)
    window._import.start(old)
    wait_for_import(window)
    assert window.pinned_group_ids == {'BIO-G1'}
    assert window.resources.catalogs[0].memberships
    monkeypatch.setattr(ImportReplacementDialog, 'exec', lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(QMessageBox, 'question', lambda *a: QMessageBox.StandardButton.Yes)
    for i in range(3):
        window.pinned_group_ids.clear()
        for group in window.current_groups or []:
            group.pinned = False
        window.schedule_viewer._clear_schedule()
        path = workbook(tmp_path / f'new-{i}.xlsx', code=f'NEW{i}')
        window._import.start(path)
        wait_for_import(window)
        assert window.excel_path == path
        assert [c.code for c in window.course_manager.get_courses()] == [f'NEW{i}']
        assert not window.pinned_group_ids
        groups = window.course_manager.get_courses()[0].generate_groups()
        assignment = {groups[0].group_id: ('R', 1, 480, 540)}
        groups[0].assignment = next(iter(assignment.values()))
        window.current_groups, window.current_schedule = groups, assignment
        window.schedule_viewer.display_schedule(assignment, TimeModel.default(), groups)
        window._save_session()


@pytest.mark.parametrize('failure', ['invalid', 'save'])
def test_replacement_failures_preserve_previous_session(window, tmp_path, monkeypatch, failure):
    prepare(window, tmp_path)
    path = workbook(tmp_path / 'new.xlsx')
    if failure == 'invalid':
        open(path, 'wb').write(b'not a workbook')
        monkeypatch.setattr(ImportReplacementDialog, 'exec', lambda self: pytest.fail('Invalid candidate cannot ask to replace'))
    else:
        monkeypatch.setattr(window._repo, 'save_session', lambda **kwargs: (_ for _ in ()).throw(OSError('save failure')))
    before = snapshot(window)
    window._import.start(path)
    wait_for_import(window)
    assert snapshot(window) == before


@pytest.mark.parametrize('change', ['valid', 'invalid'])
def test_replacement_consent_is_bound_to_validated_contents(window, tmp_path, monkeypatch, change):
    prepare(window, tmp_path)
    before = snapshot(window)
    path = workbook(tmp_path / 'new.xlsx')
    seen = []
    def review(dialog):
        seen.append(dialog._candidate)
        if len(seen) > 1:
            return QDialog.DialogCode.Rejected
        if change == 'valid':
            workbook(path, count=3)
        else:
            open(path, 'wb').write(b'invalid replacement')
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(ImportReplacementDialog, 'exec', review)
    window._import.start(path)
    wait_for_import(window)
    assert len(seen) == (2 if change == 'valid' else 1)
    assert snapshot(window) == before


def test_replacement_presentation_failure_rolls_back_sql_and_resources(window, tmp_path, monkeypatch):
    prepare(window, tmp_path)
    path = workbook(tmp_path / 'new.xlsx', code='NEW')
    before = snapshot(window)
    def fail(courses):
        raise RuntimeError('presentation failure')
    monkeypatch.setattr(window.course_manager, 'load_courses_from_excel', fail)
    window._import.start(path)
    wait_for_import(window)
    assert snapshot(window) == before
