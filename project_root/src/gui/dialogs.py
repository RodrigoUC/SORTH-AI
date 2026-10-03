"""Focused dialogs for classroom setup and scheduling feedback."""
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QListWidgetItem
)
from PyQt6.QtCore import Qt
from ..scheduling.classroom import Classroom

from .i18n import msg, language_manager
from .i18n_widgets import (
    QListWidget, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QWidget
)


class ClassroomRestrictionsDialog(QDialog):
    """
    Dialog to configure classroom restrictions.
    Left panel: list of classrooms (checkable).
    Right panel: list of courses for the selected classroom (individually checkable).
    """

    def __init__(self, parent, classroom_course_map: dict[str, list[str]],
                 existing: dict[str, set[str]] | None = None):
        super().__init__(parent)
        self.setWindowTitle(msg('Aulas con Restricciones'))
        self.setModal(True)
        self.resize(700, 480)
        self._map = {k: list(v) for k, v in classroom_course_map.items()}
        # Working copy: classroom -> set of selected course codes
        self._selected: dict[str, set[str]] = {name: set(codes) for name, codes in self._map.items()}
        self._enabled = set(existing or {})
        if existing:
            for cls, codes in existing.items():
                self._selected[cls] = set(codes)
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout()

        info = QLabel(
            msg('Active un aula para restringirla. Luego marque los cursos que pueden usarla (los desmarcados quedan libres).')
        )
        info.setWordWrap(True)
        info.setObjectName("helpText")
        outer.addWidget(info)

        split = QHBoxLayout()

        # --- Left: classroom list ---
        left = QVBoxLayout()
        left.addWidget(QLabel(msg('Aulas:')))
        self.cls_list = QListWidget()
        self.cls_list.setAccessibleName(msg('Aulas con restricciones'))
        self.cls_list.setAccessibleDescription(msg('Use flechas para seleccionar y Espacio para marcar o desmarcar.'))
        self.cls_list.setMaximumWidth(200)
        for classroom in sorted(self._map):
            item = QListWidgetItem(classroom)
            item.setCheckState(
                Qt.CheckState.Checked if classroom in self._enabled
                else Qt.CheckState.Unchecked
            )
            self.cls_list.addItem(item)
        self.cls_list.currentItemChanged.connect(self._on_classroom_selected)
        left.addWidget(self.cls_list)
        split.addLayout(left)

        # --- Right: course list for selected classroom ---
        right = QVBoxLayout()
        self._course_label = QLabel(msg('Seleccione un aula'))
        self._course_label.setStyleSheet("font-weight: bold;")
        right.addWidget(self._course_label)
        self.course_list = QListWidget()
        self.course_list.setAccessibleName(msg('Cursos permitidos en el aula seleccionada'))
        self.course_list.setAccessibleDescription(msg('Use flechas para seleccionar y Espacio para marcar o desmarcar.'))
        self.course_list.itemChanged.connect(self._on_course_toggled)
        right.addWidget(self.course_list)

        btn_row = QHBoxLayout()
        btn_all = QPushButton(msg('Marcar todos'))
        btn_none = QPushButton(msg('Desmarcar todos'))
        btn_all.clicked.connect(self._check_all)
        btn_none.clicked.connect(self._uncheck_all)
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        right.addLayout(btn_row)
        split.addLayout(right)

        outer.addLayout(split)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.setLayout(outer)

        # Select first item
        if self.cls_list.count():
            self.cls_list.setCurrentRow(0)

    def _current_classroom(self) -> str | None:
        item = self.cls_list.currentItem()
        return item.text() if item else None

    def _on_classroom_selected(self, current, _previous):
        if not current:
            return
        classroom = current.text()
        self._course_label.setText(msg('Cursos para {p1}:', p1=classroom))
        self.course_list.blockSignals(True)
        self.course_list.clear()
        selected_codes = self._selected.get(classroom, set(self._map.get(classroom, [])))
        for code in sorted(self._map.get(classroom, [])):
            item = QListWidgetItem(code)
            item.setCheckState(
                Qt.CheckState.Checked if code in selected_codes
                else Qt.CheckState.Unchecked
            )
            self.course_list.addItem(item)
        self.course_list.blockSignals(False)

    def _on_course_toggled(self, _item):
        classroom = self._current_classroom()
        if not classroom:
            return
        # Keep draft selections even while the room restriction is disabled.
        self._save_current_courses(classroom)

    def _find_cls_item(self, classroom: str) -> QListWidgetItem | None:
        for i in range(self.cls_list.count()):
            item = self.cls_list.item(i)
            if item.text() == classroom:
                return item
        return None

    def _save_current_courses(self, classroom: str):
        codes = set()
        for i in range(self.course_list.count()):
            item = self.course_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                codes.add(item.text())
        # Empty is an explicit choice, never the uninitialized default.
        self._selected[classroom] = codes

    def _check_all(self):
        self.course_list.blockSignals(True)
        for i in range(self.course_list.count()):
            self.course_list.item(i).setCheckState(Qt.CheckState.Checked)
        self.course_list.blockSignals(False)
        classroom = self._current_classroom()
        if classroom:
            self._save_current_courses(classroom)

    def _uncheck_all(self):
        self.course_list.blockSignals(True)
        for i in range(self.course_list.count()):
            self.course_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.course_list.blockSignals(False)
        classroom = self._current_classroom()
        if classroom:
            self._selected[classroom] = set()

    def get_restrictions(self) -> dict[str, set[str]]:
        """Return {classroom: {course_codes}} only for checked+non-empty classrooms."""
        result = {}
        for i in range(self.cls_list.count()):
            item = self.cls_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                classroom = item.text()
                codes = self._selected.get(classroom, set())
                if codes:
                    result[classroom] = set(codes)
        return result


