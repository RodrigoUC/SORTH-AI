import sqlite3
import threading
import time
from copy import deepcopy
import pandas as pd
import pytest
from PyQt6.QtCore import QSettings, QTimer, QThread, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog, QDialogButtonBox
from src.gui.main_window import MainWindow
from src.gui.import_preview_dialog import ImportPreviewDialog
from src.gui import import_worker
from src.gui.i18n import language_manager
from src.infrastructure.import_candidate import read_candidate, ImportCandidate
from src.infrastructure.excel_reader import ExcelImport, ExcelImportError, ImportCancelled, ExcelReader
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom
from src.scheduling.time_model import TimeModel
from src.application.import_difference import import_difference
from tests.test_gui.import_helpers import wait_for_import


@pytest.fixture
def window(tmp_path, monkeypatch):
    settings = QSettings(str(tmp_path/'preferences.ini'), QSettings.Format.IniFormat)
    w = MainWindow(SessionRepository(str(tmp_path/'session.db')), restore_session=False, feature_settings=settings)
    w._classrooms = {'R': Classroom('R', 30, 'REGULAR')}
    w.course_manager.load_courses_from_excel([Course('BIO', 1, 60, 'REGULAR')])
    w.classroom_restrictions = {'R': {'BIO'}}
    w._classroom_course_map = {'R': ['BIO']}
    w.current_groups = w.course_manager.get_courses()[0].generate_groups()
    w.current_schedule = {'BIO-G1': ('R', 1, 480, 540)}
    w.current_groups[0].assignment = w.current_schedule['BIO-G1']
    w.pinned_group_ids = {'BIO-G1'}
    w.schedule_viewer.display_schedule(w.current_schedule, TimeModel.default(), w.current_groups)
    w._save_session()
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: None)
    yield w
    w._import.cancel(announce=False)
    wait_for_import(w)
    w._unsaved = False
    w.close()


def workbook(path, code='BIO', room='R', hours='0800-0900', count=1):
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'# DE AULA': [room], 'CAPACIDAD': [30]}).to_excel(writer, sheet_name='Aulas', index=False)
        pd.DataFrame({'Curso': [code]*count, 'Horas': [hours]*count, 'Aula': [room]*count}).to_excel(writer, sheet_name='Cursos', index=False)
    return str(path)


def session(w):
    return deepcopy((w.excel_path, [vars(c) for c in w.course_manager.get_courses()],
                     {k: vars(v) for k,v in w._classrooms.items()}, w.classroom_restrictions,
                     w._classroom_course_map, w.current_schedule, w.pinned_group_ids,
                     [vars(g) for g in w.current_groups or []], w._unsaved, w._save_error))


def enable_preview(w):
    w._features.save({**w._features.values(), 'import_diff_preview': True})


def test_reader_thread_and_event_loop_remain_responsive(window, tmp_path, monkeypatch):
    path = workbook(tmp_path/'input.xlsx')
    original = import_worker.read_candidate
    entered, release = threading.Event(), threading.Event()
    thread_checks = []
    def delayed(path, cancelled, previous=None):
        in_background = QThread.currentThread() != QApplication.instance().thread()
        thread_checks.append(in_background)
        entered.set()
        # A synchronous-reader regression must fail, rather than deadlock this test.
        if not in_background:
            raise AssertionError('Excel reader ran on the GUI thread')
        while not release.wait(.005):
            if cancelled(): raise ImportCancelled()
        return original(path, cancelled, previous)
    monkeypatch.setattr(import_worker, 'read_candidate', delayed)
    ticks = []
    timer = QTimer()
    def probe():
        ticks.append((time.monotonic(), QThread.currentThread() == QApplication.instance().thread()))
        if len(ticks) == 3:
            timer.stop()
    timer.timeout.connect(probe)
    try:
        start = time.monotonic()
        window._import.start(path)
        assert time.monotonic() - start < .25
        assert entered.wait(1)
        assert all(thread_checks)
        worker = window._import.worker
        assert worker is not None and worker.isRunning()
        # Queue event-loop probes without relying on native 5 ms timer accuracy.
        # Keep the original 80 ms budget, measured at delivery so a late event
        # dispatcher return cannot make a stalled GUI pass.
        probe_start = time.monotonic()
        deadline = probe_start + .08
        timer.start(0)
        while len(ticks) < 3 and time.monotonic() < deadline:
            QApplication.processEvents()
        assert len(ticks) == 3
        assert ticks[-1][0] - probe_start < .08
        assert all(on_gui_thread for _when, on_gui_thread in ticks)
        assert window._import.worker is worker and worker.isRunning()
        assert window.btn_load.isEnabled() and not window.course_manager.isEnabled()
    finally:
        timer.stop()
        release.set()
        wait_for_import(window)
    assert thread_checks and all(thread_checks)
    assert window.excel_path == path
    assert window.pinned_group_ids == {'BIO-G1'}
    assert window.current_schedule == {'BIO-G1': ('R', 1, 480, 540)}
    assert window.classroom_restrictions == {}
    assert window._repo.load_session()['pinned_group_ids'] == {'BIO-G1'}


