"""Queued generation delivery is still in flight after QThread stops running."""
import time

import pytest
from PyQt6.QtWidgets import QApplication

from src.gui.main_window import _InfoDialog
from src.gui.scheduler_worker import SchedulerWorker
from tests.test_gui.test_background_import import window, session


@pytest.mark.parametrize('delivery', ['result', 'error', 'no_result'])
def test_close_invalidates_finished_workers_queued_delivery(window, tmp_path, monkeypatch, delivery):
    dialogs = []
    monkeypatch.setattr(_InfoDialog, 'exec', lambda dialog: dialogs.append(dialog.windowTitle()))
    if delivery != 'result':
        def finished_without_result(worker):
            if delivery == 'error':
                worker.error.emit('synthetic queued failure')
            else:
                worker.result_ready.emit(None, None)
        monkeypatch.setattr(SchedulerWorker, 'run', finished_without_result)
    window.pinned_group_ids.clear()
    window._save_session()
    before, disk = session(window), (tmp_path / 'session.db').read_bytes()
    window.show()
    window._generate_schedule()
    worker = window._worker
    # Wait without pumping Qt: the real worker has completed but its result and
    # finished notifications remain queued on the main thread.
    assert worker.wait(5000)
    assert not worker.isRunning() and window._worker is worker
    window.close()
    deadline = time.monotonic() + 3
    while window._worker is not None and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(.001)
    assert window._worker is None
    assert not window.isVisible()
    assert session(window) == before
    assert (tmp_path / 'session.db').read_bytes() == disk
    assert not dialogs
