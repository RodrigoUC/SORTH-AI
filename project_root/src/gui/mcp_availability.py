"""Owned, cancellable Qt process for a fixed local health probe."""
import json
from pathlib import Path
import sys
from threading import Event
from PyQt6.QtCore import QObject, QProcess, QThread, QTimer, pyqtSignal

from ..application import mcp_component


class _CommandResolver(QThread):
    """Hash verification can read many files; never do it on the GUI thread."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.command = None
        self.manifest = None
        self.status = 'runtime_error'
        self.cancelled = Event()

    def run(self):
        try:
            self.manifest = mcp_component.bundle_info()
            self.command = mcp_component.installed_command(cancelled=self.cancelled.is_set)
            self.status = 'available'
        except mcp_component.ComponentError as error:
            self.status = error.code
        except Exception:
            self.status = 'runtime_error'


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
        self.command = None
        self._manifest = None
        self._resolver = None
        self._cancelled = False

    def start(self):
        if self.active:
            return
        self.output.clear()
        self.command = None
        self._manifest = None
        self._cancelled = False
        self.active = True
        if getattr(sys, 'frozen', False):
            self._resolver = _CommandResolver(self)
            self._resolver.finished.connect(self._resolved)
            self._resolver.start()
            return
        self.timer.start(self.TIMEOUT_MS)
        self.process.start(sys.executable, ['-B', '-m', 'src.mcp_adapter.availability'])

    def _resolved(self):
        resolver, self._resolver = self._resolver, None
        status = resolver.status
        self.command, self._manifest = resolver.command, resolver.manifest
        resolver.deleteLater()
        if self._cancelled:
            self._stop('cancelled')
        elif status != 'available':
            self._stop(status)
        else:
            self.process.setWorkingDirectory(str(Path(self.command[0]).parent))
            self.timer.start(self.TIMEOUT_MS)
            self.process.start(self.command[0], ['--probe'])

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
                if self._manifest is not None and candidate == 'available':
                    fields = ('component', 'version', 'build_id', 'source_commit', 'sdk_version')
                    if parsed.get('frozen') is not True or any(
                            parsed.get(key) != self._manifest.get(key) for key in fields):
                        result = 'incompatible_component'
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
        if status != 'available':
            self.command = None
        self.finished.emit(status)

    def cancel(self):
        self._cancelled = True
        # Keep ownership until the resolver returns; never kill a hashing thread.
        if self._resolver is None:
            self._stop('cancelled')
        else:
            self._resolver.cancelled.set()
