"""Explicit manual placement; no automatic relaxation of laboratory requirements."""
from PyQt6.QtCore import QTime, Qt
from .i18n_widgets import (QDialog, QFormLayout, QLabel, QComboBox, QTimeEdit,
                             QDialogButtonBox, QMessageBox)
from ..scheduling.validation import validate_schedule
from .i18n import msg, join_messages


class ManualAssignmentDialog(QDialog):
    def __init__(self, group, groups, assignments, classrooms, time_model, parent=None):
        super().__init__(parent)
        self.setWindowTitle(msg('Asignar sesión manualmente'))
        self.setMinimumWidth(480)
        self.group, self.groups = group, groups
        self.assignments, self.classrooms, self.time_model = assignments, classrooms, time_model
        self.result_assignment = None
        self.lab_override = False
        layout = QFormLayout(self)
        summary = QLabel(msg('{p0} · {p2} min · {p4} estudiantes', p0=group.group_id, p2=group.duration_min, p4=group.size))
        summary.setWordWrap(True)
        layout.addRow(summary)
        reason = QLabel(msg(group.unassigned_reason) if group.unassigned_reason else msg('Seleccione el aula, día y hora. Se comprobarán todas las restricciones.'))
        reason.setWordWrap(True)
        layout.addRow(reason)
        self.room = QComboBox()
        self.room.addItem(msg('Seleccione un aula'), None)
        for name, room in classrooms.items():
            self.room.addItem(f"{name} · {room.room_type} · {room.capacity}", name)
        self.day = QComboBox()
        for day in time_model.days:
            self.day.addItem(msg(day), time_model.to_day_index(day))
        self.start = QTimeEdit(QTime(7, 0))
        self.start.setDisplayFormat('HH:mm')
        layout.addRow(msg('Aula'), self.room)
        layout.addRow(msg('Día'), self.day)
        layout.addRow(msg('Inicio'), self.start)
        self.error = QLabel("")
        self.error.setWordWrap(True)
        self.error.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.error.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
        self.error.setAccessibleName(msg('Resultado de validación'))
        layout.addRow(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.setButtonText(QDialogButtonBox.StandardButton.Save, msg('Asignar'))
        buttons.setButtonText(QDialogButtonBox.StandardButton.Cancel, msg('Cancelar'))
        buttons.accepted.connect(self._submit)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _submit(self):
        room = self.room.currentData()
        if room is None:
            self.error.setText(msg('Seleccione un aula.'))
            self.room.setAccessibleDescription(msg('Seleccione un aula.'))
            self.room.setFocus()
            return
        self.room.setAccessibleDescription('')
        start = self.start.time().hour() * 60 + self.start.time().minute()
        placement = (room, self.day.currentData(), start, start + self.group.duration_min)
        override = self.group.required_room_type == 'LAB' and self.classrooms[room].room_type != 'LAB'
        proposed = dict(self.assignments)
        proposed[self.group.group_id] = placement
        overrides = {g.group_id for g in self.groups if g.lab_override}
        if override:
            overrides.add(self.group.group_id)
        else:
            overrides.discard(self.group.group_id)
        errors = validate_schedule(proposed, self.groups, self.classrooms, self.time_model, overrides)
        if errors:
            self.error.setText(join_messages('\n', (error.render(msg) for error in errors)))
            self.error.setFocus()
            return
        if override and QMessageBox.question(
                self, msg('Confirmar excepción de laboratorio'),
                msg('{p0} requiere laboratorio. ¿Asignarlo al aula regular {p2}?\nEsta excepción manual quedará registrada en la sesión.', p0=self.group.group_id, p2=room),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.result_assignment, self.lab_override = placement, override
        self.accept()
