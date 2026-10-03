"""Explicit replacement review; no merge choice or hidden data writes."""
from PyQt6.QtWidgets import QVBoxLayout, QPlainTextEdit
from .i18n_widgets import QDialog, QLabel, QDialogButtonBox
from .i18n import msg
from ..application.import_difference import import_difference
from ..scheduling.time_model import TimeModel


FIELD_LABELS = {
    'name': 'Nombre', 'number_of_groups': 'Grupos', 'duration_min': 'Duración (minutos)',
    'required_room_type': 'Tipo de aula requerido', 'size': 'Estudiantes',
    'suggested_classroom': 'Aula sugerida', 'preferred_day': 'Día preferido',
    'preferred_start_min': 'Hora preferida', 'group_suggestions': 'Preferencias por grupo',
    'force_split': 'División de sesiones', 'capacity': 'Capacidad', 'room_type': 'Tipo de aula',
    'description': 'Descripción', 'campus': 'Campus',
}


def display_value(field, value):
    if value is None:
        return msg('Sin valor')
    if isinstance(value, bool):
        return msg('Sí') if value else msg('No')
    if field == 'preferred_start_min':
        return TimeModel.minutes_to_hhmm(value)
    if field == 'preferred_day':
        return msg(value)
    if field == 'group_suggestions':
        if not value:
            return msg('Sin valor')
        return '\n      '.join(str(msg('Grupo {number}: aula {room}, día {day}, hora {time}',
                                  number=index, room=display_value('suggested_classroom', group.get('aula')),
                                  day=display_value('preferred_day', group.get('preferred_day')),
                                  time=display_value('preferred_start_min', group.get('preferred_start_min'))))
                               for index, group in enumerate(value, 1))
    return str(value)


class ImportPreviewDialog(QDialog):
    def __init__(self, window, candidate, retained_pins):
        super().__init__(window)
        self._window, self._candidate, self._retained_pins = window, candidate, retained_pins
        self.setWindowTitle(msg('Revisar cambios del Excel'))
        self.resize(780, 560)
        layout = QVBoxLayout(self)
        label = QLabel(msg('Se reemplazarán los cursos y aulas. Se borrarán las restricciones y las asignaciones no conservadas. Cancelar mantiene la sesión actual.'))
        label.setWordWrap(True)
        layout.addWidget(label)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setAccessibleName(msg('Cambios de importación'))
        self.details.setPlainText(self.describe(window, candidate, retained_pins))
        layout.addWidget(self.details)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.setButtonText(QDialogButtonBox.StandardButton.Ok, msg('Reemplazar con este Excel'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.details.setFocus()

    def retranslate(self):
        super().retranslate()
        if hasattr(self, 'details'):
            self.details.setAccessibleName(msg('Cambios de importación'))
            self.details.setPlainText(self.describe(self._window, self._candidate, self._retained_pins))

    @staticmethod
    def describe(window, candidate, retained_pins):
        courses, rooms = import_difference(window.course_manager.get_courses(), window._classrooms, candidate.imported)
        sections = [msg('Archivo: {name}', name=candidate.path)]
        old_courses = {course.code: course for course in window.course_manager.get_courses()}
        new_courses = {course.code: course for course in candidate.imported.courses}
        for title, change, old, new in ((msg('Cursos'), courses, old_courses, new_courses),
                                       (msg('Aulas'), rooms, window._classrooms, candidate.imported.classrooms)):
            sections.append(str(title))
            for label, values in ((msg('Añadidos'), change.added), (msg('Modificados'), change.changed),
                                  (msg('Eliminados'), change.removed)):
                sections.append(str(msg('{label}: {count}', label=label, count=len(values))))
                for key in values:
                    sections.append('  ' + key)
                    if values is change.changed:
                        for field in change.changed[key]:
                            sections.append(str(msg('    {field}: {before} → {after}',
                                                    field=msg(FIELD_LABELS[field]),
                                                    before=display_value(field, getattr(old[key], field)),
                                                    after=display_value(field, getattr(new[key], field)))))
        restrictions = window.classroom_restrictions
        sections.append(str(msg('Restricciones que se borrarán: {count}', count=len(restrictions))))
        sections.extend('  ' + room + ': ' + ', '.join(sorted(codes)) for room, codes in sorted(restrictions.items()))
        assignments = window.current_schedule or {}
        for label, ids in ((msg('Asignaciones que se borrarán'), sorted(set(assignments) - retained_pins)),
                           (msg('Sesiones fijadas que se conservarán'), sorted(retained_pins))):
            sections.append(str(msg('{label}: {count}', label=label, count=len(ids))))
            for gid in ids:
                room, day, start, end = assignments[gid]
                day_name = TimeModel.default().index_to_day.get(day, str(day))
                sections.append(f'  {gid}: {room}, {msg(day_name)}, {TimeModel.minutes_to_hhmm(start)}–{TimeModel.minutes_to_hhmm(end)}')
        return '\n'.join(map(str, sections))
