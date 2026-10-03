"""Drive the real Qt event loop until the staged import reaches a terminal state."""
import time
from PyQt6.QtWidgets import QApplication


def wait_for_import(window, timeout=10):
    deadline = time.monotonic() + timeout
    while (window._import.active or window._import.worker is not None or window._import.pending) and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.001)
    QApplication.processEvents()
    assert not window._import.active
    assert window._import.worker is None
    assert window._import.pending is None
