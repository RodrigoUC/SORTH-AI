"""Latest-request-wins import coordinator. All GUI access occurs on Qt's thread."""
from PyQt6.QtCore import QObject, QTimer, Qt
from .import_worker import ImportWorker
from .import_preview_dialog import ImportPreviewDialog
from .i18n import msg, join_messages
from .i18n_widgets import QMessageBox, QDialog
from ..infrastructure.excel_reader import ExcelImportError


class ImportController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.token = 0
        self.worker = None
        self.pending = None
        self.active = False
        self.closing = False
        self.review = None
        self.retained_pins = set()

    def start(self, path):
        if self.closing:
            return
        self.cancel(announce=False, restore_controls=False)
        self.active = True
        self.window._set_import_busy(True)
        self.window.status_bar.showMessage(msg('Leyendo y validando Excel… La sesión actual se conserva.'))
        self._enqueue(path)

    def _enqueue(self, path, previous=None):
        self.pending = (self.token, path, previous)
        if self.worker is None:
            self._launch()

    def _launch(self):
        if self.pending is None or self.closing:
            return
        token, path, previous = self.pending
        self.pending = None
        worker = self.worker = ImportWorker(token, path, previous, self)
        worker.result_ready.connect(self._result)
        worker.failed.connect(self._error)
        worker.finished.connect(self._finished)
        worker.start()

    def _finished(self):
        worker = self.worker
        self.worker = None
        worker.deleteLater()
        if self.closing:
            QTimer.singleShot(0, self.window.close)
        else:
            self._launch()

    def cancel(self, *, announce=True, restore_controls=True):
        self.token += 1
        self.pending = None
        self.active = False
        if self.worker is not None:
            self.worker.requestInterruption()
        if self.review is not None:
            self.review.reject()
        if restore_controls:
            self.window._set_import_busy(False)
        if announce:
            self.window.status_bar.showMessage(msg('Importación cancelada. La sesión anterior se conserva.'))

    def _current(self, token):
        return self.active and not self.closing and token == self.token

    def _result(self, token, candidate, verified):
        if not self._current(token):
            return
        if verified:
            try:
                self.window._commit_import(candidate, self.retained_pins)
            except Exception as error:
                self._error(token, error)
                return
            self.active = False
            self.window._set_import_busy(False)
            return
        # Changed files enter the complete review flow again, never a silent merge.
        if self.worker.previous is not None:
            self.window.status_bar.showMessage(msg('El archivo cambió. Revise la nueva versión validada antes de importar.'))
        if not self._review_candidate(token, candidate):
            if self._current(token):
                self.cancel()
            return
        if self._current(token):
            self.window.status_bar.showMessage(msg('Comprobando que el archivo no cambió…'))
            self._enqueue(candidate.path, candidate)

    def _review_candidate(self, token, candidate):
        window = self.window
        imported = candidate.imported
        if imported.warnings:
            review = self.review = QMessageBox(window)
            review.setWindowTitle(msg('Revisar importación'))
            review.setIcon(QMessageBox.Icon.Warning)
            review.setTextFormat(Qt.TextFormat.PlainText)
            review.setText(msg('Avisos del archivo: {count}', count=len(imported.warnings)))
            review.setInformativeText(join_messages('\n', (item.render(msg) for item in imported.warnings[:3])) + msg('\n\nRevise los detalles antes de continuar. Cancelar conserva la sesión actual.'))
            review.setDetailedText(join_messages('\n', (item.render(msg) for item in imported.warnings)))
            review.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            review.setDefaultButton(QMessageBox.StandardButton.Cancel)
            review.setButtonText(QMessageBox.StandardButton.Ok, msg('Importar con avisos'))
            review.setButtonText(QMessageBox.StandardButton.Cancel, msg('Cancelar'))
            accepted = review.exec() == QMessageBox.StandardButton.Ok
            self.review = None
            review.deleteLater()
            if not accepted or not self._current(token):
                return False
        # Use the existing pin guard in review-only mode. Cancellation/verification
        # failures must not clear pins before a durable import has succeeded.
        errors = window._pin_input_errors(imported.courses, imported.classrooms, {})
        if not window._confirm_pin_inputs(courses=imported.courses, classrooms=imported.classrooms,
                                          restrictions={}, commit=False):
            return False
        if not self._current(token):
            return False
        self.retained_pins = set() if errors else set(window.pinned_group_ids)
        if window._features.enabled('import_diff_preview'):
            review = self.review = ImportPreviewDialog(window, candidate, self.retained_pins)
            accepted = review.exec() == QDialog.DialogCode.Accepted
            self.review = None
            review.deleteLater()
            if not accepted or not self._current(token):
                return False
        return True

    def _error(self, token, error):
        if not self._current(token):
            return
        self.cancel(announce=False)
        failed_token = self.token
        QMessageBox.critical(self.window, msg('Error'), msg('Error al cargar archivo Excel:\n{p1}',
                             p1=error.render(msg) if isinstance(error, ExcelImportError) else str(error)))
        if self.token == failed_token and not self.closing:
            self.window.status_bar.showMessage(msg('No se cargó el archivo. La sesión anterior se conserva.'))

    def prepare_close(self):
        self.closing = True
        if self.active or self.worker is not None:
            self.cancel(announce=False)
        if self.worker is not None:
            self.window.status_bar.showMessage(msg('Cancelando importación antes de cerrar…'))
            return False
        return True