def test_rapid_imports_use_one_reader_and_only_latest_result(window, tmp_path, monkeypatch):
    first, last = workbook(tmp_path/'first.xlsx'), workbook(tmp_path/'last.xlsx', count=2)
    entered, release = threading.Event(), threading.Event()
    calls = []
    original = import_worker.read_candidate
    def blocked(path, cancelled, previous=None):
        calls.append(path)
        if len(calls) == 1:
            entered.set()
            release.wait(2)
        return original(path, cancelled, previous)
    monkeypatch.setattr(import_worker, 'read_candidate', blocked)
    window._import.start(first)
    assert entered.wait(1)
    for _ in range(20): window._import.start(last)
    assert len(calls) == 1
    release.set()
    wait_for_import(window)
    assert calls == [first, last, last]
    assert window.excel_path == last
    assert window.course_manager.get_courses()[0].number_of_groups == 2


def test_cancel_then_late_delivery_cannot_overwrite(window, tmp_path):
    path = workbook(tmp_path/'input.xlsx')
    before, disk = session(window), open(window._repo._db_path,'rb').read()
    window._import.start(path)
    token = window._import.token
    window._import.cancel()
    window._import._result(token, read_candidate(path, lambda: False), True)
    wait_for_import(window)
    assert session(window) == before
    assert open(window._repo._db_path,'rb').read() == disk
    assert window.course_manager.isEnabled()


def test_close_is_cooperative_and_nonblocking(window, tmp_path, monkeypatch):
    path = workbook(tmp_path/'input.xlsx')
    entered, release = threading.Event(), threading.Event()
    original = import_worker.read_candidate
    def blocked(path, cancelled, previous=None):
        entered.set()
        release.wait(2)
        return original(path, cancelled, previous)
    monkeypatch.setattr(import_worker, 'read_candidate', blocked)
    window.show()
    window._import.start(path)
    assert entered.wait(1)
    before = session(window)
    start = time.monotonic()
    window.close()
    assert time.monotonic() - start < .25
    assert window._import.closing and window.isVisible()
    assert window._import.candidate_name is None
    assert not window._import_candidate_row.isVisible()
    assert window._import_candidate_field.text() == ''
    release.set()
    wait_for_import(window)
    QTest.qWait(20)
    assert not window.isVisible() and session(window) == before


@pytest.mark.parametrize('choice', ['cancel', 'escape', 'stale'])
def test_preview_dismissal_keeps_session(window, tmp_path, monkeypatch, choice):
    path = workbook(tmp_path/'input.xlsx', count=2)
    enable_preview(window)
    before = session(window)
    def review(dialog):
        if choice == 'stale':
            window._import.cancel()
            return QDialog.DialogCode.Accepted
        if choice == 'escape':
            dialog.show()
            QTest.keyClick(dialog, Qt.Key.Key_Escape)
            assert not dialog.isVisible()
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(ImportPreviewDialog, 'exec', review)
    window._import.start(path)
    wait_for_import(window)
    assert session(window) == before


@pytest.mark.parametrize('changed_to', ['valid', 'malformed'])
def test_changed_file_revalidated_and_reviewed_again(window, tmp_path, monkeypatch, changed_to):
    path = workbook(tmp_path/'input.xlsx')
    enable_preview(window)
    before, reviews, errors = session(window), [], []
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: errors.append(args))
    def review(dialog):
        reviews.append(dialog.details.toPlainText())
        if len(reviews) == 1:
            workbook(path, count=2, hours='bad' if changed_to == 'malformed' else '0800-0900')
            return QDialog.DialogCode.Accepted
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(ImportPreviewDialog, 'exec', review)
    window._import.start(path)
    wait_for_import(window)
    assert session(window) == before
    assert len(reviews) == (2 if changed_to == 'valid' else 1)
    assert bool(errors) == (changed_to == 'malformed')


