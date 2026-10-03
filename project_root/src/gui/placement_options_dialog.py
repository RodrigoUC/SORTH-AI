"""Keyboard-readable bounded placement review with mandatory stale revalidation."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout
from .i18n_widgets import (QDialog, QLabel, QTableWidget,
                          QTableWidgetItem, QDialogButtonBox, QPushButton)
from .i18n import msg, join_messages
from ..application.placement_suggestions import enumerate_placements, validate_choice


class PlacementOptionsDialog(QDialog):
    def __init__(self, group_id, current_inputs, apply_choice, parent=None):
        super().__init__(parent)
        self.group_id = group_id
        self.current_inputs, self.apply_choice = current_inputs, apply_choice
        self.setWindowTitle(msg('Opciones para {gid}', gid=group_id))
        self.resize(640, 480)
        layout = QVBoxLayout(self)
        hint = QLabel(msg('Opciones del horario actual, sin mover otras sesiones. Búsqueda cada 30 minutos y en horas guardadas; la asignación manual permite otras horas.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status.setAccessibleName(msg('Resultado de opciones'))
        layout.addWidget(self.status)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([msg('Aula'), msg('Día'), msg('Inicio'), msg('Fin')])
        self.table.setAccessibleName(msg('Ubicaciones válidas para la sesión pendiente'))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.setButtonText(QDialogButtonBox.StandardButton.Save, msg('Asignar'))
        self.buttons.setButtonText(QDialogButtonBox.StandardButton.Cancel, msg('Cancelar'))
        self.buttons.accepted.connect(self._apply)
        self.buttons.rejected.connect(self.reject)
        self.table.itemSelectionChanged.connect(lambda: self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(self.table.currentRow() >= 0))
        refresh = QPushButton(msg('Recalcular opciones'))
        refresh.clicked.connect(self.refresh)
        self.buttons.addButton(refresh, QDialogButtonBox.ButtonRole.ActionRole)
        layout.addWidget(self.buttons)
        self.refresh()

    def refresh(self, stale=False):
        self.table.setRowCount(0)
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        self.options = None
        inputs = self.current_inputs()
        if inputs is None:
            self.status.setText(msg('La sesión o la herramienta ya no está disponible. No se aplicó ningún cambio.'))
            return
        try:
            self.options = enumerate_placements(self.group_id, **inputs)
        except ValueError:
            self.status.setText(msg('La sesión o la herramienta ya no está disponible. No se aplicó ningún cambio.'))
            return
        tm = inputs['time_model']
        for placement in self.options.placements:
            row = self.table.rowCount()
            self.table.insertRow(row)
            room, day, start, end = placement
            for col, text in enumerate((room, msg(tm.to_day_name(day)), tm.minutes_to_hhmm(start), tm.minutes_to_hhmm(end))):
                self.table.setItem(row, col, QTableWidgetItem(text))
        text = [msg('El horario cambió. Opciones recalculadas; elija de nuevo.') if stale else
                msg('{count} opciones en el horario actual.', count=len(self.options.placements)) if self.options.placements else
                msg('No hay opciones en el horario actual. Esto no demuestra imposibilidad global.')]
        if self.options.truncated:
            text.append(msg('Búsqueda limitada: se muestran solo los primeros resultados válidos.'))
        if not self.options.placements:
            text.extend(error.render(msg) if hasattr(error, 'render') else msg(str(error)) for error in self.options.notices)
        self.status.setText(join_messages('\n', text))
        self.table.resizeColumnsToContents()

    def _apply(self):
        row = self.table.currentRow()
        if self.options is None or row < 0 or row >= len(self.options.placements):
            return
        inputs = self.current_inputs()
        if inputs is None:
            self.refresh()
            return
        placement = self.options.placements[row]
        errors = validate_choice(self.options, placement, **inputs)
        if errors:
            self.refresh(stale=True)
            return
        if self.apply_choice(self.options, placement):
            self.accept()
