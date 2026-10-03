"""Closing while a cancelled reader drains must preserve the accepted session."""
import threading
import time

import pytest
from PyQt6.QtWidgets import QApplication

from src.gui import import_worker
from src.gui.scheduler_worker import SchedulerWorker
from tests.test_gui.test_background_import import window, workbook, session
from tests.test_gui.import_helpers import wait_for_import


@pytest.mark.parametrize('cancel_first', [False, True])
def test_close_keeps_inputs_locked_until_reader_retires(window, tmp_path, monkeypatch, cancel_first):
    entered, release = threading.Event(), threading.Event()
    original = import_worker.read_candidate

    def blocked(path, cancelled, previous=None):
        entered.set()
        release.wait(5)
        return original(path, cancelled, previous)

    monkeypatch.setattr(import_worker, 'read_candidate', blocked)
    window.show()
    before, disk = session(window), (tmp_path / 'session.db').read_bytes()
    try:
        window._import.start(workbook(tmp_path / 'input.xlsx'))
        assert entered.wait(1)
        if cancel_first:
            window._import.cancel()
        window.close()
        assert window._import.closing and window.isVisible()
        assert window._busy
        assert not window.btn_generate.isEnabled()
        assert not window.course_manager.isEnabled()
        # Repeated cancellation must not reopen input while Close is pending.
        window._import.cancel(announce=False)
        assert window._busy and not window.btn_generate.isEnabled()
    finally:
        release.set()
        wait_for_import(window)
    assert not window.isVisible()
    assert session(window) == before
    assert (tmp_path / 'session.db').read_bytes() == disk


@pytest.mark.parametrize('finish_first', ['reader', 'scheduler'])
def test_close_cancels_generation_even_with_retiring_reader(window, tmp_path, monkeypatch, finish_first):
    reader_entered, reader_release = threading.Event(), threading.Event()
    scheduler_entered, scheduler_release = threading.Event(), threading.Event()
    read_original, run_original = import_worker.read_candidate, SchedulerWorker.run

    def blocked_read(path, cancelled, previous=None):
        reader_entered.set()
        reader_release.wait(5)
        return read_original(path, cancelled, previous)

    def blocked_run(worker):
        scheduler_entered.set()
        scheduler_release.wait(5)
        run_original(worker)

    monkeypatch.setattr(import_worker, 'read_candidate', blocked_read)
    monkeypatch.setattr(SchedulerWorker, 'run', blocked_run)
    window.pinned_group_ids.clear()
    window._save_session()
    window.show()
    before, disk = session(window), (tmp_path / 'session.db').read_bytes()
    try:
        window._import.start(workbook(tmp_path / 'input.xlsx'))
        assert reader_entered.wait(1)
        window._import.cancel()
        window._generate_schedule()
        assert scheduler_entered.wait(1)
        worker = window._worker
        window.close()
        assert worker.isInterruptionRequested()
        assert window._generation_cancelled
        assert window._busy and not window.btn_generate.isEnabled()
        releases = [reader_release, scheduler_release]
        if finish_first == 'scheduler':
            releases.reverse()
        releases[0].set()
        deadline = time.monotonic() + 3
        while (window._import.worker if finish_first == 'reader' else window._worker) is not None:
            assert time.monotonic() < deadline
            QApplication.processEvents()
            time.sleep(.001)
        assert window.isVisible()
        assert window._busy and not window.btn_generate.isEnabled()
        releases[1].set()
    finally:
        reader_release.set()
        scheduler_release.set()
        wait_for_import(window)
        deadline = time.monotonic() + 5
        while window._worker is not None and time.monotonic() < deadline:
            QApplication.processEvents()
            time.sleep(.001)
        assert window._worker is None
    assert not window.isVisible()
    assert session(window) == before
    assert (tmp_path / 'session.db').read_bytes() == disk


def test_cancel_failed_save_close_restores_controls_after_reader_retires(window, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    entered, release = threading.Event(), threading.Event()
    original = import_worker.read_candidate

    def blocked(path, cancelled, previous=None):
        entered.set()
        release.wait(5)
        return original(path, cancelled, previous)

    monkeypatch.setattr(import_worker, 'read_candidate', blocked)
    monkeypatch.setattr(window, '_save_session', lambda: False)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args: QMessageBox.StandardButton.Cancel)
    window._unsaved = True
    window.show()
    before, disk = session(window), (tmp_path / 'session.db').read_bytes()
    try:
        window._import.start(workbook(tmp_path / 'input.xlsx'))
        assert entered.wait(1)
        window.close()
    finally:
        release.set()
        wait_for_import(window)
    assert window.isVisible() and not window._import.closing
    assert not window._busy
    assert window.course_manager.isEnabled() and window.btn_generate.isEnabled()
    assert window.btn_projects.isEnabled() and window._retry_save_button.isEnabled()
    assert session(window) == before
    assert (tmp_path / 'session.db').read_bytes() == disk