def test_write_error_rolls_back_sql_without_unpinning(window, tmp_path, monkeypatch):
    path = workbook(tmp_path/'input.xlsx', room='NEW')
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.StandardButton.Yes)
    with sqlite3.connect(window._repo._db_path) as con:
        con.execute("CREATE TRIGGER refuse_import BEFORE INSERT ON courses BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END")
    before, disk = session(window), open(window._repo._db_path, 'rb').read()
    window._import.start(path)
    wait_for_import(window)
    assert session(window) == before
    assert open(window._repo._db_path, 'rb').read() == disk
    assert window._repo.load_session()['pinned_group_ids'] == {'BIO-G1'}


def test_accepted_unpin_and_import_commit_together(window, tmp_path, monkeypatch):
    path = workbook(tmp_path/'input.xlsx', room='NEW', code='CHEM')
    enable_preview(window)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.StandardButton.Yes)
    inspected = []
    def review(dialog):
        assert window.pinned_group_ids == {'BIO-G1'}
        inspected.append(dialog.details.toPlainText())
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(ImportPreviewDialog, 'exec', review)
    window._import.start(path)
    wait_for_import(window)
    assert all(text in inspected[0] for text in ['BIO-G1', 'CHEM', 'NEW'])
    assert not window.pinned_group_ids and window.current_schedule is None
    assert window._repo.load_session()['courses'][0].code == 'CHEM'


def test_default_off_still_validates_pin_confirmation(window, tmp_path, monkeypatch):
    assert not window._features.enabled('import_diff_preview')
    path, before, called = workbook(tmp_path/'input.xlsx', room='NEW'), session(window), []
    monkeypatch.setattr(ImportPreviewDialog, 'exec', lambda self: pytest.fail('preview should be off'))
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: called.append(args) or QMessageBox.StandardButton.Cancel)
    window._import.start(path)
    wait_for_import(window)
    assert called and session(window) == before


def test_difference_excludes_runtime_occupancy(window):
    imported = ExcelImport(deepcopy(window._classrooms), deepcopy(window.course_manager.get_courses()), {}, [])
    imported.classrooms['R'].occupancy = {1: [(100, 200)]}
    courses, rooms = import_difference(window.course_manager.get_courses(), window._classrooms, imported)
    assert not rooms.changed and not courses.changed
    imported.classrooms['R'].capacity = 50
    imported.courses[0].group_suggestions = [{'preferred_start_min': 600}]
    courses, rooms = import_difference(window.course_manager.get_courses(), window._classrooms, imported)
    assert courses.changed == {'BIO': ('group_suggestions',)}
    assert rooms.changed == {'R': ('capacity',)}


def test_preview_localizes_and_has_accessible_default_cancel(window):
    manager, previous = language_manager(), language_manager().language
    dialog = ImportPreviewDialog(window, ImportCandidate('synthetic.xlsx', b'x', ExcelImport({}, [], {}, [])), set())
    try:
        for language, title, heading, action in [('es','Revisar cambios del Excel','Eliminados','Reemplazar con este Excel'),
                                                ('en','Review Excel changes','Deleted','Replace with this Excel file')]:
            manager.set_language(language, persist=False)
            assert dialog.windowTitle() == title and heading in dialog.details.toPlainText()
            buttons = dialog.findChild(QDialogButtonBox)
            assert buttons.button(QDialogButtonBox.StandardButton.Ok).text() == action
            assert buttons.button(QDialogButtonBox.StandardButton.Cancel).isDefault()
            assert dialog.details.accessibleName() and dialog.details.isReadOnly()
    finally:
        manager.set_language(previous, persist=False)
        dialog.reject()


