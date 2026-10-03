"""Background reader. Communicates data only, never accesses widgets."""
from PyQt6.QtCore import QThread, pyqtSignal
from ..infrastructure.import_candidate import read_candidate
from ..infrastructure.excel_reader import ImportCancelled


class ImportWorker(QThread):
    result_ready = pyqtSignal(int, object, bool)
    failed = pyqtSignal(int, object)

    def __init__(self, token, path, previous=None, parent=None):
        super().__init__(parent)
        self.token, self.path, self.previous = token, path, previous

    def run(self):
        try:
            result = read_candidate(self.path, self.isInterruptionRequested, self.previous)
            if not self.isInterruptionRequested():
                self.result_ready.emit(self.token, result, result is self.previous)
        except ImportCancelled:
            return
        except Exception as error:
            if not self.isInterruptionRequested():
                self.failed.emit(self.token, error)
