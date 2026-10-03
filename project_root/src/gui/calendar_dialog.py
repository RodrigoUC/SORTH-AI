"""Detached calendar editor: preview first, atomic project transition second."""
from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QFormLayout, QTimeEdit, QHeaderView
from .i18n_widgets import (QDialog, QLabel, QPushButton, QCheckBox, QTableWidget,
                           QDialogButtonBox, QMessageBox)
from .i18n import msg
from ..scheduling.project_calendar import ProjectCalendar, DAYS
from ..application.calendar_transition import preview_calendar_change


class CalendarDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(msg('Calendario del proyecto'))
        self.resize(620, 540)
        layout = QVBoxLayout(self)
        hint = QLabel(msg('Define días lectivos, horas y descansos. El calendario guardado se respeta aunque ocultes el editor.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        days = QHBoxLayout()
        layout.addLayout(days)
        self.days = {}
        for day in DAYS:
            control = QCheckBox(msg(day))
            control.setAccessibleName(msg(day))
            days.addWidget(control)
            self.days[day] = control
        form = QFormLayout()
        layout.addLayout(form)
        self.opening = self._time(420, 'Hora de apertura')
        self.closing = self._time(1320, 'Hora de cierre')
        form.addRow(msg('Hora de apertura'), self.opening)
        form.addRow(msg('Hora de cierre'), self.closing)
        note = QLabel(msg('Las horas se expresan en HH:mm. Para terminar a medianoche, usa 00:00 como cierre.'))
        note.setWordWrap(True)
        layout.addWidget(note)
        self.breaks = QTableWidget(0, 2)
        self.breaks.setAccessibleName(msg('Descansos del proyecto'))
        self.breaks.setHorizontalHeaderLabels([msg('Inicio'), msg('Fin')])
        self.breaks.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.breaks)
        row = QHBoxLayout()
        layout.addLayout(row)
        for title, action in [('Añadir descanso', self.add_break), ('Quitar descanso seleccionado', self.remove_break),
                              ('Restablecer calendario predeterminado', lambda: self.load(ProjectCalendar()))]:
            button = QPushButton(msg(title))
            button.clicked.connect(lambda _=False, callback=action: callback())
            row.addWidget(button)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        self.feedback.setAccessibleName(msg('Resultado de la revisión del calendario'))
        layout.addWidget(self.feedback)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.apply_button = QPushButton(msg('Revisar y aplicar'))
        self.buttons.addButton(self.apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.load(window.calendar)

    def _time(self, minute, label):
        control = QTimeEdit(QTime((minute // 60) % 24, minute % 60))
        control.setDisplayFormat('HH:mm')
        control.setAccessibleName(msg(label))
        return control

    def add_break(self, start=720, end=780):
        row = self.breaks.rowCount()
        self.breaks.insertRow(row)
        self.breaks.setCellWidget(row, 0, self._time(start, 'Inicio del descanso'))
        self.breaks.setCellWidget(row, 1, self._time(end, 'Fin del descanso'))

    def remove_break(self):
        row = self.breaks.currentRow()
        if row >= 0:
            self.breaks.removeRow(row)

    def load(self, calendar):
        for day, control in self.days.items():
            control.setChecked(day in calendar.days)
        self.opening.setTime(QTime(calendar.day_start // 60, calendar.day_start % 60))
        self.closing.setTime(QTime((calendar.day_end // 60) % 24, calendar.day_end % 60))
        self.breaks.setRowCount(0)
        for start, end in calendar.breaks:
            self.add_break(start, end)

    @staticmethod
    def minutes(control):
        time = control.time()
        return time.hour() * 60 + time.minute()

    def value(self):
        return ProjectCalendar(tuple(day for day, control in self.days.items() if control.isChecked()),
            self.minutes(self.opening), self.minutes(self.closing) or 1440,
            tuple((self.minutes(self.breaks.cellWidget(row, 0)), self.minutes(self.breaks.cellWidget(row, 1)) or 1440)
                  for row in range(self.breaks.rowCount())))

    def accept(self):
        window = self.window
        if window._busy or window._restore_failed:
            return
        from ..application.edit_history import fingerprint
        expected = fingerprint(window._capture_edit_state())
        try:
            calendar = self.value()
            preview = preview_calendar_change(window.calendar, calendar, window.current_schedule,
                window.current_groups or [g for c in window.course_manager.get_courses() for g in c.generate_groups()], window._validation_classrooms(),
                {g.group_id for g in (window.current_groups or []) if g.lab_override}, getattr(window, 'resources', None))
        except ValueError as error:
            self.feedback.setText(msg('Revisa días, horas y descansos: deben ser válidos, no solaparse y dejar tiempo lectivo. {detail}', detail=msg(str(error))))
            return
        if set(preview.affected) & window.pinned_group_ids:
            self.feedback.setText(msg('Hay sesiones fijadas afectadas. Desfíjalas explícitamente antes de cambiar el calendario.'))
            return
        detail = ', '.join(preview.affected) or str(msg('Ninguna'))
        answer = QMessageBox.question(self, msg('Revisar calendario'), msg(
            'Sesiones que quedarán pendientes: {sessions}. Las demás conservan su día y hora. ¿Aplicar el calendario?', sessions=detail),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes:
            return
        if window._apply_calendar(calendar, preview, expected=expected):
            super().accept()
        else:
            self.feedback.setText(msg('No se pudo guardar el calendario. No se aplicaron cambios.'))