def test_snapshot_requires_identical_bytes_and_cancellation_is_separate(tmp_path):
    path = workbook(tmp_path/'input.xlsx')
    candidate = read_candidate(path, lambda: False)
    assert read_candidate(path, lambda: False, candidate) is candidate
    workbook(path, code='CHANGED')
    changed = read_candidate(path, lambda: False, candidate)
    assert changed.digest != candidate.digest and changed.imported.courses[0].code == 'CHANGED'
    with pytest.raises(ImportCancelled): read_candidate(path, lambda: True)
    checks = []
    with pytest.raises(ImportCancelled):
        ExcelReader(path, cancelled=lambda: checks.append(1) or len(checks) > 4).load_validated()


def test_reader_limits_remain_enforced(tmp_path, monkeypatch):
    path = workbook(tmp_path/'input.xlsx', count=101)
    monkeypatch.setattr(ExcelReader, 'MAX_DATA_ROWS', 100)
    with pytest.raises(ExcelImportError, match='límite'): read_candidate(path, lambda: False)


def test_file_changed_during_read_is_rejected(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from src.infrastructure import import_candidate
    path = workbook(tmp_path/'input.xlsx')
    original = import_candidate.os.fstat
    calls = []
    def changed(fd):
        result = original(fd)
        calls.append(fd)
        return SimpleNamespace(st_dev=result.st_dev, st_ino=result.st_ino, st_size=result.st_size,
                               st_mtime_ns=result.st_mtime_ns + (len(calls) == 3),
                               st_ctime_ns=result.st_ctime_ns)
    monkeypatch.setattr(import_candidate.os, 'fstat', changed)
    with pytest.raises(ExcelImportError, match='cambió mientras'):
        read_candidate(path, lambda: False)


def test_close_inside_preview_never_applies_accepted_late_result(window, tmp_path, monkeypatch):
    path = workbook(tmp_path/'input.xlsx')
    before = session(window)
    enable_preview(window)
    def review(dialog):
        window.close()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(ImportPreviewDialog, 'exec', review)
    window._import.start(path)
    wait_for_import(window)
    assert session(window) == before
    assert window._import.closing


def test_reduced_motion_uses_static_import_progress(window, tmp_path):
    path = workbook(tmp_path/'input.xlsx')
    window._set_reduced_motion(True)
    window._import.start(path)
    assert window._progress.maximum() == 1
    assert window._progress.accessibleName()
    window._import.cancel()
    wait_for_import(window)
    assert not window._progress.isVisible()


def test_opening_new_picker_invalidates_old_candidate_before_nested_events(window, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QFileDialog
    path = workbook(tmp_path/'input.xlsx')
    candidate = read_candidate(path, lambda: False)
    before = session(window)
    window._import.start(path)
    old_token = window._import.token
    def picker(*args):
        window._import._result(old_token, candidate, True)
        return '', ''
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', picker)
    window._load_excel()
    wait_for_import(window)
    assert session(window) == before


@pytest.mark.parametrize('accept', [False, True])
def test_real_warning_dialog_nested_event_loop_and_thread_cleanup(window, tmp_path, monkeypatch, accept):
    path = workbook(tmp_path/'warnings.xlsx')
    # A harmless missing preference generates the normal import warning.
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'# DE AULA': ['R'], 'CAPACIDAD': [30]}).to_excel(writer, sheet_name='Aulas', index=False)
        pd.DataFrame({'Curso': ['BIO'], 'Aula': ['MISSING']}).to_excel(writer, sheet_name='Cursos', index=False)
    original_exec = QMessageBox.exec
    before = session(window)
    def review(dialog):
        QTimer.singleShot(20, lambda: dialog.done(int(QMessageBox.StandardButton.Ok if accept else QMessageBox.StandardButton.Cancel)))
        return original_exec(dialog)
    monkeypatch.setattr(QMessageBox, 'exec', review)
    window._import.start(path)
    wait_for_import(window)
    if accept:
        assert window.excel_path == path
        assert window.pinned_group_ids == {'BIO-G1'}
    else:
        assert session(window) == before


def test_import_materialization_failure_preserves_disk_and_live_state(window, tmp_path, monkeypatch):
    candidate = read_candidate(workbook(tmp_path/'replacement.xlsx', code='NEW'), lambda: False)
    before = session(window)
    disk = (tmp_path/'session.db').read_bytes()
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic presentation failure')
    monkeypatch.setattr(window.course_manager, 'load_courses_from_excel', fail)
    with pytest.raises(RuntimeError, match='synthetic presentation failure'):
        window._commit_import(candidate, set())
    assert (tmp_path/'session.db').read_bytes() == disk
    assert session(window) == before