class AddClassroomDialog(QDialog):
    """Dialog to add a new classroom to the current session."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(msg('Agregar Aula'))
        self.setModal(True)
        self.resize(420, 360)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout()
        layout.setSpacing(10)

        self.inp_code     = QLineEdit()
        self.inp_code.setPlaceholderText(msg('placeholder.classroom_code'))
        self.inp_desc     = QLineEdit()
        self.inp_desc.setPlaceholderText(msg('Ej: Aula General'))
        self.inp_campus   = QLineEdit()
        self.inp_campus.setPlaceholderText(msg('Ej: HO'))
        self.inp_capacity = QSpinBox()
        self.inp_capacity.setRange(1, 500)
        self.inp_capacity.setValue(30)
        self.inp_type     = QComboBox()
        self.inp_type.addItems(["REGULAR", "LAB"])
        self.inp_type.setToolTip(
            msg('Detectado automáticamente por el código (L al inicio → LAB).\nPuedes cambiarlo manualmente si es necesario.')
        )

        self.inp_code.textChanged.connect(self._update_type_preview)

        layout.addRow(msg('Código *:'), self.inp_code)
        layout.addRow(msg('Descripción:'), self.inp_desc)
        layout.addRow(msg('Campus:'), self.inp_campus)
        layout.addRow(msg('Capacidad *:'), self.inp_capacity)
        layout.addRow(msg('Tipo de sala:'), self.inp_type)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        outer = QVBoxLayout()
        outer.addLayout(layout)
        outer.addWidget(buttons)
        self.setLayout(outer)

    def _update_type_preview(self, code: str):
        room_type = "LAB" if code.strip().upper().startswith("L") else "REGULAR"
        self.inp_type.setCurrentText(room_type)

    def _on_accept(self):
        if not self.inp_code.text().strip():
            QMessageBox.warning(self, msg('Error'), msg('El código del aula es obligatorio.'))
            self.inp_code.setFocus()
            return
        self.accept()

    def get_classroom(self) -> Classroom:
        code = self.inp_code.text().strip()
        room_type = self.inp_type.currentText()  # use whatever the user selected
        return Classroom(
            name=code,
            capacity=self.inp_capacity.value(),
            room_type=room_type,
            description=self.inp_desc.text().strip(),
            campus=self.inp_campus.text().strip(),
        )


class _InfoDialog(QDialog):
    """Styled info/warning dialog with colored header."""

    def __init__(self, parent, title: str, message: str, warning: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        icon = "\u26a0\ufe0f" if warning else "\u2705"
        header = QLabel(msg('  {p1}  {p3}', p1=icon, p3=title))
        header.setObjectName("dialogWarningHeader" if warning else "dialogInfoHeader")
        outer.addWidget(header)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(28, 20, 28, 20)
        body_layout.setSpacing(20)

        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.PlainText)
        lbl.setStyleSheet("font-size: 11pt;")
        lbl.setMinimumWidth(440)
        body_layout.addWidget(lbl)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        body_layout.addWidget(buttons)
        outer.addWidget(body)

        self.setLayout(outer)
