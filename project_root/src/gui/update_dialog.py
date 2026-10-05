"""Explicit release review, integrity-checked download and separately confirmed exit."""
import sys
from PyQt6 import sip
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QVBoxLayout, QScrollArea, QWidget, QFrame,
                             QPlainTextEdit, QApplication)
from .i18n import msg, language_manager, Message
from .i18n_widgets import (QDialog, QLabel, QPushButton, QMessageBox, QProgressBar,
                          QDialogButtonBox, ResponsiveDialogButtonBox, ResponsiveActionLabels)
from .update_operation import UpdateOperation
from ..application import app_updates


ERROR_MESSAGES = {
    'cancelled': 'Operación cancelada. No se instaló ninguna actualización.',
    'offline': 'No se pudo conectar con GitHub. Revisa la conexión y vuelve a intentarlo.',
    'network_error': 'No se pudo conectar con GitHub. Revisa la conexión y vuelve a intentarlo.',
    'timeout': 'GitHub no respondió a tiempo. Vuelve a intentarlo más tarde.',
    'rate_limited': 'GitHub limitó las consultas. Vuelve a intentarlo más tarde.',
    'invalid_metadata': 'La publicación no cumple el formato seguro esperado. No se descargó ni ejecutó un instalador.',
    'invalid_release': 'La publicación no cumple el formato seguro esperado. No se descargó ni ejecutó un instalador.',
    'invalid_url': 'Se rechazó una dirección de descarga no permitida. No se ejecutó un instalador.',
    'unsafe_url': 'Se rechazó una dirección de descarga no permitida. No se ejecutó un instalador.',
    'integrity_error': 'El instalador no coincide con el tamaño o SHA-256 esperado. No se ejecutó y debe descargarse de nuevo.',
    'checksum_mismatch': 'El instalador no coincide con el tamaño o SHA-256 esperado. No se ejecutó y debe descargarse de nuevo.',
    'too_large': 'La respuesta supera el límite permitido. No se ejecutó un instalador.',
    'invalid_version': 'No se pudo verificar la versión instalada. No es posible compararla de forma segura.',
    'invalid_identity': 'No se pudo verificar la versión instalada. No es posible compararla de forma segura.',
    'no_installer': 'Esta publicación no incluye un instalador Windows compatible con SHA-256 verificable.',
    'unverifiable_installer': 'Esta publicación no incluye un instalador Windows compatible con SHA-256 verificable.',
    'storage_error': 'No se pudo guardar la descarga temporal. Revisa el espacio y los permisos y vuelve a intentarlo.',
    'runtime_error': 'No se pudo completar la operación. No se ejecutó un instalador. Vuelve a intentarlo.',
}

ERROR_MESSAGES.update({
    'invalid_asset': ERROR_MESSAGES['invalid_metadata'],
    'invalid_response': ERROR_MESSAGES['invalid_metadata'],
    'size_limit': ERROR_MESSAGES['too_large'],
    'metadata_limit': ERROR_MESSAGES['too_large'],
    'installer_unavailable': ERROR_MESSAGES['no_installer'],
})


class InstallConfirmation(QDialog):
    """Long consequential consent keeps both explicit actions on screen."""
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(msg('Confirmar instalación'))
        layout = QVBoxLayout(self)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setTabChangesFocus(True)
        self.details.setAccessibleName(str(msg('Detalles de la instalación')))
        self._text_message = text
        self.details.setPlainText(str(text))
        language_manager().changed.connect(self._language_changed)
        layout.addWidget(self.details, 1)
        self.buttons = ResponsiveDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Yes).setText(msg('Guardar, cerrar e instalar'))
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        cancel = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel.setDefault(True)
        cancel.setFocus(Qt.FocusReason.TabFocusReason)
        # The complete body scrolls; the responsive action footer never does.
        available = self.screen().availableGeometry()
        self.resize(min(620, max(320, available.width() - 32)),
                    min(520, max(260, available.height() - 48)))

    def _language_changed(self):
        scroll = self.details.verticalScrollBar().value()
        self.details.setAccessibleName(str(msg('Detalles de la instalación')))
        self.details.setPlainText(self._text_message.render() if isinstance(self._text_message, Message)
                                  else str(self._text_message))
        self.details.verticalScrollBar().setValue(scroll)