@pytest.mark.parametrize('method', ['_invalidate_schedule', '_refresh_overview', '_update_save_state'])
def test_late_import_presentation_failure_rolls_back(window, tmp_path, monkeypatch, method):
    candidate = read_candidate(workbook(tmp_path/'replacement.xlsx', code='NEW'), lambda: False)
    before = session(window)
    disk = (tmp_path/'session.db').read_bytes()
    original = getattr(window, method)
    calls = []
    def once(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError('late presentation')
        return original(*args, **kwargs)
    monkeypatch.setattr(window, method, once)
    with pytest.raises(RuntimeError, match='late presentation'):
        window._commit_import(candidate, set())
    assert (tmp_path/'session.db').read_bytes() == disk
    assert session(window) == before
    assert not window._restore_failed


def test_import_commit_failure_after_presentation_rolls_back(window, tmp_path, monkeypatch):
    from contextlib import contextmanager
    candidate = read_candidate(workbook(tmp_path/'replacement.xlsx', code='NEW'), lambda: False)
    before = session(window)
    disk = (tmp_path/'session.db').read_bytes()
    original = window._repo._connect
    @contextmanager
    def fail_commit():
        with original() as connection:
            yield connection
            if connection.total_changes:
                assert window.excel_path == candidate.path
                raise sqlite3.OperationalError('late commit failure')
    monkeypatch.setattr(window._repo, '_connect', fail_commit)
    with pytest.raises(sqlite3.OperationalError, match='late commit failure'):
        window._commit_import(candidate, set())
    assert (tmp_path/'session.db').read_bytes() == disk
    assert session(window) == before


def test_import_rollback_render_failure_locks_preserved_domain(window, tmp_path, monkeypatch):
    candidate = read_candidate(workbook(tmp_path/'replacement.xlsx', code='NEW'), lambda: False)
    before = session(window)
    disk = (tmp_path/'session.db').read_bytes()
    original_courses = window.course_manager.courses
    def fail(*args, **kwargs):
        raise RuntimeError('persistent renderer failure')
    monkeypatch.setattr(window.course_manager, '_refresh_table', fail)
    with pytest.raises(RuntimeError, match='persistent renderer failure'):
        window._commit_import(candidate, set())
    assert (tmp_path/'session.db').read_bytes() == disk
    assert window.course_manager.courses is original_courses
    assert session(window)[:-1] == before[:-1]
    assert window._restore_failed and window._busy
    assert not window.course_manager.isEnabled()
    window._import.cancel(announce=False)
    assert window._busy and not window.course_manager.isEnabled()
    window._unsaved = False


def test_import_failure_preserves_consultation_state(window, tmp_path, monkeypatch):
    view = window.schedule_viewer
    view._list_search.setText('BIO')
    view._day_filter.setCurrentIndex(2)
    window.course_manager._search.setText('BIO')
    window.course_manager.table.setCurrentCell(0, 1)
    before = (view._list_search.text(), view._day_filter.currentData(),
              window.course_manager._search.text(), window.course_manager.table.currentRow(),
              window.course_manager.table.currentColumn())
    candidate = read_candidate(workbook(tmp_path/'replacement.xlsx', code='NEW'), lambda: False)
    original = window._refresh_overview
    calls = []
    def once():
        if not calls:
            calls.append(True)
            raise RuntimeError('late presentation failure')
        original()
    monkeypatch.setattr(window, '_refresh_overview', once)
    with pytest.raises(RuntimeError):
        window._commit_import(candidate, set())
    assert (view._list_search.text(), view._day_filter.currentData(),
            window.course_manager._search.text(), window.course_manager.table.currentRow(),
            window.course_manager.table.currentColumn()) == before


def test_unpinned_import_does_not_materialize_unused_schedule(window, tmp_path, monkeypatch):
    from src.gui import main_window
    candidate = read_candidate(workbook(tmp_path/'replacement.xlsx', code='NEW'), lambda: False)
    def unused_view(*args, **kwargs):
        raise AssertionError('An unpinned import must clear, not materialize a schedule')
    monkeypatch.setattr(main_window, 'ScheduleViewerWidget', unused_view)
    monkeypatch.setattr(window.schedule_viewer, 'display_schedule', unused_view)
    window._commit_import(candidate, set())
    assert window.current_groups is None and window.current_schedule is None
    assert not window.pinned_group_ids
    saved = window._repo.load_session()
    assert saved['courses'][0].code == 'NEW'
    assert not saved['assignments'] and not saved['pinned_group_ids']


def test_pinned_import_preflight_matches_real_partial_schedule(window, tmp_path, monkeypatch):
    from src.gui.schedule_viewer_widget import ScheduleViewerWidget
    candidate = read_candidate(workbook(tmp_path/'replacement.xlsx', count=2), lambda: False)
    original = ScheduleViewerWidget.display_schedule
    presentations = []
    def record(view, assignments, time_model, groups, *args, **kwargs):
        presentations.append((view is window.schedule_viewer, deepcopy(assignments),
                              deepcopy([vars(group) for group in groups])))
        return original(view, assignments, time_model, groups, *args, **kwargs)
    monkeypatch.setattr(ScheduleViewerWidget, 'display_schedule', record)
    window._commit_import(candidate, {'BIO-G1'})
    assert len(presentations) == 2
    assert [entry[0] for entry in presentations] == [False, True]
    assert presentations[0][1:] == presentations[1][1:]
    assert len(window.current_groups) == 2
    assert window.current_groups[0].pinned
    assert not window.current_groups[1].assignment
    assert window.current_groups[1].unassigned_reason


@pytest.mark.parametrize('fail_preflight', [True, False])
def test_retained_pin_render_failure_preserves_transaction(window, tmp_path, monkeypatch, fail_preflight):
    from src.gui.schedule_viewer_widget import ScheduleViewerWidget
    candidate = read_candidate(workbook(tmp_path/'replacement.xlsx', count=2), lambda: False)
    before = session(window)
    disk = (tmp_path/'session.db').read_bytes()
    original = ScheduleViewerWidget.display_schedule
    failed = []
    def fail_once(view, *args, **kwargs):
        if not failed and (view is not window.schedule_viewer) == fail_preflight:
            failed.append(True)
            raise RuntimeError('retained-pin presentation failure')
        return original(view, *args, **kwargs)
    monkeypatch.setattr(ScheduleViewerWidget, 'display_schedule', fail_once)
    with pytest.raises(RuntimeError, match='retained-pin presentation failure'):
        window._commit_import(candidate, {'BIO-G1'})
    assert failed
    assert (tmp_path/'session.db').read_bytes() == disk
    assert session(window) == before
    assert not window._restore_failed


def read_f6(window):
    """Inspect the actual keyboard-opened, focusable plain-text status dialog."""
    from PyQt6.QtWidgets import QPlainTextEdit
    observed = []
    def inspect():
        dialog = QApplication.activeModalWidget()
        field = dialog.findChild(QPlainTextEdit)
        observed.append(field.toPlainText())
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
    window.activateWindow()
    QApplication.processEvents()
    QTimer.singleShot(30, inspect)
    QTest.keyClick(window, Qt.Key.Key_F6)
    assert len(observed) == 1
    return observed[0]


@pytest.mark.parametrize('language', ['es', 'en'])
@pytest.mark.parametrize('accepted_session', [False, True])
def test_candidate_identity_is_separate_plain_keyboard_readable_and_localized(
        window, tmp_path, monkeypatch, language, accepted_session):
    manager, original_language = language_manager(), language_manager().language
    name = 'Cursos & revisión ' + 'universitaria ' * 10 + '.xlsx'
    path = workbook(tmp_path / name)
    if accepted_session:
        window.excel_path = str(tmp_path / 'accepted.xlsx')
        window.excel_path_label.setText('accepted.xlsx')
        window._save_session()
    accepted_path, accepted_label = window.excel_path, window.excel_path_label.text()
    before, disk = session(window), (tmp_path / 'session.db').read_bytes()
    entered, release = threading.Event(), threading.Event()
    original = import_worker.read_candidate
    def checkpoint(path, cancelled, previous=None):
        entered.set()
        while not release.wait(.005):
            if cancelled():
                raise ImportCancelled()
        return original(path, cancelled, previous)
    monkeypatch.setattr(import_worker, 'read_candidate', checkpoint)
    try:
        manager.set_language(language, persist=False)
        accepted_label = window.excel_path_label.text()
        window.resize(960, 640)
        window.show()
        window._import.start(path)
        assert entered.wait(1)
        QApplication.processEvents()
        field = window._import_candidate_field
        assert window._import_candidate_row.isVisible() and field.isReadOnly()
        assert field.text() == name and field.cursorPosition() == 0
        assert window.excel_path == accepted_path
        assert window.excel_path_label.text() == accepted_label
        assert window.width() == 960 and window.height() == 640
        assert field.geometry().width() < field.fontMetrics().horizontalAdvance(name)
        field.setFocus()
        QTest.keyClick(field, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        assert field.selectedText() == name
        assert name in read_f6(window)
        if accepted_session:
            assert 'accepted.xlsx' in read_f6(window)
        assert ('Reading and validating' if language == 'en' else 'Leyendo y validando') in window.status_bar.currentMessage()
        for reduced in (True, False, True):
            window._set_reduced_motion(reduced)
            assert window._progress.maximum() == (1 if reduced else 0)
            assert name in window.status_bar.currentMessage()
            assert window._cancel_import_button.height() >= window._cancel_import_button.minimumSizeHint().height()
        manager.set_language('en' if language == 'es' else 'es', persist=False)
        assert name in window.status_bar.currentMessage() and field.text() == name
        # QLineEdit renders arbitrary names literally, without QLabel auto-rich text.
        window._set_import_candidate('<b>literal & untrusted.xlsx</b>')
        assert field.text() == '<b>literal & untrusted.xlsx</b>'
        window._set_import_candidate(name)
        window._import.cancel()
        assert window._import.candidate_name is None and not window._import_candidate_row.isVisible()
        assert field.text() == ''
        assert name in read_f6(window)
        assert session(window) == before and (tmp_path / 'session.db').read_bytes() == disk
    finally:
        release.set()
        wait_for_import(window)
        manager.set_language(original_language, persist=False)
        window._set_reduced_motion(False)


def test_latest_candidate_identity_tracks_waiting_read_review_verify_and_commit(window, tmp_path, monkeypatch):
    paths = [workbook(tmp_path / f'{name}.xlsx', count=count) for count, name in enumerate(['A', 'B', 'C'], 1)]
    entered, release = threading.Event(), threading.Event()
    original = import_worker.read_candidate
    calls, stages = [], []
    def checkpoint(path, cancelled, previous=None):
        calls.append(path)
        if len(calls) == 1:
            entered.set()
            release.wait(2)
        return original(path, cancelled, previous)
    monkeypatch.setattr(import_worker, 'read_candidate', checkpoint)
    window.status_bar.messageChanged.connect(stages.append)
    window.show()
    before = session(window)
    window._import.start(paths[0])
    assert entered.wait(1)
    for path in paths[1:]:
        window._import.start(path)
    assert window._import.candidate_name == 'C.xlsx'
    assert window._import_candidate_field.text() == 'C.xlsx'
    assert 'C.xlsx' in window.status_bar.currentMessage()
    assert 'Esperando' in window.status_bar.currentMessage()
    assert 'A.xlsx' not in read_f6(window) and 'B.xlsx' not in read_f6(window)
    assert session(window) == before
    release.set()
    wait_for_import(window)
    assert calls == [paths[0], paths[2], paths[2]]
    for stage in ('Leyendo y validando C.xlsx', 'Revisando C.xlsx', 'Comprobando que C.xlsx', 'Guardando C.xlsx'):
        assert any(stage in text for text in stages), stages
    assert window.excel_path == paths[2] and window.excel_path_label.text() == 'C.xlsx'
    assert window._import.candidate_name is None and window._import_candidate_field.text() == ''
    assert not window._import_candidate_row.isVisible()
    assert 'Excel cargado: C.xlsx' in window.status_bar.currentMessage()


def test_cancel_verification_clears_candidate_and_preserves_atomic_session(window, tmp_path, monkeypatch):
    path = workbook(tmp_path / 'verify.xlsx')
    original = import_worker.read_candidate
    entered, release = threading.Event(), threading.Event()
    def checkpoint(path, cancelled, previous=None):
        if previous is not None:
            entered.set()
            while not release.wait(.005):
                if cancelled():
                    raise ImportCancelled()
        return original(path, cancelled, previous)
    monkeypatch.setattr(import_worker, 'read_candidate', checkpoint)
    before, disk = session(window), (tmp_path / 'session.db').read_bytes()
    window._import.start(path)
    deadline = time.monotonic() + 2
    while not entered.is_set() and time.monotonic() < deadline:
        QTest.qWait(5)
    assert entered.is_set()
    assert 'Comprobando que verify.xlsx' in window.status_bar.currentMessage()
    window._import.cancel()
    release.set()
    wait_for_import(window)
    assert window._import.candidate_name is None and not window._import_candidate_field.text()
    assert 'verify.xlsx' in window.status_bar.currentMessage()
    assert session(window) == before and (tmp_path / 'session.db').read_bytes() == disk


def test_changed_candidate_review_identity_and_rejection(window, tmp_path, monkeypatch):
    path = workbook(tmp_path / 'changed.xlsx')
    enable_preview(window)
    statuses = []
    before, disk = session(window), (tmp_path / 'session.db').read_bytes()
    def review(dialog):
        statuses.append(window.status_bar.currentMessage())
        assert window._import.candidate_name == 'changed.xlsx'
        assert window._import_candidate_field.text() == 'changed.xlsx'
        if len(statuses) == 1:
            workbook(path, count=2)
            return QDialog.DialogCode.Accepted
        return QDialog.DialogCode.Rejected
    monkeypatch.setattr(ImportPreviewDialog, 'exec', review)
    window._import.start(path)
    wait_for_import(window)
    assert 'Revisando changed.xlsx' in statuses[0]
    assert 'El archivo changed.xlsx cambió' in statuses[1]
    assert window._import.candidate_name is None and not window._import_candidate_field.text()
    assert 'changed.xlsx' in window.status_bar.currentMessage()
    assert session(window) == before and (tmp_path / 'session.db').read_bytes() == disk


@pytest.mark.parametrize('failure', ['malformed', 'commit'])
def test_import_error_replaces_previous_success_and_preserves_identity_and_session(window, tmp_path, monkeypatch, failure):
    from contextlib import contextmanager
    from src.gui.i18n import msg
    path = workbook(tmp_path / 'failed-latest.xlsx', hours='bad' if failure == 'malformed' else '0800-0900')
    window.status_bar.showMessage(msg('✅ Excel cargado: {p1}  ({p3} aulas, {p5} cursos)', p1='old-success.xlsx', p3=1, p5=1))
    before, disk = session(window), (tmp_path / 'session.db').read_bytes()
    if failure == 'commit':
        original = window._repo._connect
        @contextmanager
        def fail_commit():
            with original() as connection:
                yield connection
                if connection.total_changes:
                    assert window.excel_path == path
                    raise sqlite3.OperationalError('synthetic private commit detail')
        monkeypatch.setattr(window._repo, '_connect', fail_commit)
    modal_statuses = []
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args: modal_statuses.append(window.status_bar.currentMessage()))
    window.show()
    window._import.start(path)
    wait_for_import(window)
    assert len(modal_statuses) == 1 and 'No se pudo importar failed-latest.xlsx' in modal_statuses[0]
    status = read_f6(window)
    assert 'No se pudo importar failed-latest.xlsx' in status
    assert 'old-success.xlsx' not in status and 'synthetic private commit detail' not in status
    assert window._import.candidate_name is None and not window._import_candidate_row.isVisible()
    assert session(window) == before and (tmp_path / 'session.db').read_bytes() == disk


def test_new_import_during_error_dialog_keeps_newest_identity(window, tmp_path, monkeypatch):
    failed = workbook(tmp_path / 'failed.xlsx', hours='bad')
    replacement = workbook(tmp_path / 'replacement.xlsx')
    statuses = []
    def modal(*args):
        window._import.start(replacement)
        statuses.append(window.status_bar.currentMessage())
    monkeypatch.setattr(QMessageBox, 'critical', modal)
    window._import.start(failed)
    wait_for_import(window)
    assert statuses and 'replacement.xlsx' in statuses[0]
    assert window.excel_path == replacement
    assert 'Excel cargado: replacement.xlsx' in window.status_bar.currentMessage()
    assert window._import.candidate_name is None
