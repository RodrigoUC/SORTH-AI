"""Transactional native settings: Cancel never changes preferences or project data."""
from PyQt6.QtWidgets import QVBoxLayout, QScrollArea, QWidget, QFrame
from .i18n_widgets import QDialog, QLabel, QCheckBox, QDialogButtonBox, QMessageBox, QPushButton
from .i18n import msg
from .features import FEATURES, McpPreferenceConflict
from PyQt6.QtCore import QSignalBlocker
from .mcp_availability import McpAvailabilityProbe
from ..scheduling.teaching_resources import RESOURCE_KINDS


class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        window._features.refresh()
        self.setWindowTitle(msg('Configuración'))
        self.resize(620, 620)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        intro = QLabel(msg('Las funciones opcionales empiezan desactivadas. Los cambios se guardan en este equipo.'))
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.recovery_label = QLabel(msg('La configuración opcional no se puede leer. Puedes conservar el archivo original y restablecer solo estas herramientas.'))
        self.recovery_label.setWordWrap(True)
        self.recovery_label.setVisible(bool(window._features.load_error))
        layout.addWidget(self.recovery_label)
        self.recover_button = QPushButton(msg('Conservar original y restablecer herramientas'))
        self.recover_button.setVisible(bool(window._features.load_error))
        self.recover_button.clicked.connect(self.recover_preferences)
        layout.addWidget(self.recover_button)
        self.mcp_status = None
        self.mcp_probe = McpAvailabilityProbe(self)
        self.mcp_probe.finished.connect(self._mcp_checked)
        self.controls = {}
        for feature in FEATURES:
            control = QCheckBox(msg(feature.title))
            control.setAccessibleName(msg(feature.title))
            control.setAccessibleDescription(msg(feature.description))
            control.setChecked(window.resources.catalog(feature.key).enabled if feature.key in RESOURCE_KINDS
                               else window._features.enabled(feature.key))
            layout.addWidget(control)
            description = QLabel(msg(feature.description))
            description.setWordWrap(True)
            description.setObjectName('mutedText')
            layout.addWidget(description)
            self.controls[feature.key] = control
            if feature.key == 'mcp_server':
                self.mcp_status_label = QLabel(msg('Disponibilidad MCP sin verificar en este entorno.'))
                self.mcp_status_label.setWordWrap(True)
                layout.addWidget(self.mcp_status_label)
                self.mcp_check_button = QPushButton(msg('Verificar disponibilidad local de MCP'))
                self.mcp_check_button.clicked.connect(self._check_mcp)
                layout.addWidget(self.mcp_check_button)
                control.toggled.connect(lambda checked: self._check_mcp() if checked else None)
        self.calendar_button = QPushButton(msg('Guardar configuración y editar calendario'))
        self.calendar_button.setEnabled(window._features.enabled('project_calendar') and not window._busy and not window._restore_failed)
        self.calendar_button.clicked.connect(self.open_calendar)
        self.controls['project_calendar'].toggled.connect(lambda enabled: self.calendar_button.setEnabled(enabled and not window._busy and not window._restore_failed))
        layout.addWidget(self.calendar_button)
        note = QLabel(msg('Desactivar herramientas oculta sus controles y conserva sus datos. Desactivar recursos retira esas restricciones después de confirmar y regenerar. Las reglas básicas siguen activas.'))
        note.setWordWrap(True)
        layout.addWidget(note)
        mcp = QLabel(msg('Desactivar MCP bloquea nuevos inicios y solicitudes y descarta resultados pendientes. El cliente cierra el proceso stdio; una tarea en curso puede tardar hasta 10 segundos. La verificación solo comprueba este entorno; el EXE estándar no incluye MCP. Consulta MCP_OPTIONAL.md para un entorno Python separado.'))
        mcp.setWordWrap(True)
        mcp.setObjectName('mutedText')
        layout.addWidget(mcp)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)

    def _check_mcp(self):
        if self.mcp_probe.active:
            return
        previous = self.window._features.enabled('mcp_server')
        self.window._features.refresh()
        current = self.window._features.enabled('mcp_server')
        if current != previous:
            with QSignalBlocker(self.controls['mcp_server']):
                self.controls['mcp_server'].setChecked(current)
        self.mcp_status = 'checking'
        self.mcp_check_button.setEnabled(False)
        self.mcp_status_label.setText(msg('Verificando componentes locales de MCP…'))
        self.mcp_probe.start()

    def _mcp_checked(self, status):
        self.mcp_status = status
        self.mcp_check_button.setEnabled(True)
        messages = {
            'available': 'MCP disponible en este entorno. El cliente inicia el servidor; Guardar no lo inicia.',
            'missing_sdk': 'Falta el SDK MCP opcional en este entorno. No se ha instalado nada.',
            'incompatible_sdk': 'Versión MCP incompatible. Se requiere mcp 1.30.0; no se ha cambiado nada.',
            'frozen_unsupported': 'Este EXE no incluye el servidor MCP opcional. Usa el código fuente y un entorno Python separado según MCP_OPTIONAL.md.',
            'runtime_error': 'No se pudieron cargar los componentes MCP. Revisa el entorno siguiendo MCP_OPTIONAL.md.',
            'timeout': 'La verificación MCP agotó el tiempo. Puedes volver a intentarlo.',
            'cancelled': 'Verificación MCP cancelada.',
        }
        self.mcp_status_label.setText(msg(messages[status]))

    def done(self, result):
        self.mcp_probe.cancel()
        super().done(result)

    def open_calendar(self):
        self.accept()
        if self.result() == QDialog.DialogCode.Accepted:
            self.window._show_calendar()

    def recover_preferences(self):
        answer = QMessageBox.question(self, msg('Configuración'), msg(
            'Se conservará el archivo original y se restablecerán las herramientas opcionales. Los parámetros de recursos de la sesión, horarios, fijaciones y escenarios no cambian. ¿Continuar?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.window._features.recover_defaults({kind: self.window.resources.catalog(kind).enabled
                                                       for kind in RESOURCE_KINDS})
        except (OSError, ValueError):
            self.recovery_label.setVisible(bool(self.window._features.load_error))
            self.recover_button.setVisible(bool(self.window._features.load_error))
            QMessageBox.warning(self, msg('Configuración'), msg('No se pudo guardar la configuración. Revisa los permisos e inténtalo de nuevo.'))
            return
        for key, control in self.controls.items():
            control.setChecked(self.window._features.enabled(key))
        self.window._apply_feature_preferences()
        self.recovery_label.hide()
        self.recover_button.hide()

    def accept(self):
        values = {key: control.isChecked() for key, control in self.controls.items()}
        if (values['mcp_server'] and not self.window._features.enabled('mcp_server')
                and self.mcp_status != 'available'):
            QMessageBox.warning(self, msg('Configuración'), msg('Verifica que MCP esté disponible antes de activarlo. No se han guardado cambios.'))
            return
        if (self.window._features.enabled('pinned_sessions') and not values['pinned_sessions']
                and self.window.pinned_group_ids):
            answer = QMessageBox.question(self, msg('Sesiones fijadas'), msg(
                'Se ocultarán los controles para fijar sesiones. Las sesiones ya fijadas seguirán condicionando la generación. Para cambiarlas, vuelve a activar esta función. ¿Guardar configuración?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                return
        changes = self.window._resource_parameter_changes(values)
        if changes and (self.window.current_schedule or any(
                self.window.resources.catalog(kind).memberships for kind in changes)):
            answer = QMessageBox.question(self, msg('Cambiar parámetros de recursos'), msg(
                'Al desactivar un parámetro, sus recursos dejan de limitar nuevos horarios. Los registros se conservan. Cambiar estos parámetros retira el resultado actual y desfija sus sesiones; deberá regenerarlo. ¿Continuar?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                return
        if self.window._busy or self.window._restore_failed:
            QMessageBox.warning(self, msg('Configuración'), msg('Espera a que termine la operación o recupera la sesión antes de guardar la configuración.'))
            return
        if values['mcp_server'] != self.window._features.enabled('mcp_server') and changes:
            QMessageBox.warning(self, msg('Configuración'), msg('Guarda los cambios de recursos y el permiso MCP por separado. No se han guardado cambios.'))
            return
        previous = self.window._features.values()
        try:
            self.window._features.save(values)
            if changes and not self.window._apply_resource_parameters(values):
                try:
                    self.window._features.save(previous)
                except (OSError, ValueError) as error:
                    detail = msg('La sesión y sus parámetros de recursos no cambiaron. Algunas preferencias de herramientas se guardaron y no se pudieron restaurar. Recupere la configuración antes de continuar. {detail}', detail=str(error))
                    self.window._features.load_error = str(detail)
                    self.window._view_recovery_failure(detail, committed=False)
                    self.recovery_label.show()
                    self.recover_button.show()
                    QMessageBox.warning(self, msg('Configuración'), detail)
                return
        except McpPreferenceConflict:
            with QSignalBlocker(self.controls['mcp_server']):
                self.controls['mcp_server'].setChecked(self.window._features.enabled('mcp_server'))
            QMessageBox.warning(self, msg('Configuración'), msg('El permiso MCP cambió fuera de este diálogo. Se ha actualizado su casilla; revisa los cambios antes de guardar.'))
            return
        except (OSError, ValueError):
            self.recovery_label.setVisible(bool(self.window._features.load_error))
            self.recover_button.setVisible(bool(self.window._features.load_error))
            QMessageBox.warning(self, msg('Configuración'), msg('No se pudo guardar la configuración. Revisa los permisos e inténtalo de nuevo.'))
            return
        try:
            self.window._apply_feature_preferences()
        except Exception as error:
            # Preferences (and any resource transaction) are already accepted.
            # A late widget failure is recovery, never a failed-save claim.
            self.window._committed_view_failure(error)
        super().accept()
