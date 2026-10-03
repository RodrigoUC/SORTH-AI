# src/gui/course_manager_widget.py

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QHeaderView
)
from PyQt6.QtCore import Qt, QTime, pyqtSignal
from copy import deepcopy
from PyQt6.QtWidgets import (
    QCompleter
)

from ..scheduling.course import Course
from ..scheduling.time_model import TimeModel

from .i18n import msg, language_manager
from .i18n_widgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTimeEdit, QWidget
)


def _confirm(parent, title: str, message: str) -> bool:
    """Styled confirmation dialog with colored header."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setModal(True)
    dlg.setMinimumWidth(420)

    outer = QVBoxLayout()
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)

    header = QLabel(msg('  ⚠️  {p1}', p1=title))
    header.setStyleSheet(
        "background-color: #BF360C; color: #FFFFFF; "
        "font-size: 12pt; font-weight: bold; padding: 14px 20px;"
    )
    outer.addWidget(header)

    body = QWidget()
    body_layout = QVBoxLayout(body)
    body_layout.setContentsMargins(28, 20, 28, 20)
    body_layout.setSpacing(20)

    lbl = QLabel(message)
    lbl.setWordWrap(True)
    lbl.setStyleSheet("font-size: 11pt;")
    body_layout.addWidget(lbl)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    body_layout.addWidget(buttons)
    outer.addWidget(body)

    dlg.setLayout(outer)
    return dlg.exec() == QDialog.DialogCode.Accepted


class CourseDialog(QDialog):
    """Dialog for adding/editing a course."""

    DAYS = ["(Sin preferencia)", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]

    def __init__(self, parent=None, course: Course = None,
                 completions: list[tuple[str, str]] | None = None):
        super().__init__(parent)
        self.course = course
        self._completions = completions or []   # [(code, name), ...]
        self._code_to_name = {c: n for c, n in self._completions}
        self.setWindowTitle(msg('Agregar Curso') if not course else msg('Editar Curso'))
        self.setModal(True)
        self.resize(460, 420)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout()

        # Code
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText(msg('placeholder.course_code'))
        self.code_edit.textChanged.connect(self._update_room_type_label)
        self.code_edit.textChanged.connect(self._autofill_name)
        if self._completions:
            code_completer = QCompleter([c for c, _ in self._completions])
            code_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            code_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.code_edit.setCompleter(code_completer)
        layout.addRow(msg('Código del Curso:'), self.code_edit)

        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(msg('Ej: Biología General (opcional)'))
        if self._completions:
            name_completer = QCompleter([n for _, n in self._completions if n])
            name_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.name_edit.setCompleter(name_completer)
        layout.addRow(msg('Nombre:'), self.name_edit)

        # Number of groups
        self.groups_spin = QSpinBox()
        self.groups_spin.setMinimum(1)
        self.groups_spin.setMaximum(50)
        self.groups_spin.setValue(1)
        layout.addRow(msg('Número de Grupos:'), self.groups_spin)

        # Duration — hours + minutes
        dur_layout = QHBoxLayout()
        self.dur_hours = QSpinBox()
        self.dur_hours.setAccessibleName(msg('Duración en horas'))
        self.dur_hours.setRange(0, 14)
        self.dur_hours.setValue(1)
        self.dur_hours.setSuffix(" h")
        self.dur_mins = QSpinBox()
        self.dur_mins.setAccessibleName(msg('Duración en minutos'))
        self.dur_mins.setRange(0, 55)
        self.dur_mins.setSingleStep(5)
        self.dur_mins.setValue(30)
        self.dur_mins.setSuffix(" min")
        dur_layout.addWidget(self.dur_hours)
        dur_layout.addWidget(self.dur_mins)
        layout.addRow(msg('Duración:'), dur_layout)

        # Room type (auto-detected)
        self.room_type_label = QLabel()
        layout.addRow(msg('Tipo de Sala:'), self.room_type_label)

        # Suggested classroom
        self.classroom_edit = QLineEdit()
        self.classroom_edit.setPlaceholderText(msg('placeholder.preferred_classroom'))
        layout.addRow(msg('Aula Sugerida:'), self.classroom_edit)

        # Preferred day
        self.day_combo = QComboBox()
        for index, day in enumerate(self.DAYS):
            self.day_combo.addItem(msg(day), day if index else None)
        layout.addRow(msg('Día Preferido:'), self.day_combo)

        # Preferred start time — QTimeEdit for clarity
        time_layout = QHBoxLayout()
        self.chk_pref_time = QCheckBox(msg('Activar hora preferida'))
        self.chk_pref_time.toggled.connect(self._toggle_pref_time)
        self.pref_time_edit = QTimeEdit()
        self.pref_time_edit.setAccessibleName(msg('Hora de inicio preferida'))
        self.pref_time_edit.setDisplayFormat("HH:mm")
        self.pref_time_edit.setTime(QTime(8, 0))
        self.pref_time_edit.setMinimumTime(QTime(7, 0))
        self.pref_time_edit.setMaximumTime(QTime(21, 0))
        self.pref_time_edit.setToolTip(msg('Hora de inicio preferida para este curso (ej: 08:00, 13:00)'))
        time_layout.addWidget(self.chk_pref_time)
        time_layout.addWidget(self.pref_time_edit)
        time_layout.addStretch()
        layout.addRow(msg('Hora Preferida:'), time_layout)

        # Split across days
        self.split_combo = QComboBox()
        self.split_combo.addItems([
            msg('Automático (dividir si > 4.5h)'),
            msg('Forzar división en varios días'),
            msg('No dividir (asignar en un solo día)'),
        ])
        self.split_combo.setToolTip(
            msg('Automático: se divide solo si la duración supera 4.5 horas.\nForzar división: siempre se divide en bloques de 2h en días distintos.\nNo dividir: se asigna completo en un solo día sin importar la duración.')
        )
        layout.addRow(msg('División en días:'), self.split_combo)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        # Load existing data if editing
        if self.course:
            self.code_edit.setText(self.course.code)
            self.name_edit.setText(self.course.name or "")
            self.groups_spin.setValue(self.course.number_of_groups)
            h, m = divmod(self.course.duration_min, 60)
            self.dur_hours.setValue(h)
            self.dur_mins.setValue(m)
            self.classroom_edit.setText(self.course.suggested_classroom or "")
            if self.course.preferred_day:
                idx = self.day_combo.findData(self.course.preferred_day)
                if idx >= 0:
                    self.day_combo.setCurrentIndex(idx)
            if self.course.preferred_start_min is not None:
                self.chk_pref_time.setChecked(True)
                ph, pm = divmod(self.course.preferred_start_min, 60)
                self.pref_time_edit.setTime(QTime(ph, pm))
            else:
                self.chk_pref_time.setChecked(False)

            # Split
            fs = self.course.force_split
            if fs is True:
                self.split_combo.setCurrentIndex(1)
            elif fs is False:
                self.split_combo.setCurrentIndex(2)
            else:
                self.split_combo.setCurrentIndex(0)

        self._update_room_type_label()
        self._toggle_pref_time(self.chk_pref_time.isChecked())

    def _autofill_name(self, code: str):
        """Auto-fill name when code matches a known course exactly."""
        name = self._code_to_name.get(code.strip())
        if name and not self.name_edit.text():
            self.name_edit.setText(name)

    def _update_room_type_label(self):
        code = self.code_edit.text().strip().upper()
        if code.endswith("L") or code.endswith("P"):
            self.room_type_label.setText(msg('🔬 LAB (detectado automáticamente)'))
            self.room_type_label.setStyleSheet("color: #1565C0;")
        else:
            self.room_type_label.setText(msg('🏫 REGULAR (detectado automáticamente)'))
            self.room_type_label.setStyleSheet("color: #2E7D32;")

    def _toggle_pref_time(self, enabled: bool):
        self.pref_time_edit.setEnabled(enabled)

    def accept(self):
        if not self.code_edit.text().strip():
            QMessageBox.warning(self, msg('Advertencia'), msg('El código del curso es obligatorio.'))
            self.code_edit.setFocus()
            return
        super().accept()

    def get_course(self) -> Course | None:
        code = self.code_edit.text().strip()
        if not code:
            return None

        duration_min = self.dur_hours.value() * 60 + self.dur_mins.value()
        if duration_min <= 0:
            duration_min = 60

        code_upper = code.upper()
        room_type = "LAB" if (code_upper.endswith("L") or code_upper.endswith("P")) else "REGULAR"

        preferred_day = self.day_combo.currentData()

        preferred_start_min = None
        if self.chk_pref_time.isChecked():
            t = self.pref_time_edit.time()
            preferred_start_min = t.hour() * 60 + t.minute()

        suggested = self.classroom_edit.text().strip() or None

        idx = self.split_combo.currentIndex()
        force_split = None if idx == 0 else (True if idx == 1 else False)

        if self.course is not None and code == self.course.code:
            room_type = self.course.required_room_type
        course = Course(
            code=code,
            name=self.name_edit.text().strip() or None,
            number_of_groups=self.groups_spin.value(),
            duration_min=duration_min,
            required_room_type=room_type,
            suggested_classroom=suggested,
            preferred_day=preferred_day,
            preferred_start_min=preferred_start_min,
            force_split=force_split,
        )
        if self.course is not None:
            # Editing visible fields must not erase enrollment, per-group
            # suggestions, or future domain metadata that this dialog cannot edit.
            original = deepcopy(self.course)
            for key, value in vars(course).items():
                if key not in ('size', 'group_suggestions'):
                    setattr(original, key, value)
            return original
        return course


class CourseManagerWidget(QWidget):
    """Widget for managing courses to be scheduled."""

    courses_changed = pyqtSignal()  # emitted after any add/edit/delete/clear/load

    def __init__(self, repo=None):
        super().__init__()
        self.courses: list[Course] = []
        self._repo = repo  # SessionRepository, optional
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        info = QLabel(msg('Cursos a programar'))
        info.setStyleSheet("font-size: 15pt; font-weight: 600; padding: 4px 0;")
        layout.addWidget(info)
        self._empty_label = QLabel(msg('Aún no hay cursos. Cargue un Excel o agregue su primer curso.'))
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("color: #526175; padding: 8px 0;")
        layout.addWidget(self._empty_label)

        # Table
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(msg('Buscar por código o nombre de curso…'))
        self._search.setClearButtonEnabled(True)
        self._search.setAccessibleName(msg('Buscar cursos'))
        self._search.textChanged.connect(self._filter_table)
        search_row.addWidget(self._search)
        layout.addLayout(search_row)

        self.table = QTableWidget()
        self.table.setAccessibleName(msg('Cursos a programar'))
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            msg('Código'), msg('Nombre'), msg('Grupos'), msg('Duración'), msg('Aula Sugerida'),
            msg('Día Preferido'), msg('Hora Preferida')
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = self.edit_actions = QHBoxLayout()
        btn_add = QPushButton(msg('➕ Agregar Curso'))
        btn_add.setToolTip(msg('Agregar un nuevo curso manualmente a la lista'))
        btn_add.clicked.connect(self._add_course)
        btn_edit = QPushButton(msg('✏️ Editar'))
        btn_edit.setToolTip(msg('Editar el curso seleccionado en la tabla'))
        btn_edit.clicked.connect(self._edit_course)
        btn_delete = QPushButton(msg('🗑️ Eliminar'))
        btn_delete.setToolTip(msg('Eliminar el curso seleccionado de la lista'))
        btn_delete.clicked.connect(self._delete_course)
        btn_clear = QPushButton(msg('🧹 Limpiar Todo'))
        btn_clear.setToolTip(msg('Eliminar todos los cursos de la lista'))
        btn_clear.clicked.connect(self._clear_all)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_clear)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_courses_from_excel(self, courses: list[Course]):
        """Load courses imported from Excel, replacing current list."""
        if not self._accept_courses(courses):
            return False
        self.courses = list(courses)
        self._search.clear()
        self._refresh_table()
        self.courses_changed.emit()

    def _accept_courses(self, courses):
        guard = getattr(self, "change_guard", None)
        return guard is None or guard(list(courses))

    def _commit_courses(self, proposed, label):
        handler = getattr(self, 'commit_handler', None)
        if handler is not None:
            return handler(proposed, label)
        if not self._accept_courses(proposed):
            return False
        self.courses = list(proposed)
        self._refresh_table()
        self.courses_changed.emit()
        return True

    def _replace_course(self, index, course):
        proposed = list(self.courses)
        proposed[index] = course
        return self._commit_courses(proposed, 'Editar curso')

    def get_courses(self) -> list[Course]:
        return list(self.courses)

    def edit_course_by_code(self, code: str):
        """Open edit dialog for the course with the given code."""
        for i, c in enumerate(self.courses):
            if c.code == code:
                self.table.setCurrentCell(i, 0)
                dialog = CourseDialog(self, self.courses[i], completions=self._get_completions())
                if dialog.exec():
                    course = dialog.get_course()
                    if course:
                        self._replace_course(i, course)
                return
        QMessageBox.information(self, msg('Info'),
                                msg('El curso {p1} no se encuentra en la lista de cursos.', p1=code))

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _get_completions(self) -> list[tuple[str, str]]:
        if self._repo:
            try:
                return self._repo.get_course_completions()
            except Exception:
                pass
        return []

    def _add_course(self):
        dialog = CourseDialog(self, completions=self._get_completions())
        if dialog.exec():
            course = dialog.get_course()
            if not course:
                QMessageBox.warning(self, msg('Advertencia'), msg('El código del curso es obligatorio.'))
                return
            existing = next((i for i, c in enumerate(self.courses) if c.code == course.code), None)
            if existing is not None:
                if _confirm(self, msg('Curso ya existe'),
                            msg("El curso '{p1}' ya existe en la lista.\n¿Deseas modificarlo en su lugar?", p1=course.code)):
                    edit_dlg = CourseDialog(self, self.courses[existing],
                                           completions=self._get_completions())
                    if edit_dlg.exec():
                        updated = edit_dlg.get_course()
                        if updated:
                            self._replace_course(existing, updated)
                return
            self._commit_courses([*self.courses, course], 'Agregar curso')

    def _selected_course_index(self):
        item = self.table.item(self.table.currentRow(), 0)
        if item is None:
            return -1
        code = item.data(Qt.ItemDataRole.UserRole)
        return next((i for i, course in enumerate(self.courses) if course.code == code), -1)

    def _edit_course(self):
        row = self._selected_course_index()
        if row < 0:
            QMessageBox.warning(self, msg('Advertencia'), msg('Seleccione un curso para editar.'))
            return
        dialog = CourseDialog(self, self.courses[row], completions=self._get_completions())
        if dialog.exec():
            course = dialog.get_course()
            if not course:
                QMessageBox.warning(self, msg('Advertencia'), msg('El código del curso es obligatorio.'))
                return
            self._replace_course(row, course)

    def _delete_course(self):
        row = self._selected_course_index()
        if row < 0:
            QMessageBox.warning(self, msg('Advertencia'), msg('Seleccione un curso para eliminar.'))
            return
        if _confirm(self, msg('Confirmar eliminación'),
                    msg('¿Eliminar el curso {p1}?', p1=self.courses[row].code)):
            self._commit_courses(self.courses[:row] + self.courses[row + 1:], 'Eliminar curso')

    def _clear_all(self):
        if not self.courses:
            return
        if _confirm(self, msg('Confirmar'), msg('¿Eliminar todos los cursos de la lista?')):
            self._commit_courses([], 'Eliminar cursos')

    # ------------------------------------------------------------------
    # Table rendering
    # ------------------------------------------------------------------

    def _refresh_table(self):
        current = self.table.item(self.table.currentRow(), 0)
        selected_code = current.data(Qt.ItemDataRole.UserRole) if current else None
        column = max(0, self.table.currentColumn())
        self._empty_label.setVisible(not self.courses)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.courses))
        for i, c in enumerate(self.courses):
            h, m = divmod(c.duration_min, 60)
            dur_text = f"{h}h {m:02d}min" if m else f"{h}h"

            pref_time = "—"
            if c.preferred_start_min is not None:
                pref_time = TimeModel.minutes_to_hhmm(c.preferred_start_min)

            item = QTableWidgetItem(c.code)
            item.setData(Qt.ItemDataRole.UserRole, c.code)
            self.table.setItem(i, 0, item)
            self.table.setItem(i, 1, QTableWidgetItem(c.name or ""))
            self.table.setItem(i, 2, QTableWidgetItem(str(c.number_of_groups)))
            self.table.setItem(i, 3, QTableWidgetItem(dur_text))
            self.table.setItem(i, 4, QTableWidgetItem(c.suggested_classroom or "—"))
            self.table.setItem(i, 5, QTableWidgetItem(msg(c.preferred_day) if c.preferred_day else "—"))
            self.table.setItem(i, 6, QTableWidgetItem(pref_time))

        self.table.setSortingEnabled(True)
        self._filter_table(self._search.text())
        self.table.clearSelection()
        self.table.setCurrentItem(None)
        for row in range(self.table.rowCount()):
            if (self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == selected_code
                    and not self.table.isRowHidden(row)):
                self.table.setCurrentCell(row, column)
                break

    def _filter_table(self, text: str):
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            code = self.table.item(row, 0)
            name = self.table.item(row, 1)
            match = (
                (code and text in code.text().lower()) or
                (name and text in name.text().lower())
            )
            self.table.setRowHidden(row, not match if text else False)
        if self.table.currentRow() >= 0 and self.table.isRowHidden(self.table.currentRow()):
            self.table.clearSelection()
            self.table.setCurrentItem(None)
