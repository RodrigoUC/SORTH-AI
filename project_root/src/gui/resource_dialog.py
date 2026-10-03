"""Transactional local resource editing; cancel never mutates the working plan."""
from dataclasses import replace
from uuid import uuid4
from PyQt6.QtCore import Qt, QTime
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QAbstractItemView, QHeaderView, QListWidgetItem
from .i18n_widgets import (QDialog, QLabel, QPushButton, QLineEdit, QCheckBox,
    QComboBox, QTimeEdit, QTableWidget, QTableWidgetItem, QListWidget,
    QDialogButtonBox, QMessageBox, QFormLayout)
from .i18n import msg, language_manager
from ..scheduling.teaching_resources import Resource, ResourceCatalog

RESOURCE_TITLES = {'teacher': 'Docentes', 'student_group': 'Grupos de estudiantes',
                   'student': 'Estudiantes individuales'}


class ResourceEditor(QDialog):
    def __init__(self, resource, time_model, parent=None):
        super().__init__(parent)
        self.resource, self.time_model = resource, time_model
        self.result_resource = None
        self.setWindowTitle(msg('Editar recurso'))
        self.resize(540, 420)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.label = QLineEdit(resource.label)
        form.addRow(msg('Nombre o alias'), self.label)
        layout.addLayout(form)
        privacy = QLabel(msg('Use un alias si lo prefiere. No se necesitan correos, edades ni identificaciones personales.'))
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        self.declared = QCheckBox(msg('Limitar a la disponibilidad declarada'))
        self.declared.setChecked(resource.availability is not None)
        layout.addWidget(self.declared)
        note = QLabel(msg('Sin declarar: no limita horarios. Declarada sin franjas: ninguna sesión puede asignarse.'))
        note.setWordWrap(True)
        layout.addWidget(note)
        self.windows = QTableWidget(0, 3)
        self.windows.setHorizontalHeaderLabels([msg('Día'), msg('Inicio'), msg('Fin')])
        self.windows.setAccessibleName(msg('Disponibilidad declarada'))
        self.windows.setTabKeyNavigation(False)
        self.windows.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.windows)
        actions = QHBoxLayout()
        self.add = QPushButton(msg('Agregar franja'))
        self.add.clicked.connect(lambda: self._add_window((1, 480, 600)))
        self.remove = QPushButton(msg('Quitar franja'))
        self.remove.clicked.connect(lambda: self.windows.removeRow(self.windows.currentRow()))
        actions.addWidget(self.add); actions.addWidget(self.remove)
        layout.addLayout(actions)
        self.declared.toggled.connect(self._availability_state)
        for window in resource.availability or ():
            self._add_window(window)
        self._availability_state()
        self.error = QLabel(''); self.error.setWordWrap(True)
        self.error.setAccessibleName(msg('Resultado de validación'))
        self.error.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._submit); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _availability_state(self):
        for widget in (self.windows, self.add, self.remove):
            widget.setEnabled(self.declared.isChecked())

    def _add_window(self, window):
        row = self.windows.rowCount(); self.windows.insertRow(row)
        day = QComboBox()
        for index, name in self.time_model.index_to_day.items():
            day.addItem(msg(name), index)
        day.setCurrentIndex(day.findData(window[0])); day.setAccessibleName(msg('Día'))
        self.windows.setCellWidget(row, 0, day)
        for col, minutes in ((1, window[1]), (2, window[2])):
            time = QLineEdit(f'{minutes // 60:02}:{minutes % 60:02}')
            time.setPlaceholderText('HH:mm')
            time.setAccessibleName(msg('Inicio') if col == 1 else msg('Fin'))
            self.windows.setCellWidget(row, col, time)

    def _submit(self):
        windows = None
        if self.declared.isChecked():
            windows = tuple((self.windows.cellWidget(row, 0).currentData(),
                             self._minutes(row, 1), self._minutes(row, 2))
                            for row in range(self.windows.rowCount()))
        candidate = Resource(self.resource.id, self.label.text().strip(), windows)
        errors = ResourceCatalog(resources=(candidate,)).structure_issues(set(), self.time_model)
        if errors:
            self.error.setText(msg('Revise el nombre y las franjas: el final debe ser posterior al inicio.'))
            self.error.setFocus()
            return
        if windows == () and QMessageBox.question(self, msg('Disponibilidad vacía'),
                msg('No se permitirá ninguna sesión para este recurso. ¿Guardar disponibilidad vacía?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
            return
        self.result_resource = candidate
        self.accept()

    def _minutes(self, row, col):
        import re
        value = self.windows.cellWidget(row, col).text()
        if not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]|24:00', value):
            return -1
        hours, minutes = map(int, value.split(':'))
        return hours * 60 + minutes


class ResourceDialog(QDialog):
    def __init__(self, catalog, groups, time_model, parent=None):
        super().__init__(parent)
        self.catalog, self.groups, self.time_model = catalog, groups, time_model
        self.resources = list(catalog.resources)
        self.memberships = dict(catalog.memberships)
        self.result_catalog = None
        self.setWindowTitle(msg(RESOURCE_TITLES[catalog.kind]))
        self.resize(820, 620)
        layout = QVBoxLayout(self)
        intro = QLabel(msg('Agregue recursos y elija explícitamente sus sesiones. No se asignan personas automáticamente.'))
        intro.setWordWrap(True); layout.addWidget(intro)
        self.list = QListWidget(); self.list.setAccessibleName(msg('Recursos locales'))
        layout.addWidget(self.list, 1)
        row = QHBoxLayout()
        for label, handler in [('Agregar recurso', self._add), ('Editar recurso', self._edit), ('Quitar recurso', self._remove)]:
            button = QPushButton(msg(label)); button.clicked.connect(handler); row.addWidget(button)
        layout.addLayout(row)
        self.sessions = QTableWidget(len(groups), 3)
        self.sessions.setHorizontalHeaderLabels([msg('Sesión'), msg('Curso'), msg('Recursos asignados')])
        self.sessions.setAccessibleName(msg('Asignaciones de recursos por sesión'))
        self.sessions.setTabKeyNavigation(False)
        self.sessions.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sessions.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sessions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sessions.doubleClicked.connect(self._choose)
        layout.addWidget(self.sessions, 2)
        self.choose = QPushButton(msg('Elegir recursos de la sesión'))
        self.choose.clicked.connect(self._choose); layout.addWidget(self.choose)
        no_inference = QLabel(msg('Los grupos de estudiantes y las personas se asignan por separado. No se infieren matrículas ni pertenencias entre ellos.'))
        no_inference.setWordWrap(True); layout.addWidget(no_inference)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._submit); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        language_manager().changed.connect(self._refresh)
        self._refresh()

    def _refresh(self):
        selected = self.list.currentRow()
        self.list.clear()
        for resource in self.resources:
            state = msg('Sin disponibilidad declarada') if resource.availability is None else msg('Disponibilidad declarada')
            self.list.addItem(QListWidgetItem(f'{resource.label} · {resource.id} · {state}'))
        if selected >= 0:
            self.list.setCurrentRow(min(selected, len(self.resources)-1))
        labels = {r.id: f'{r.label} [{r.id}]' for r in self.resources}
        for row, group in enumerate(self.groups):
            for col, value in enumerate((group.group_id, group.course_name or group.course_code or '',
                    ', '.join(labels.get(r, r) for r in self.memberships.get(group.group_id) or ()) or msg('Sin recursos asignados'))):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.sessions.setItem(row, col, item)

    def _add(self):
        editor = ResourceEditor(Resource(uuid4().hex, ''), self.time_model, self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.resources.append(editor.result_resource); self._refresh()

    def _edit(self):
        row = self.list.currentRow()
        if row < 0: return
        editor = ResourceEditor(self.resources[row], self.time_model, self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.resources[row] = editor.result_resource; self._refresh()

    def _remove(self):
        row = self.list.currentRow()
        if row < 0: return
        resource = self.resources[row]
        if QMessageBox.question(self, msg('Quitar recurso'),
                msg('¿Quitar {name} y sus asignaciones de todas las sesiones? Cancelar conserva todo.', name=resource.label),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
            return
        del self.resources[row]
        self.memberships = {gid: None if ids is None else tuple(r for r in ids if r != resource.id)
                            for gid, ids in self.memberships.items()}
        self._refresh()

    def _choose(self):
        row = self.sessions.currentRow()
        if row < 0: return
        group = self.groups[row]
        dialog = QDialog(self); dialog.setWindowTitle(msg('Elegir recursos de la sesión'))
        dialog.resize(460, 400); layout = QVBoxLayout(dialog)
        label = QLabel(group.group_id); layout.addWidget(label)
        choices = QListWidget(); choices.setAccessibleName(msg('Recursos asignados'))
        # Teacher default is one; explicit multiple assignments require opt-in.
        multiple = QCheckBox(msg('Asignar varios recursos a esta sesión'))
        current = self.memberships.get(group.group_id) or ()
        multiple.setChecked(self.catalog.kind != 'teacher')
        multiple.setVisible(self.catalog.kind != 'teacher')
        layout.addWidget(multiple)
        for resource in self.resources:
            item = QListWidgetItem(f'{resource.label} [{resource.id}]')
            item.setData(Qt.ItemDataRole.UserRole, resource.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if resource.id in current else Qt.CheckState.Unchecked)
            choices.addItem(item)
        def enforce_single(changed=None):
            if multiple.isChecked(): return
            checked = [choices.item(i) for i in range(choices.count())
                       if choices.item(i).checkState() == Qt.CheckState.Checked]
            keep = changed if changed in checked else (checked[0] if checked else None)
            choices.blockSignals(True)
            for item in checked:
                if item is not keep: item.setCheckState(Qt.CheckState.Unchecked)
            choices.blockSignals(False)
        choices.itemChanged.connect(enforce_single)
        multiple.toggled.connect(lambda: enforce_single())
        layout.addWidget(choices)
        note = QLabel(msg('Sin selección no se aplica esta restricción. Cada recurso seleccionado queda ocupado durante toda la sesión.'))
        note.setWordWrap(True); layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.memberships[group.group_id] = tuple(choices.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(choices.count()) if choices.item(i).checkState() == Qt.CheckState.Checked)
            self._refresh()

    def _submit(self):
        self.result_catalog = replace(self.catalog, resources=tuple(self.resources),
                                      memberships=tuple(self.memberships.items()))
        self.accept()
