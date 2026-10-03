"""Owned Qt worker for an explicitly confirmed, offline MCP preparation.

Cancellation is cooperative: the installer owns staging cleanup and its atomic
commit. A dialog must keep this owner alive until ``finished`` is emitted; no
thread termination or rollback of a pre-existing component is attempted here.
"""
from threading import Event

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from ..application import mcp_component


class _PreparationThread(QThread):
    progress = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cancelled = Event()
        self.status = 'runtime_error'
        self.result = None

    def run(self):
        try:
            self.result = mcp_component.prepare_component(
                cancelled=self.cancelled.is_set, progress=self.progress.emit)
            self.status = 'available'
        except mcp_component.ComponentError as error:
            self.status = error.code
        except Exception:
            # Never expose paths, archive content or dependency diagnostics.
            self.status = 'runtime_error'


class McpPreparation(QObject):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = False
        self._thread = None

    def start(self):
        if self.active:
            return
        self.active = True
        self._thread = _PreparationThread(self)
        self._thread.progress.connect(self.progress)
        self._thread.finished.connect(self._complete)
        self._thread.start()

    def _complete(self):
        thread, self._thread = self._thread, None
        self.active = False
        status, result = thread.status, thread.result
        thread.deleteLater()
        self.finished.emit(status, result)

    def cancel(self):
        if self._thread is not None:
            self._thread.cancelled.set()