class UpdateDialog(QDialog):
    def __init__(self, window, parent=None):
        super().__init__(parent or window)
        self.window = window
        self.release = None
        # Shared ownership cell survives native widget deletion without keeping
        # the widget alive. Only a user-confirmed transfer clears this cell.
        self._download_owner = [None]
        owner = self._download_owner
        self.destroyed.connect(lambda: app_updates.discard_download(owner[0])
                               if owner[0] is not None else None)
        self._pending_close = None
        self._closed = False
        self._confirmation = None
        self._cancelling = False
        self.setWindowTitle(msg('Actualizaciones de SORTH'))
        self.resize(640, 580)
        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)
        try:
            identity = app_updates.current_identity()
            current = msg('Versión instalada: {version}\nCompilación: {build}',
                          version=identity.version, build=identity.build_id or msg('Código fuente'))
        except app_updates.UpdateError:
            current = msg(ERROR_MESSAGES['invalid_identity'])
        self.identity_label = self._label(current)
        layout.addWidget(self.identity_label)
        layout.addWidget(self._label(msg('Solo se consultan publicaciones estables de RodrigoUC/SORTH-AI en GitHub. GitHub recibe los datos normales de conexión, como la dirección IP; no se envían horarios ni archivos de sesión.')))
        self.status_label = self._label(msg('Todavía no se han buscado actualizaciones.'))
        self.status_label.setAccessibleName(msg('Estado de la actualización'))
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.status_label)
        self.check_button = QPushButton(msg('Buscar actualizaciones'))
        self.check_button.clicked.connect(self.check)
        layout.addWidget(self.check_button)
        self.release_label = self._label('')
        self.release_label.hide()
        layout.addWidget(self.release_label)
        self.notes = QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setTabChangesFocus(True)
        self.notes.setAccessibleName(msg('Notas de la publicación'))
        self.notes.setMinimumHeight(100)
        self.notes.hide()
        layout.addWidget(self.notes)
        self.page_button = QPushButton(msg('Ver publicación oficial'))
        self.page_button.clicked.connect(self._open_page)
        self.page_button.hide()
        layout.addWidget(self.page_button)
        self.download_button = QPushButton(msg('Descargar instalador y verificar SHA-256'))
        self.download_button.clicked.connect(self._download)
        self.download_button.hide()
        layout.addWidget(self.download_button)
        self.install_button = QPushButton(msg('Guardar, cerrar SORTH e instalar…'))
        self.install_button.clicked.connect(self._verify_for_install)
        self.install_button.hide()
        layout.addWidget(self.install_button)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setAccessibleName(msg('Progreso de la descarga'))
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        self.cancel_button = QPushButton(msg('Cancelar operación'))
        self.cancel_button.clicked.connect(self._cancel)
        self.cancel_button.hide()
        layout.addWidget(self.cancel_button)
        layout.addWidget(self._label(msg('SHA-256 comprueba que la descarga coincide con los metadatos de GitHub; no autentica al editor. Los instaladores actuales no están firmados. No omitas avisos de SmartScreen o Defender.')))
        if not self._can_install():
            layout.addWidget(self._label(msg('La instalación desde esta ventana solo está disponible en la aplicación empaquetada para Windows. Puedes consultar la publicación oficial.')))
        layout.addStretch(1)
        self.buttons = ResponsiveDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self._responsive = ResponsiveActionLabels(self.scroll, [self.check_button, self.page_button,
            self.download_button, self.install_button, self.cancel_button], self)
        self.operation = UpdateOperation(self)
        self.operation.finished.connect(self._finished)
        self.operation.progress.connect(self._progress)
        QApplication.instance().focusChanged.connect(self._scroll_to_focus)
        language_manager().changed.connect(self._language_changed)
        self.check_button.setFocus(Qt.FocusReason.TabFocusReason)

    @property
    def download(self):
        return self._download_owner[0]

    @download.setter
    def download(self, value):
        self._download_owner[0] = value

    def _language_changed(self):
        if self.release is not None and not self.release.body:
            self.notes.setPlainText(str(msg('Esta publicación no incluye notas de cambios.')))

    @staticmethod
    def _label(text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        return label

    @staticmethod
    def _can_install():
        return sys.platform == 'win32' and bool(getattr(sys, 'frozen', False))

    def _scroll_to_focus(self, previous, focused):
        if self.isVisible() and focused is not None and self.scroll.widget().isAncestorOf(focused):
            self.scroll.ensureWidgetVisible(focused, 0, 12)
            # Native text-edit focus handling can adjust scrolling afterwards.
            QTimer.singleShot(0, self._reveal_current_focus)

    def _reveal_current_focus(self):
        if sip.isdeleted(self):
            return
        focused = QApplication.focusWidget()
        if self.isVisible() and focused is not None and self.scroll.widget().isAncestorOf(focused):
            self.scroll.ensureWidgetVisible(focused, 0, 12)
            if isinstance(focused, QPlainTextEdit):
                # ensureWidgetVisible uses the text caret, not the whole notes
                # editor. Reveal its actual rectangle for keyboard inspection.
                center = focused.mapTo(self.scroll.widget(), focused.rect().center())
                self.scroll.ensureVisible(center.x(), center.y(),
                    min(focused.width() // 2, self.scroll.viewport().width() // 2),
                    min(focused.height() // 2 + 12, self.scroll.viewport().height() // 2))

    def _forget_download(self):
        if self.download is not None:
            app_updates.discard_download(self.download)
            self.download = None
        self._download_owner[0] = None
        self.install_button.hide()

    def _busy(self, value):
        for button in (self.check_button, self.page_button, self.download_button, self.install_button):
            button.setEnabled(not value)
        self.cancel_button.setVisible(value)
        self.cancel_button.setEnabled(value)
        self._cancelling = False

    def check(self):
        if self._closed or self.operation.active or self._pending_close is not None:
            return
        self._forget_download()
        self.release = None
        for widget in (self.release_label, self.notes, self.page_button, self.download_button):
            widget.hide()
        self.notes.clear()
        self.status_label.setText(msg('Consultando publicaciones oficiales…'))
        self._busy(True)
        self.operation.start('check')

    def _open_page(self):
        if not self._closed and self.release is not None and not self.operation.active:
            # Backend validation fixes this to the official repository/tag.
            if not QDesktopServices.openUrl(QUrl(self.release.page_url)):
                self.status_label.setText(msg('No se pudo abrir el navegador. Vuelve a intentarlo.'))

    def _download(self):
        if (self._closed or self.operation.active or self._pending_close is not None or not self._can_install()
                or self.release is None or self.release.installer is None):
            return
        if not self._confirm_download() or self._closed or self._pending_close is not None:
            return
        self._forget_download()
        self.status_label.setText(msg('Descargando el instalador oficial y verificando su integridad…'))
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self._busy(True)
        self.operation.start('download', self.release)

    def _confirm_download(self):
        confirmation = QMessageBox(self)
        confirmation.setWindowTitle(msg('Confirmar descarga'))
        confirmation.setIcon(QMessageBox.Icon.Information)
        confirmation.setTextFormat(Qt.TextFormat.PlainText)
        confirmation.setText(msg('Descargar SORTH {version} desde la publicación oficial de RodrigoUC/SORTH-AI en GitHub ({size} bytes). Se guardará temporalmente y se verificará su SHA-256. El instalador no está firmado y no se ejecutará hasta otra confirmación. ¿Descargar ahora?', version=self.release.version, size=self.release.installer.size))
        confirmation.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        confirmation.button(QMessageBox.StandardButton.Yes).setText(msg('Descargar instalador'))
        confirmation.setDefaultButton(QMessageBox.StandardButton.Cancel)
        return self._exec_confirmation(confirmation)

    def _progress(self, received, total):
        if not self._cancelling and self._pending_close is None and total > 0:
            self.progress_bar.setValue(min(100, max(0, received * 100 // total)))

    def _verify_for_install(self):
        if (self._closed or self.operation.active or self._pending_close is not None or self.download is None
                or not self._can_install()):
            return
        self.status_label.setText(msg('Volviendo a verificar el instalador antes de confirmar…'))
        self._busy(True)
        self.operation.start('verify', self.download)

    def _exec_confirmation(self, confirmation):
        self._confirmation = confirmation
        try:
            answer = confirmation.exec()
            accepted = (QDialog.DialogCode.Accepted if isinstance(confirmation, InstallConfirmation)
                        else QMessageBox.StandardButton.Yes)
            return not sip.isdeleted(self) and not self._closed and answer == accepted
        finally:
            self._confirmation = None
            if not sip.isdeleted(confirmation):
                confirmation.deleteLater()

    def _confirm_install(self):
        confirmation = InstallConfirmation(msg('Se instalará SORTH {version} desde RodrigoUC/SORTH-AI. El archivo coincide con el SHA-256 publicado en GitHub, pero no tiene firma de editor.\n\nSORTH guardará la sesión y creará una copia SQLite validada antes de cerrarse. Si no puede hacerlo, no iniciará el instalador. Conserva además una copia de tus archivos y preferencias; una versión nueva puede cambiar el formato de datos. Cierra las otras instancias de SORTH.\n\nEl instalador se abrirá después de cerrar esta aplicación y requerirá tus pasos en Windows. No omitas advertencias de SmartScreen o Defender. ¿Guardar, cerrar e iniciar el instalador?', version=self.release.version), self)
        return self._exec_confirmation(confirmation)

    def _finished(self, status, result):
        self._busy(False)
        self.progress_bar.hide()
        if self._pending_close is not None:
            if status == 'download' and result is not None:
                app_updates.discard_download(result)
            close, self._pending_close = self._pending_close, None
            self.done(close)
            return
        if status == 'check':
            self._show_release(result)
        elif status == 'download':
            self.download = result
            self.status_label.setText(msg('Descarga verificada por SHA-256. No se ha instalado nada.'))
            self.install_button.show()
        elif status == 'verify':
            confirmed = self._confirm_install()
            if sip.isdeleted(self) or self._closed:
                return
            if confirmed and self.download is not None:
                self.window._pending_update_installer = self.download
                self.download = None  # Transfer ownership only after explicit confirmation.
                self.done(QDialog.DialogCode.Accepted)
            else:
                self.status_label.setText(msg('Instalación cancelada. La sesión sigue abierta.'))
        else:
            self.status_label.setText(msg(ERROR_MESSAGES.get(status, ERROR_MESSAGES['runtime_error'])))
            if status not in ('cancelled',):
                self._forget_download()

    def _show_release(self, result):
        self.release = result.release
        if result.state == 'no_releases':
            self.status_label.setText(msg('Todavía no hay publicaciones estables oficiales. No se puede confirmar que esta compilación sea la última.'))
        elif result.state == 'current':
            self.status_label.setText(msg('No hay una versión estable con número mayor que la instalada. Las compilaciones de revisión con el mismo número no se consideran actualizaciones.'))
        else:
            self.status_label.setText(msg('Hay una actualización disponible: {version}', version=self.release.version))
        if self.release is None:
            return
        self.release_label.setText(msg('SORTH {version} · {title}', version=self.release.version, title=self.release.title))
        self.release_label.show()
        self.notes.setPlainText(self.release.body or str(msg('Esta publicación no incluye notas de cambios.')))
        self.notes.show()
        self.page_button.show()
        can_download = result.state == 'available' and self.release.installer is not None and self._can_install()
        self.download_button.setVisible(can_download)
        if result.state == 'available' and self.release.installer is None:
            self.status_label.setText(msg('SORTH {version} está publicado, pero no incluye un instalador Windows compatible con SHA-256 verificable. Consulta las notas oficiales.', version=self.release.version))

    def _cancel(self):
        if self.operation.active:
            self._cancelling = True
            self.cancel_button.setEnabled(False)
            self.status_label.setText(msg('Cancelando la operación de forma segura…'))
            self.operation.cancel()

    def done(self, result):
        self._closed = True
        if self._confirmation is not None:
            self._confirmation.reject()
        if self.operation.active:
            self._pending_close = result
            self.buttons.setEnabled(False)
            self._cancel()
            return
        self._forget_download()
        super().done(result)

    def closeEvent(self, event):
        if self.operation.active:
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)
