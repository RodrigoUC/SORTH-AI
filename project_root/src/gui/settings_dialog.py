"""Transactional preferences plus a separately confirmed local MCP preparation."""
from PyQt6.QtWidgets import QVBoxLayout, QScrollArea, QWidget, QFrame, QSizePolicy, QApplication
from .i18n_widgets import QDialog, QLabel, QCheckBox, QDialogButtonBox, QMessageBox, QPushButton, ResponsiveActionLabels, ResponsiveDialogButtonBox, QComboBox
from .i18n import msg
from .features import FEATURES, McpPreferenceConflict
from PyQt6.QtCore import QSignalBlocker, Qt
from .mcp_availability import McpAvailabilityProbe
from .mcp_preparation import McpPreparation
from .mcp_client_help import McpClientHelp
from ..application import mcp_component
from ..application.mcp_preferences import enabled as mcp_permission_enabled
from ..scheduling.teaching_resources import RESOURCE_KINDS


class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        window._features.refresh()
        self.setWindowTitle(msg('Configuración'))
        self.resize(680, 620)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        header = QFrame()
        header.setObjectName('settingsHeader')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(4)
        title = QLabel(msg('Configuración'))
        title.setObjectName('settingsTitle')
        title.setAccessibleDescription(msg('Activa solo las herramientas que necesites. Las funciones opcionales empiezan desactivadas.'))
        header_layout.addWidget(title)
        self.intro_label = intro = QLabel(msg('Activa solo las herramientas que necesites. Las funciones opcionales empiezan desactivadas.'))
        intro.setObjectName('settingsSubtitle')
        intro.setWordWrap(True)
        header_layout.addWidget(intro)
        outer.addWidget(header)

        self.section_selector = QComboBox()
        self.section_selector.setAccessibleName(msg('Sección de configuración'))
        self.section_selector.setAccessibleDescription(msg('Elige General, Recursos académicos, Herramientas avanzadas o Conexión MCP. Los cambios se conservan al cambiar de sección.'))
        self.section_selector.setToolTip(msg('Elige General, Recursos académicos, Herramientas avanzadas o Conexión MCP. Los cambios se conservan al cambiar de sección.'))
        self.section_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.section_selector.setMinimumContentsLength(1)
        self.section_selector.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        outer.addWidget(self.section_selector)

        self.scroll = scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName('settingsContent')
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        self.recovery_label = QLabel(msg('La configuración opcional no se puede leer. Puedes conservar el archivo original y restablecer solo estas herramientas.'))
        self.recovery_label.setWordWrap(True)
        self.recovery_label.setVisible(bool(window._features.load_error))
        layout.addWidget(self.recovery_label)
        self.recover_button = QPushButton(msg('Conservar original y restablecer herramientas'))
        self.recover_button.setVisible(bool(window._features.load_error))
        self.recover_button.clicked.connect(self.recover_preferences)
        layout.addWidget(self.recover_button)
        self.mcp_status = None
        self.mcp_command = None
        self._pending_close = None
        self.mcp_preparation = McpPreparation(self)
        self.mcp_preparation.progress.connect(self._mcp_progress)
        self.mcp_preparation.finished.connect(self._mcp_prepared)
        self.mcp_probe = McpAvailabilityProbe(self)
        self.mcp_probe.finished.connect(self._mcp_checked)
        self.controls = {}
        descriptions = {}
        for feature in FEATURES:
            control = QCheckBox(msg(feature.title))
            control.setAccessibleName(msg(feature.title))
            control.setAccessibleDescription(msg(feature.description))
            control.setChecked(window.resources.catalog(feature.key).enabled if feature.key in RESOURCE_KINDS
                               else window._features.enabled(feature.key))
            description = QLabel(msg(feature.description))
            description.setWordWrap(True)
            description.setObjectName('mutedText')
            self.controls[feature.key] = control
            descriptions[feature.key] = description
        self._saved_values = {key: control.isChecked() for key, control in self.controls.items()}
        self.sections = {}
        self.section_features = {
            'general': ('import_diff_preview', 'undo_redo', 'placement_suggestions', 'pinned_sessions'),
            'resources': ('teacher', 'student_group', 'student'),
            'advanced': ('project_scenarios', 'bulk_operations', 'project_calendar'),
            'mcp': ('mcp_server',),
        }
        sections = (
            ('general', 'General', 'Revisa cambios y organiza las sesiones del horario.'),
            ('resources', 'Recursos académicos', 'Define qué recursos deben evitar cruces de horario.'),
            ('advanced', 'Herramientas avanzadas', 'Organiza escenarios, sesiones y parámetros del calendario.'),
            ('mcp', 'Conexión MCP', 'Prepara el complemento, guarda el permiso local y configura tu cliente.'),
        )
        for key, label, summary in sections:
            self.section_selector.addItem(msg(label), key)
            section = QWidget()
            section_layout = QVBoxLayout(section)
            # Match the scroll body's width: no hidden inset may invalidate the
            # shared native multiline-action measurement.
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(8)
            self._section_heading(section_layout, msg(label), role='settingsSectionTitle')
            section_summary = QLabel(msg(summary))
            section_summary.setWordWrap(True)
            section_summary.setObjectName('mutedText')
            section_layout.addWidget(section_summary)
            section_layout.addSpacing(6)
            if key == 'mcp':
                self._add_mcp_section(section_layout, self.controls['mcp_server'], descriptions['mcp_server'])
            else:
                for index, feature_key in enumerate(self.section_features[key]):
                    if index:
                        divider = QFrame()
                        divider.setObjectName('settingsDivider')
                        divider.setFixedHeight(1)
                        section_layout.addWidget(divider)
                    section_layout.addWidget(self.controls[feature_key])
                    section_layout.addWidget(descriptions[feature_key])
                    section_layout.addSpacing(6)
            if key == 'advanced':
                self.calendar_button = QPushButton(msg('Guardar configuración y editar calendario'))
                self.calendar_button.setEnabled(window._features.enabled('project_calendar') and not window._busy and not window._restore_failed)
                self.calendar_button.clicked.connect(self.open_calendar)
                self.controls['project_calendar'].toggled.connect(lambda enabled: self.calendar_button.setEnabled(enabled and not window._busy and not window._restore_failed and not self.mcp_preparation.active))
                section_layout.addWidget(self.calendar_button)
            if key in ('resources', 'advanced'):
                note = QLabel(msg('Al desactivar un recurso, sus registros se conservan. Sus restricciones se retiran después de confirmar y regenerar el horario.') if key == 'resources' else msg('Al desactivar una herramienta se ocultan sus controles. Los escenarios, las fijaciones y el calendario guardados se conservan.'))
                note.setWordWrap(True)
                note.setObjectName('settingsNotice')
                section_layout.addSpacing(4)
                section_layout.addWidget(note)
            self.sections[key] = section
            layout.addWidget(section)
        layout.addStretch(1)

        self.save_state = QLabel()
        self.save_state.setObjectName('settingsSaveState')
        self.save_state.setWordWrap(True)
        self.save_state.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.save_state.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.save_state.setAccessibleName(msg('Estado de los cambios de configuración'))
        self.save_state.setToolTip(msg('Guardar aplica las preferencias de todas las secciones en este equipo. Cancelar descarta los cambios de preferencias.'))
        outer.addWidget(self.save_state)
        self.buttons = ResponsiveDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName('primaryAction')
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self._responsive_actions = ResponsiveActionLabels(scroll, [
            *self.controls.values(), self.recover_button, self.calendar_button,
            self.mcp_check_button, self.mcp_prepare_button, self.mcp_cancel_button,
            self.mcp_help_button,
        ], self)
        for control in self.controls.values():
            control.toggled.connect(self._refresh_save_state)
        self.section_selector.currentIndexChanged.connect(self._section_changed)
        self._section_changed()
        self._refresh_mcp_permission()
        self._refresh_save_state()
        # Native tab order follows each section; hidden sections are skipped.
        ordered = [self.section_selector, self.recover_button,
                   *(self.controls[key] for section in ('general', 'resources', 'advanced')
                     for key in self.section_features[section]), self.calendar_button,
                   self.mcp_status_label, self.mcp_check_button, self.mcp_prepare_button,
                   self.mcp_cancel_button, self.controls['mcp_server'],
                   self.mcp_permission_label, self.mcp_help_button, self.save_state,
                   self.buttons.button(QDialogButtonBox.StandardButton.Save),
                   self.buttons.button(QDialogButtonBox.StandardButton.Cancel)]
        for previous, following in zip(ordered, ordered[1:]):
            self.setTabOrder(previous, following)
        QApplication.instance().focusChanged.connect(self._scroll_to_focus)
        self.section_selector.setFocus(Qt.FocusReason.TabFocusReason)

    def _scroll_to_focus(self, previous, focused):
        # Nested section widgets are not direct children of the scroller. Native
        # tab traversal alone may leave their focused control outside the reading
        # viewport. Follow the settled focus change for keyboard and programmatic
        # focus (including the visible cancel action of an MCP operation).
        if (self.isVisible() and focused is not None
                and self.scroll.widget().isAncestorOf(focused)):
            self.scroll.ensureWidgetVisible(focused, 0, 12)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'intro_label'):
            # Reserve actual reading space at short heights without shrinking
            # the user's text. The introduction remains in the title's native
            # accessible description; every section retains its own guidance.
            self.intro_label.setVisible(self.height() >= 520)

    def select_section(self, key):
        """Select a stable section key without discarding any pending choices."""
        index = self.section_selector.findData(key)
        if index >= 0:
            self.section_selector.setCurrentIndex(index)

    def _section_changed(self, *_):
        selected = self.section_selector.currentData()
        for key, section in self.sections.items():
            section.setVisible(key == selected)
        self.scroll.verticalScrollBar().setValue(0)
        self._responsive_actions._rewrap()

    def _refresh_save_state(self, *_):
        if not hasattr(self, 'save_state'):
            return
        # Like the MCP status, this snapshot is presentation only. Do not replace
        # the save transaction's expected generation while showing pending work.
        saved = dict(self._saved_values)
        saved['mcp_server'] = mcp_permission_enabled(self.window._features.path)
        count = sum(control.isChecked() != saved[key] for key, control in self.controls.items())
        self.save_state.setText(msg('Cambios sin guardar: {count}', count=count) if count
                                else msg('Sin cambios por guardar'))
        self.save_state.setProperty('pending', bool(count))
        self.save_state.style().unpolish(self.save_state)
        self.save_state.style().polish(self.save_state)

    @staticmethod
    def _section_heading(layout, text, role='settingsStepTitle'):
        layout.addSpacing(4)
        heading = QLabel(text)
        heading.setObjectName(role)
        heading.setWordWrap(True)
        font = heading.font()
        font.setBold(True)
        heading.setFont(font)
        layout.addWidget(heading)

    def _add_mcp_section(self, layout, control, description):
        self._section_heading(layout, msg('1. Preparar MCP'))
        self.mcp_status_label = QLabel(msg('Disponibilidad MCP sin verificar en este entorno.'))
        self.mcp_status_label.setWordWrap(True)
        self.mcp_status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.mcp_status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.mcp_status_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.mcp_status_label.setAccessibleName(msg('Estado del complemento MCP'))
        layout.addWidget(self.mcp_status_label)
        self.mcp_check_button = QPushButton(msg('Verificar disponibilidad local de MCP'))
        self.mcp_check_button.clicked.connect(self._check_mcp)
        layout.addWidget(self.mcp_check_button)
        self.mcp_prepare_button = QPushButton(msg('Preparar complemento MCP'))
        self.mcp_prepare_button.clicked.connect(self._prepare_mcp)
        layout.addWidget(self.mcp_prepare_button)
        self.mcp_cancel_button = QPushButton(msg('Cancelar preparación MCP'))
        self.mcp_cancel_button.clicked.connect(self._cancel_mcp_operation)
        self.mcp_cancel_button.hide()
        layout.addWidget(self.mcp_cancel_button)
        preparation_note = QLabel(msg('Preparar requiere confirmación y conserva el complemento aunque canceles Configuración. No concede permiso ni conecta clientes.'))
        preparation_note.setWordWrap(True)
        preparation_note.setObjectName('mutedText')
        layout.addWidget(preparation_note)
        self._section_heading(layout, msg('2. Guardar el permiso local'))
        layout.addWidget(control)
        layout.addWidget(description)
        self.mcp_permission_label = QLabel()
        self.mcp_permission_label.setWordWrap(True)
        self.mcp_permission_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.mcp_permission_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.mcp_permission_label)
        control.toggled.connect(self._refresh_mcp_permission)
        control.toggled.connect(lambda checked: self._check_mcp() if checked else None)
        self._section_heading(layout, msg('3. Configurar tu cliente'))
        self.mcp_help_button = QPushButton(msg('Ver guía de conexión'))
        self.mcp_help_button.clicked.connect(self._show_mcp_help)
        layout.addWidget(self.mcp_help_button)
        guide_note = QLabel(msg('Abre instrucciones para OpenCode, Claude Desktop o ChatGPT. La conexión y sus permisos se gestionan en el cliente.'))
        guide_note.setWordWrap(True)
        guide_note.setObjectName('mutedText')
        layout.addWidget(guide_note)

    def _refresh_mcp_permission(self):
        # Read for presentation only: keep the preference store's expected
        # generation intact so a later Save still detects external changes.
        saved = mcp_permission_enabled(self.window._features.path)
        selected = self.controls['mcp_server'].isChecked()
        if selected != saved:
            text = (msg('Cambio pendiente: pulsa Guardar para permitir MCP. Cancelar conserva el permiso desactivado.')
                    if selected else msg('Cambio pendiente: pulsa Guardar para desactivar MCP. El permiso sigue activo hasta guardar.'))
        elif saved:
            text = msg('Permiso guardado: activado. El cliente inicia el servidor; SORTH no lo inicia al guardar.')
        elif self.mcp_status == 'available':
            text = msg('Permiso guardado: desactivado. MCP está listo; marca la casilla y pulsa Guardar si deseas permitirlo.')
        else:
            text = msg('Permiso guardado: desactivado. Prepara y verifica MCP antes de permitirlo y guardar.')
        self.mcp_permission_label.setText(text)
        self._refresh_save_state()
        if hasattr(self, 'buttons'):
            waiting = self.mcp_status == 'checking' and selected and not saved
            save = self.buttons.button(QDialogButtonBox.StandardButton.Save)
            save.setEnabled(not waiting and not self.mcp_preparation.active
                            and self.mcp_status != 'preparing' and self._pending_close is None)
            save.setToolTip(msg('Espera a que termine la verificación MCP antes de guardar el permiso.') if waiting else '')

    def _check_mcp(self):
        self.select_section('mcp')
        if self.mcp_probe.active or self.mcp_preparation.active or self._pending_close is not None:
            return
        previous = self.window._features.enabled('mcp_server')
        self.window._features.refresh()
        current = self.window._features.enabled('mcp_server')
        if current != previous:
            with QSignalBlocker(self.controls['mcp_server']):
                self.controls['mcp_server'].setChecked(current)
        self._refresh_mcp_permission()
        self.mcp_status = 'checking'
        self._refresh_mcp_permission()
        self.mcp_command = None
        self.section_selector.setEnabled(False)
        self.mcp_check_button.setEnabled(False)
        self.mcp_prepare_button.setEnabled(False)
        self.mcp_help_button.setEnabled(False)
        self.mcp_cancel_button.setText(msg('Cancelar verificación MCP'))
        self.mcp_cancel_button.setEnabled(True)
        self.mcp_cancel_button.show()
        self.mcp_status_label.setText(msg('Verificando componentes locales de MCP…'))
        self.mcp_probe.start()

    def _mcp_checked(self, status):
        self.mcp_cancel_button.hide()
        self.mcp_command = self.mcp_probe.command if status == 'available' else None
        self._show_mcp_status(status)
        self._finish_pending_close()

    def _show_mcp_status(self, status):
        self.mcp_status = status
        if status not in {'available', 'prepared'}:
            self.mcp_command = None
        idle = not self.mcp_preparation.active and not self.mcp_probe.active
        self.section_selector.setEnabled(idle)
        self.mcp_check_button.setEnabled(idle)
        self.mcp_prepare_button.setEnabled(idle and status not in {'available', 'prepared'})
        self.mcp_prepare_button.setToolTip(msg('MCP ya está disponible. Usa Verificar disponibilidad local de MCP para comprobarlo de nuevo.') if status in {'available', 'prepared'} else '')
        self.mcp_help_button.setEnabled(idle)
        messages = {
            'available': 'MCP disponible en este entorno. El cliente inicia el servidor; Guardar no lo inicia.',
            'prepared': 'Complemento MCP preparado y verificado. El permiso no ha cambiado. Puedes conectar un cliente y activar MCP por separado con Guardar.',
            'missing_sdk': 'Falta el SDK MCP opcional en este entorno. No se ha instalado nada.',
            'incompatible_sdk': 'Versión MCP incompatible. Se requiere mcp 1.30.0; no se ha cambiado nada.',
            'frozen_unsupported': 'Este EXE no incluye el servidor MCP opcional. Usa el código fuente y un entorno Python separado según MCP_OPTIONAL.md.',
            'missing_bundle': 'El complemento MCP no está incluido en esta compilación. Usa una distribución que lo incluya o consulta la ruta de desarrollo en MCP_OPTIONAL.md.',
            'missing_component': 'El complemento MCP aún no está preparado. Pulsa Preparar complemento MCP y revisa la confirmación.',
            'unsupported_platform': 'Este complemento MCP requiere Windows de 64 bits. Consulta MCP_OPTIONAL.md para desarrollo desde código fuente.',
            'invalid_manifest': 'No se pudo validar el paquete MCP. Obtén una distribución verificada de SORTH; no se instalará este paquete.',
            'integrity_error': 'La integridad del complemento MCP no coincide. No se ejecutará. Obtén una distribución verificada de SORTH o consulta soporte antes de reparar archivos.',
            'incompatible_component': 'El complemento MCP no corresponde a esta versión de SORTH. Prepara el complemento incluido en esta compilación.',
            'busy': 'Otra preparación MCP está en curso. Espera a que termine y vuelve a intentarlo.',
            'io_error': 'No se pudo preparar el complemento MCP. Revisa el espacio disponible y los permisos de la carpeta de datos e inténtalo de nuevo.',
            'cleanup_failed': 'No se pudieron retirar todos los archivos temporales de la preparación MCP. El permiso no ha cambiado; consulta soporte antes de limpiar archivos manualmente.',
            'probe_failed': 'El complemento MCP no superó su verificación. No está listo; revisa MCP_OPTIONAL.md antes de reintentar.',
            'runtime_error': 'No se pudieron cargar los componentes MCP. Revisa el entorno siguiendo MCP_OPTIONAL.md.',
            'timeout': 'La verificación MCP agotó el tiempo. Puedes volver a intentarlo.',
            'cancelled': 'Operación MCP cancelada. El permiso no ha cambiado.',
        }
        self.mcp_status_label.setText(msg(messages.get(status, messages['runtime_error'])))
        if status == 'prepared':
            self.mcp_status = 'available'
        self._refresh_mcp_permission()

    def _confirm_mcp_preparation(self, manifest, destination):
        confirmation = QMessageBox(self)
        confirmation.setWindowTitle(msg('Preparar complemento MCP'))
        confirmation.setIcon(QMessageBox.Icon.Question)
        confirmation.setTextFormat(Qt.TextFormat.PlainText)
        confirmation.setText(msg('Se copiará el complemento MCP {version} incluido con SORTH a:\n{path}\n\nSe comprobará su integridad y se ejecutará una prueba local sin iniciar el servidor. No usa red ni pip y no instala en Python del sistema. Se aplica inmediatamente; Cancelar configuración no elimina el complemento. El permiso MCP y los clientes no cambian. ¿Preparar ahora?',
                                 version=manifest['version'], path=str(destination)))
        confirmation.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        confirmation.button(QMessageBox.StandardButton.Yes).setText(msg('Preparar complemento MCP'))
        confirmation.setDefaultButton(QMessageBox.StandardButton.Cancel)
        return confirmation.exec() == QMessageBox.StandardButton.Yes

    def _prepare_mcp(self):
        self.select_section('mcp')
        if self.mcp_preparation.active or self.mcp_probe.active or self._pending_close is not None:
            return
        try:
            manifest = mcp_component.bundle_info()
            destination = mcp_component.component_install_path()
        except mcp_component.ComponentError as error:
            self._show_mcp_status(error.code)
            return
        except Exception:
            self._show_mcp_status('runtime_error')
            return
        if not self._confirm_mcp_preparation(manifest, destination):
            return
        self.mcp_status = 'preparing'
        self.mcp_command = None
        self.section_selector.setEnabled(False)
        self.mcp_check_button.setEnabled(False)
        self.mcp_prepare_button.setEnabled(False)
        self.mcp_help_button.setEnabled(False)
        self.mcp_cancel_button.setText(msg('Cancelar preparación MCP'))
        self.mcp_cancel_button.setEnabled(True)
        self.mcp_cancel_button.show()
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        self.calendar_button.setEnabled(False)
        self._mcp_progress('verifying')
        self.mcp_preparation.start()

    def _mcp_progress(self, state):
        if self._pending_close is not None or not self.mcp_cancel_button.isEnabled():
            return
        messages = {
            'verifying': 'Comprobando integridad del paquete MCP…',
            'extracting': 'Preparando archivos del complemento MCP…',
            'checking': 'Verificando el complemento MCP preparado…',
            'committing': 'Finalizando la preparación MCP…',
        }
        self.mcp_status_label.setText(msg(messages.get(state, messages['verifying'])))

    def _cancel_mcp_operation(self):
        if self.mcp_probe.active:
            self.mcp_cancel_button.setEnabled(False)
            self.mcp_status_label.setText(msg('Cancelando la verificación MCP de forma segura…'))
            self.mcp_probe.cancel()
        elif self.mcp_preparation.active:
            self._cancel_mcp_preparation()

    def _cancel_mcp_preparation(self):
        self.mcp_cancel_button.setEnabled(False)
        self.mcp_status_label.setText(msg('Cancelando la preparación MCP de forma segura…'))
        self.mcp_preparation.cancel()

    def _mcp_prepared(self, status, result):
        self.mcp_cancel_button.hide()
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(True)
        self.calendar_button.setEnabled(self.controls['project_calendar'].isChecked()
                                        and not self.window._busy and not self.window._restore_failed)
        self.mcp_command = result['command'] if status == 'available' and result else None
        self._show_mcp_status('prepared' if status == 'available' else status)
        self._finish_pending_close()

    def _show_mcp_help(self):
        self._refresh_mcp_permission()
        # Read for presentation only: keep the preference store's expected
        # generation intact so a later Save still detects external changes.
        saved = mcp_permission_enabled(self.window._features.path)
        McpClientHelp(self.mcp_command, self, permission_enabled=saved,
                      pending_permission=self.controls['mcp_server'].isChecked() != saved).exec()

    def _finish_pending_close(self):
        if self._pending_close is not None and not self.mcp_preparation.active and not self.mcp_probe.active:
            result, self._pending_close = self._pending_close, None
            super().done(result)

    def done(self, result):
        if self.mcp_preparation.active or self.mcp_probe.active:
            self._pending_close = result
            self.buttons.setEnabled(False)
            self.mcp_preparation.cancel()
            self.mcp_probe.cancel()
            self.mcp_status_label.setText(msg('Terminando la operación MCP de forma segura antes de cerrar…'))
            self._finish_pending_close()
            return
        super().done(result)

    def closeEvent(self, event):
        if self.mcp_preparation.active or self.mcp_probe.active:
            event.ignore()
            self.reject()
        else:
            super().closeEvent(event)

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
        self._saved_values = {key: control.isChecked() for key, control in self.controls.items()}
        self._refresh_save_state()

    def accept(self):
        if self.mcp_preparation.active or self._pending_close is not None:
            return
        values = {key: control.isChecked() for key, control in self.controls.items()}
        if (self.mcp_status == 'checking' and values['mcp_server']
                and not mcp_permission_enabled(self.window._features.path)):
            return
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
            self._refresh_mcp_permission()
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
