"""One opt-in, read-only update check owned by the visible main window."""
from PyQt6.QtCore import QObject, QTimer

from .i18n import msg
from .update_operation import UpdateOperation


class UpdateStartupNotice(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.operation = UpdateOperation(self)
        self.operation.finished.connect(self._finished)
        self.closing = False
        self._available_version = None
        self._notice_timer = QTimer(self)
        self._notice_timer.setInterval(500)
        self._notice_timer.timeout.connect(self._show_when_idle)

    def start(self):
        return self.operation.start('check')

    def _finished(self, status, result):
        if self.closing:
            # Cancellation drains asynchronously. Even a successful result
            # queued before close is discarded, then close is retried safely.
            QTimer.singleShot(0, self.window.close)
            return
        if status == 'check' and result.state == 'available' and result.release is not None:
            self._available_version = result.release.version
            self._show_when_idle()

    def _show_when_idle(self):
        if (self.closing or self._available_version is None
                or not self.window._features.enabled('auto_update_check')):
            self._notice_timer.stop()
            self._available_version = None
            return
        if (self.window._busy or self.window._restore_failed or self.window._save_error
                or self.window._scenario_comparison_error):
            self._notice_timer.start()
            return
        self._notice_timer.stop()
        self.window.status_bar.showMessage(msg(
            'SORTH {version} está disponible. Abre Configuración → Buscar actualizaciones para revisarlo.',
            version=self._available_version))
        self._available_version = None

    def prepare_close(self) -> bool:
        self.closing = True
        self._available_version = None
        self._notice_timer.stop()
        if self.operation.active:
            self.operation.cancel()
            return False
        return True


def start_update_notice(window):
    """Called solely by gui_app.main after show(), using committed preferences."""
    existing = getattr(window, '_update_startup', None)
    if existing is not None:
        return existing
    if not window._features.enabled('auto_update_check'):
        return None
    controller = UpdateStartupNotice(window)
    window._update_startup = controller
    controller.start()
    return controller
