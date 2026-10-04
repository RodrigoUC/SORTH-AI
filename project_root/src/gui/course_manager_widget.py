# src/gui/course_manager_widget.py

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QHeaderView, QScrollArea, QFrame, QApplication,
    QSizePolicy, QLayout
)
from PyQt6.QtCore import Qt, QTime, pyqtSignal, QItemSelectionModel, QEvent, QTimer
from copy import deepcopy
from PyQt6.QtWidgets import (
    QCompleter
)

from ..scheduling.course import Course
from ..scheduling.time_model import TimeModel
from ..scheduling.project_calendar import ProjectCalendar

from .i18n import msg, language_manager
from .i18n_widgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem, QTimeEdit,
    QWidget, ResponsiveActionLabels, ResponsiveDialogButtonBox
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
    header.setObjectName("dialogWarningHeader")
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

    def __init__(self, parent=None, course: Course = None,
                 completions: list[tuple[str, str]] | None = None, calendar=None):
        super().__init__(parent)
        self.course = course
        self.calendar = calendar if calendar is not None else ProjectCalendar()
        self._completions = completions or []   # [(code, name), ...]
        self._code_to_name = {c: n for c, n in self._completions}
        self.setWindowTitle(msg('Agregar Curso') if not course else msg('Editar Curso'))
        self.setModal(True)
        self.resize(460, 420)
        self._init_ui()
        # An untouched restored literal must retain its exact representation.
        self._initial_text = {
            'code': self.code_edit.text(),
            'name': self.name_edit.text(),
            'suggested_classroom': self.classroom_edit.text(),
        }

    def _init_ui(self):
        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        content = QWidget()
        content.setObjectName('courseContent')
        content_layout = QVBoxLayout(content)
        layout = self.form = QFormLayout()
        content_layout.addLayout(layout)
        content_layout.addStretch()
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)

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
        self.groups_spin.setMaximum(max(50, self.course.number_of_groups if self.course else 50))
        self.groups_spin.setValue(1)
        layout.addRow(msg('Número de Grupos:'), self.groups_spin)

        # Duration — hours + minutes
        dur_layout = QHBoxLayout()
        self.dur_hours = QSpinBox()
        self.dur_hours.setAccessibleName(msg('Duración en horas'))
        self.dur_hours.setRange(0, max(14, self.course.duration_min // 60 if self.course else 14))
        self.dur_hours.setValue(1)
        self.dur_hours.setSuffix(" h")
        self.dur_mins = QSpinBox()
        self.dur_mins.setAccessibleName(msg('Duración en minutos'))
        self.dur_mins.setRange(0, 59)
        self.dur_mins.setSingleStep(5)
        self.dur_mins.setValue(30)
        self.dur_mins.setSuffix(" min")
        dur_layout.addWidget(self.dur_hours)
        dur_layout.addWidget(self.dur_mins)
        layout.addRow(msg('Duración:'), dur_layout)

        # Room type (saved value while editing, detected for a changed code)
        self.room_type_label = QLabel()
        self.room_type_label.setWordWrap(True)
        # Reserve the native wrapped hint in the form's height budget; otherwise
        # QFormLayout can steal one line from a later compound input.
        self.room_type_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.room_type_label.setTextFormat(Qt.TextFormat.PlainText)
        self.room_type_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.room_type_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addRow(msg('Tipo de Sala:'), self.room_type_label)

        # Suggested classroom
        self.classroom_edit = QLineEdit()
        self.classroom_edit.setPlaceholderText(msg('placeholder.preferred_classroom'))
        layout.addRow(msg('Aula Sugerida:'), self.classroom_edit)

        # Preferred day
        self.day_combo = QComboBox()
        self.day_combo.addItem(msg('(Sin preferencia)'), None)
        days = list(self.calendar.days)
        if self.course and self.course.preferred_day and self.course.preferred_day not in days:
            # A soft preference may be latent outside the active calendar.
            # Opening an editor must never silently erase it.
            days.append(self.course.preferred_day)
        for day in days:
            self.day_combo.addItem(msg(day), day)
        layout.addRow(msg('Día Preferido:'), self.day_combo)

        # Preferred start time — QTimeEdit for clarity
        time_group = QWidget()
        time_layout = QVBoxLayout(time_group)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.chk_pref_time = QCheckBox(msg('Activar hora preferida'))
        self.chk_pref_time.toggled.connect(self._toggle_pref_time)
        self.pref_time_edit = QTimeEdit()
        self.pref_time_edit.setAccessibleName(msg('Hora de inicio preferida'))
        self.pref_time_edit.setDisplayFormat("HH:mm")
        self.pref_time_edit.setTime(QTime(8, 0))
        self.pref_time_edit.setMinimumTime(QTime(0, 0))
        self.pref_time_edit.setMaximumTime(QTime(23, 59))
        self.pref_time_edit.setToolTip(msg('Hora de inicio preferida para este curso (ej: 08:00, 13:00)'))
        time_layout.addWidget(self.chk_pref_time)
        time_layout.addWidget(self.pref_time_edit)
        layout.addRow(msg('Hora Preferida:'), time_group)

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

        # Keep native text inputs usable rather than squeezing them alongside
        # a long label. QFormLayout wraps from these native font-size hints.
        for editor in (self.code_edit, self.name_edit, self.classroom_edit):
            editor.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        for combo in (self.day_combo, self.split_combo):
            # The native popup retains each complete option. Its longest item
            # must not impose a desktop-wide minimum on the closed form.
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(8)
            combo.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        for row in range(layout.rowCount()):
            item = layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
            if item is not None:
                item.widget().setWordWrap(True)

        self.buttons = ResponsiveDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self._responsive_actions = ResponsiveActionLabels(self.scroll, [self.chk_pref_time], self)
        self._focus_reveal_timer = QTimer(self)
        self._focus_reveal_timer.setSingleShot(True)
        self._focus_reveal_timer.timeout.connect(self._reveal_focus)
        self.scroll.viewport().installEventFilter(self)
        content.installEventFilter(self)
        QApplication.instance().focusChanged.connect(self._scroll_to_focus)
        language_manager().changed.connect(self._refresh_form_layout)

        # Load existing data if editing
        if self.course:
            # Qt limits text by UTF-16 units; accepted Excel/session values can
            # be longer than the default. Keep them fully visible and editable.
            for editor, value in ((self.code_edit, self.course.code),
                                  (self.name_edit, self.course.name),
                                  (self.classroom_edit, self.course.suggested_classroom)):
                units = len((value or '').encode('utf-16-le')) // 2
                editor.setMaxLength(max(editor.maxLength(), units))
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

    def _effective_code(self):
        text = self.code_edit.text()
        return self.course.code if self.course is not None and text == self.course.code else text.strip()

    def _required_room_type(self, code):
        if self.course is not None and code == self.course.code:
            return self.course.required_room_type
        return "LAB" if code.upper().endswith(("L", "P")) else "REGULAR"

    def _update_room_type_label(self):
        code = self._effective_code()
        room_type = self._required_room_type(code)
        if self.course is not None and code == self.course.code:
            # A restored course may intentionally disagree with its suffix.
            # Show the value this editor will preserve, not a fresh prediction.
            self.room_type_label.setText(msg('{room_type} (guardado en el curso)', room_type=room_type))
        elif room_type == 'LAB':
            self.room_type_label.setText(msg('🔬 LAB (detectado automáticamente)'))
        else:
            self.room_type_label.setText(msg('🏫 REGULAR (detectado automáticamente)'))
        self.room_type_label.setObjectName('headingText' if room_type == 'LAB' else 'successText')
        # Qt does not automatically repolish a changed object-name selector.
        # This changes only presentation; draft fields remain untouched.
        self.room_type_label.style().unpolish(self.room_type_label)
        self.room_type_label.style().polish(self.room_type_label)
        self.room_type_label.update()

    def _refresh_form_layout(self, *_):
        # Native QFormLayout can retain pre-translation height-for-width rows.
        # Refresh after the localization batch so wrapped text cannot borrow
        # height from an unrelated input below it.
        self.form.invalidate()
        layout = self.scroll.widget().layout()
        layout.invalidate()
        layout.activate()
        self.scroll.widget().updateGeometry()
        self._focus_reveal_timer.start(0)

    def _scroll_to_focus(self, previous, focused):
        if (self.isVisible() and focused is not None
                and self.scroll.widget().isAncestorOf(focused)):
            self._reveal_focus()
            self._focus_reveal_timer.start(0)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.LayoutRequest,
                            QEvent.Type.FontChange, QEvent.Type.StyleChange):
            self._focus_reveal_timer.start(0)
        return super().eventFilter(watched, event)

    def _reveal_focus(self):
        focused = QApplication.focusWidget()
        if (self.isVisible() and focused is not None and focused.isVisible()
                and self.scroll.widget().isAncestorOf(focused)):
            center = focused.mapTo(self.scroll.widget(), focused.rect().center())
            self.scroll.ensureVisible(center.x(), center.y(), 0,
                                      min(self.scroll.viewport().height() // 2,
                                          focused.height() // 2 + 12))

    def _toggle_pref_time(self, enabled: bool):
        self.pref_time_edit.setEnabled(enabled)

    def accept(self):
        if not self.code_edit.text().strip():
            QMessageBox.warning(self, msg('Advertencia'), msg('El código del curso es obligatorio.'))
            self.code_edit.setFocus()
            return
        super().accept()

    def get_course(self) -> Course | None:
        text_values = {}
        for field, editor in (('code', self.code_edit), ('name', self.name_edit),
                              ('suggested_classroom', self.classroom_edit)):
            text = editor.text()
            text_values[field] = (getattr(self.course, field)
                if self.course is not None and text == self._initial_text[field]
                else text.strip() or None)
        code = text_values['code']
        if not code:
            return None

        duration_min = self.dur_hours.value() * 60 + self.dur_mins.value()
        if duration_min <= 0:
            duration_min = 60

        room_type = self._required_room_type(code)

        preferred_day = self.day_combo.currentData()

        preferred_start_min = None
        if self.chk_pref_time.isChecked():
            t = self.pref_time_edit.time()
            preferred_start_min = t.hour() * 60 + t.minute()

        suggested = text_values['suggested_classroom']

        idx = self.split_combo.currentIndex()
        force_split = None if idx == 0 else (True if idx == 1 else False)

        course = Course(
            code=code,
            name=text_values['name'],
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

    def __init__(self, repo=None, calendar_provider=None):
        super().__init__()
        self.courses: list[Course] = []
        self._repo = repo  # SessionRepository, optional
        self._calendar_provider = calendar_provider or ProjectCalendar
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        info = QLabel(msg('Cursos a programar'))
        info.setStyleSheet("font-size: 15pt; font-weight: 600; padding: 4px 0;")
        layout.addWidget(info)
        self._empty_label = QLabel(msg('Aún no hay cursos. Cargue un Excel o agregue su primer curso.'))
        self._empty_label.setWordWrap(True)
        self._empty_label.setObjectName("mutedText")
        self._empty_label.setStyleSheet("padding: 8px 0;")
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
                # A model index is not a visual row after sorting/filtering.
                # Never leave a different course selected for the next action.
                self.table.clearSelection()
                self.table.setCurrentItem(None)
                for row in range(self.table.rowCount()):
                    item = self.table.item(row, 0)
                    if (item is not None and item.data(Qt.ItemDataRole.UserRole) == code
                            and not self.table.isRowHidden(row)):
                        self.table.setCurrentCell(row, 0)
                        break
                dialog = CourseDialog(self, self.courses[i], completions=self._get_completions(), calendar=self._calendar_provider())
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
        dialog = CourseDialog(self, completions=self._get_completions(), calendar=self._calendar_provider())
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
                                           completions=self._get_completions(), calendar=self._calendar_provider())
                    if edit_dlg.exec():
                        updated = edit_dlg.get_course()
                        if updated:
                            self._replace_course(existing, updated)
                return
            self._commit_courses([*self.courses, course], 'Agregar curso')

    def selected_course_codes(self):
        # Hidden rows never participate; stable codes, not sorted visual indices.
        return tuple(sorted(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            for row in {index.row() for index in self.table.selectionModel().selectedRows()}
            if not self.table.isRowHidden(row)))

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
        dialog = CourseDialog(self, self.courses[row], completions=self._get_completions(), calendar=self._calendar_provider())
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
        # ResizeToContents recalculates column widths synchronously for each
        # replaced cell in a visible table. Batch those calculations until the
        # complete table is ready; disabling painting alone is insufficient.
        header = self.table.horizontalHeader()
        modes = [header.sectionResizeMode(column) for column in range(header.count())]
        updates_enabled = self.table.updatesEnabled()
        try:
            self.table.setUpdatesEnabled(False)
            header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            self._refresh_table_contents()
        finally:
            for column, mode in enumerate(modes):
                header.setSectionResizeMode(column, mode)
            self.table.setUpdatesEnabled(updates_enabled)

    def _refresh_table_contents(self):
        selected_codes = self.selected_course_codes()
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
        if self.table.selectionMode() == self.table.SelectionMode.ExtendedSelection:
            for row in range(self.table.rowCount()):
                if (not self.table.isRowHidden(row) and
                        self.table.item(row, 0).data(Qt.ItemDataRole.UserRole) in selected_codes):
                    self.table.selectionModel().select(self.table.model().index(row, 0),
                        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)

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
