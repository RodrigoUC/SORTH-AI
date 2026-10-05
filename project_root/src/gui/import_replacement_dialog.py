"""Explicit consent before replacing a previously imported workbook."""
from pathlib import Path

from PyQt6.QtWidgets import QVBoxLayout, QPlainTextEdit

from .i18n import msg
from .i18n_widgets import QDialog, QDialogButtonBox, QLabel


class ImportReplacementDialog(QDialog):
    def __init__(self, window, candidate):
        super().__init__(window)
        self._candidate = candidate
        self.setWindowTitle(msg('Reemplazar el Excel actual'))
        self.setMinimumWidth(480)
        self.resize(640, 330)
        layout = QVBoxLayout(self)
        sources = QPlainTextEdit()
        sources.setReadOnly(True)
        sources.setTabChangesFocus(True)
        sources.setMaximumHeight(90)
        sources.setAccessibleName(msg('Reemplazar el Excel actual'))
        sources.setPlainText(str(msg('Excel actual: {old}\nNuevo Excel: {new}',
                                    old=str(Path(window.excel_path).resolve()),
                                    new=str(Path(candidate.path).resolve()))))
        layout.addWidget(sources)
        explanation = QLabel(msg(
            'El nuevo Excel reemplazará los cursos y las aulas actuales. Se perderán las asignaciones del horario, las fijaciones, las restricciones de aulas y las asociaciones de docentes, grupos de estudiantes y estudiantes con las sesiones anteriores. No se trasladarán asociaciones por identificador.'))
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        retained = QLabel(msg(
            'Se conservarán los catálogos de recursos, sus disponibilidades, el calendario y las preferencias. Cancelar o un error conserva la sesión actual.'))
        retained.setWordWrap(True)
        layout.addWidget(retained)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                       QDialogButtonBox.StandardButton.Cancel, self)
        self.buttons.setButtonText(QDialogButtonBox.StandardButton.Ok, msg('Reemplazar Excel'))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setFocus()
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
