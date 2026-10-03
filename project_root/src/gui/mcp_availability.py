"""Owned, cancellable Qt process for a fixed local health probe."""
import json
from pathlib import Path
import sys
from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal


class McpAvailabilityProbe(QObject):
    finished = pyqtSignal(str)
    TIMEOUT_MS = 5000
    MAX_OUTPUT = 4096

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(Path(__file__).resolve().parents[2]))
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: self._stop('timeout'))
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.readyReadStandardError.connect(self._discard_error)
        self.process.finished.connect(self._complete)
        self.process.errorOccurred.connect(lambda _: self._stop('runtime_error'))
        self.active = False
        self.output = bytearray()

    def start(self):
        if self.active:
            return
        if getattr(sys, 'frozen', False):
            self.finished.emit('frozen_unsupported')
            return
        self.output.clear()
        self.active = True
        self.timer.start(self.TIMEOUT_MS)
        self.process.start(sys.executable, ['-B', '-m', 'src.mcp_adapter.availability'])

    def _read(self):
        data = bytes(self.process.readAllStandardOutput())
        if len(self.output) + len(data) > self.MAX_OUTPUT:
            self._stop('runtime_error')
        else:
            self.output.extend(data)

    def _discard_error(self):
        # Never display dependency tracebacks or user paths as health evidence.
        self.process.readAllStandardError()

    def _complete(self, code, status):
        if not self.active:
            return
        self._read()
        if not self.active:
            return
        result = 'runtime_error'
        try:
            parsed = json.loads(self.output)
            candidate = parsed['status']
            if (code == 0 and status == QProcess.ExitStatus.NormalExit and candidate in
                    {'available', 'missing_sdk', 'incompatible_sdk', 'frozen_unsupported', 'runtime_error'}):
                result = candidate
        except (ValueError, KeyError, TypeError):
            pass
        self._stop(result)

    def _stop(self, status):
        if not self.active:
            return
        self.active = False
        self.timer.stop()
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(200)
        self.finished.emit(status)

    def cancel(self):
        self._stop('cancelled')
