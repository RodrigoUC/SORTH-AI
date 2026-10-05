"""Owned cooperative updater worker; network/hash work never runs on Qt's thread."""
from threading import Event
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication
from ..application import app_updates


class _UpdateThread(QThread):
    progress = pyqtSignal(object, object)

    def __init__(self, kind, argument, parent):
        super().__init__(parent)
        self.kind, self.argument = kind, argument
        self.cancelled = Event()
        self.status, self.result = 'runtime_error', None

    def run(self):
        try:
            if self.kind == 'check':
                version = self.argument or app_updates.current_app_version()
                self.result = app_updates.check_updates(version, cancelled=self.cancelled.is_set)
            elif self.kind == 'download':
                self.result = app_updates.download_installer(
                    self.argument, cancelled=self.cancelled.is_set, progress=self.progress.emit)
            elif self.kind == 'verify':
                self.result = app_updates.verify_download(self.argument, cancelled=self.cancelled.is_set)
            else:
                return
            self.status = self.kind
        except app_updates.UpdateError as error:
            self.status = error.code
        except Exception:
            # Do not expose URLs, local paths, proxy credentials or HTTP payloads.
            self.status = 'runtime_error'


class UpdateOperation(QObject):
    finished = pyqtSignal(str, object)
    progress = pyqtSignal(object, object)

    def __init__(self, parent=None):
        # A disappearing dialog must never destroy a running QThread. Keep the
        # worker owner with QApplication and cancel when its UI owner is gone.
        super().__init__(QApplication.instance())
        self._abandoned = False
        if parent is not None:
            parent.destroyed.connect(self.abandon)
        self.active = False
        self._thread = None

    def start(self, kind, argument=None):
        if self._abandoned or self.active or kind not in ('check', 'download', 'verify'):
            return False
        self.active = True
        self._thread = _UpdateThread(kind, argument, self)
        self._thread.progress.connect(self.progress)
        self._thread.finished.connect(self._complete)
        self._thread.start()
        return True

    def cancel(self):
        if self._thread is not None:
            self._thread.cancelled.set()

    def abandon(self):
        self._abandoned = True
        self.cancel()
        if not self.active:
            self.deleteLater()

    def _complete(self):
        thread, self._thread = self._thread, None
        self.active = False
        status, result = thread.status, thread.result
        if thread.cancelled.is_set() or self._abandoned:
            if thread.kind == 'download' and result is not None:
                app_updates.discard_download(result)
            status, result = 'cancelled', None
        thread.deleteLater()
        if self._abandoned:
            self.deleteLater()
        else:
            self.finished.emit(status, result)
