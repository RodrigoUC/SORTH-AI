"""Native explicit-field editor: selection, review, one atomic application."""
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QHeaderView, QPlainTextEdit
from .i18n_widgets import (QDialog, QLabel, QCheckBox, QComboBox, QSpinBox,
                          QTableWidget, QTableWidgetItem, QPushButton)
from .i18n import msg, language_manager
from ..application.bulk_courses import preview_bulk, apply_bulk
from ..application.edit_history import EditError
from ..scheduling.project_calendar import ProjectCalendar

FIELD_LABELS = {'required_room_type': 'Tipo de aula', 'size': 'Tamaño', 'preferred_day': 'Día preferido'}


class BulkCourseDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.selected_codes = window.course_manager.selected_course_codes()
        self.plan = None
        self.setWindowTitle(msg('Editar cursos en lote'))
        self.resize(760, 570)
        self.setMinimumSize(620, 460)
        layout = QVBoxLayout(self)
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setPlainText(str(msg('Cursos seleccionados: {count}. Identificadores: {codes}',
            count=len(self.selected_codes), codes=', '.join(self.selected_codes))))
        self.summary.setAccessibleName(msg('Cursos seleccionados'))
        self.summary.setMaximumHeight(60)
        layout.addWidget(self.summary)
        note = QLabel(msg('Marque solo los campos que desea cambiar. Sin marcar conserva el valor de cada curso.'))
        note.setWordWrap(True)
        layout.addWidget(note)
        self.checks, self.inputs = {}, {}
        courses = [c for c in window.course_manager.get_courses() if c.code in self.selected_codes]
        days = list(getattr(window, 'calendar', ProjectCalendar()).days)
        for course in courses:
            if course.preferred_day and course.preferred_day not in days:
                days.append(course.preferred_day)
        for field, title in FIELD_LABELS.items():
            row = QHBoxLayout()
            check = QCheckBox(msg(title))
            check.setAccessibleName(msg(title))
            row.addWidget(check)
            if field == 'size':
                control = QSpinBox()
                control.setRange(0, 100000)
            else:
                control = QComboBox()
                options = [('REGULAR', 'REGULAR'), ('LAB', 'LAB')] if field == 'required_room_type' else [
                    ('Borrar preferencia', None), *[(day, day) for day in days]]
                for label, value in options:
                    control.addItem(msg(label) if label not in ('REGULAR', 'LAB') else label, value)
            control.setAccessibleName(msg(title))
            control.setEnabled(False)
            check.toggled.connect(control.setEnabled)
            values = [getattr(c, field) for c in courses]
            mixed = len(set(values)) > 1
            if values and not mixed:
                if field == 'size':
                    control.setValue(values[0])
                else:
                    control.setCurrentIndex(max(0, control.findData(values[0])))
            current = QLabel(msg('Valores mezclados') if mixed else msg('Conservar valor'))
            row.addWidget(control, 1)
            row.addWidget(current)
            layout.addLayout(row)
            self.checks[field], self.inputs[field] = check, control
            check.toggled.connect(self._invalidate)
            (control.valueChanged if field == 'size' else control.currentIndexChanged).connect(self._invalidate)
        self.table = QTableWidget(0, 4)
        self.table.setAccessibleName(msg('Vista previa de cambios por código'))
        self.table.setHorizontalHeaderLabels([msg('Código'), msg('Campo'), msg('Antes'), msg('Después')])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.impact = QLabel(msg('Revise el lote antes de aplicarlo.'))
        self.impact.setWordWrap(True)
        self.impact.setAccessibleName(msg('Impacto en horario y restricciones'))
        layout.addWidget(self.impact)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setAccessibleName(msg('Error de edición en lote'))
        layout.addWidget(self.error)
        row = QHBoxLayout()
        self.review = QPushButton(msg('Revisar cambios'))
        self.apply = QPushButton(msg('Aplicar lote'))
        self.cancel = QPushButton(msg('Cancelar'))
        self.review.clicked.connect(self._review)
        self.apply.clicked.connect(self._apply)
        self.cancel.clicked.connect(self.reject)
        self.apply.setEnabled(False)
        self.apply.setAutoDefault(False)
        row.addWidget(self.review)
        row.addStretch()
        row.addWidget(self.apply)
        row.addWidget(self.cancel)
        layout.addLayout(row)
        language_manager().changed.connect(self._invalidate)

    def _invalidate(self, *_):
        self.plan = None
        self.apply.setEnabled(False)
        self.table.setRowCount(0)
        self.impact.setText(msg('Revise el lote antes de aplicarlo.'))
        self.error.clear()

    def _fields(self):
        return {field: (control.value() if field == 'size' else control.currentData())
                for field, control in self.inputs.items() if self.checks[field].isChecked()}

    def _review(self):
        self._invalidate()
        try:
            self.plan = preview_bulk(self.window._capture_edit_state(), self.selected_codes, self._fields())
        except EditError as error:
            self.error.setText(error.render(msg))
            return
        self.table.setRowCount(len(self.plan.changes))
        for row, (code, field, before, after) in enumerate(self.plan.changes):
            def render(value):
                return msg('Sin preferencia') if value is None else (msg(value) if field == 'preferred_day' else str(value))
            for column, value in enumerate((code, msg(FIELD_LABELS[field]), render(before), render(after))):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.impact.setText(msg('Se dejarán pendientes {pending} asignaciones no fijadas. Se conservan {pins} sesiones fijadas y todas las restricciones. Las preferencias por grupo se conservan y pueden prevalecer sobre el día del curso.',
            pending=len(self.plan.removed_assignments), pins=len(self.plan.preserved_pins)))
        self.apply.setEnabled(True)

    def _apply(self):
        if self.plan is None:
            return
        try:
            if self.window._busy or self.window._restore_failed or not self.window._features.enabled('bulk_operations'):
                raise EditError('La herramienta no está disponible. Cierre el diálogo y revise Configuración.')
            accepted = apply_bulk(self.window._history, self.window._capture_edit_state(), self.plan,
                self.window.course_manager.selected_course_codes(), self.window._persist_edit_state,
                enabled=self.window._features.enabled('undo_redo'))
        except Exception as error:
            self.error.setText(error.render(msg) if isinstance(error, EditError) else msg(
                'No se pudo guardar el lote. Se conservan todos los datos. {detail}', detail=str(error)))
            return
        try:
            self.window._finish_edit_commit(msg('Lote guardado. Puede deshacerlo en una sola operación.'))
            self.accept()
        except Exception as error:
            self.window._committed_view_failure(error)
