"""Transactional native settings: Cancel never changes preferences or project data."""
from PyQt6.QtWidgets import QVBoxLayout
from .i18n_widgets import QDialog, QLabel, QCheckBox, QDialogButtonBox, QMessageBox, QPushButton
from .i18n import msg
from .features import FEATURES


class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(msg('Configuración'))
        self.resize(560, 380)
        layout = QVBoxLayout(self)
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
        self.controls = {}
        for feature in FEATURES:
            control = QCheckBox(msg(feature.title))
            control.setAccessibleName(msg(feature.title))
            control.setAccessibleDescription(msg(feature.description))
            control.setChecked(window._features.enabled(feature.key))
            layout.addWidget(control)
            description = QLabel(msg(feature.description))
            description.setWordWrap(True)
            description.setObjectName('mutedText')
            layout.addWidget(description)
            self.controls[feature.key] = control
        note = QLabel(msg('Desactivar oculta los controles, sin borrar datos. Las sesiones ya fijadas siguen protegidas. Las validaciones de seguridad siempre están activas.'))
        note.setWordWrap(True)
        layout.addWidget(note)
        mcp = QLabel(msg('MCP se instala y se inicia por separado; esta configuración no activa servicios externos.'))
        mcp.setWordWrap(True)
        mcp.setObjectName('mutedText')
        layout.addWidget(mcp)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def recover_preferences(self):
        answer = QMessageBox.question(self, msg('Configuración'), msg(
            'Se conservará el archivo original y se desactivarán las herramientas opcionales. Los horarios, fijaciones y escenarios no cambian. ¿Continuar?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.window._features.recover_defaults()
        except (OSError, ValueError):
            self.recovery_label.setVisible(bool(self.window._features.load_error))
            self.recover_button.setVisible(bool(self.window._features.load_error))
            QMessageBox.warning(self, msg('Configuración'), msg('No se pudo guardar la configuración. Revisa los permisos e inténtalo de nuevo.'))
            return
        for control in self.controls.values():
            control.setChecked(False)
        self.window._apply_feature_preferences()
        self.recovery_label.hide()
        self.recover_button.hide()

    def accept(self):
        values = {key: control.isChecked() for key, control in self.controls.items()}
        if (self.window._features.enabled('pinned_sessions') and not values['pinned_sessions']
                and self.window.pinned_group_ids):
            answer = QMessageBox.question(self, msg('Sesiones fijadas'), msg(
                'Se ocultarán los controles para fijar sesiones. Las sesiones ya fijadas seguirán condicionando la generación. Para cambiarlas, vuelve a activar esta función. ¿Guardar configuración?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.window._features.save(values)
        except (OSError, ValueError):
            self.recovery_label.setVisible(bool(self.window._features.load_error))
            self.recover_button.setVisible(bool(self.window._features.load_error))
            QMessageBox.warning(self, msg('Configuración'), msg('No se pudo guardar la configuración. Revisa los permisos e inténtalo de nuevo.'))
            return
        self.window._apply_feature_preferences()
        super().accept()
