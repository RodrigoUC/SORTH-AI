"""Transactional local resource editing; cancel never mutates the working plan."""
from dataclasses import replace
from uuid import uuid4
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtWidgets import (QVBoxLayout, QAbstractItemView, QHeaderView,
    QListWidgetItem, QScrollArea, QFrame, QWidget, QApplication, QSizePolicy,
    QStyle, QStyleOptionFrame)
from .i18n_widgets import (QDialog, QLabel, QPushButton, QLineEdit, QCheckBox,
    QComboBox, QTableWidget, QTableWidgetItem, QListWidget,
    QDialogButtonBox, QMessageBox, QFormLayout, ResponsiveActionLabels,
    ResponsiveDialogButtonBox)
from .i18n import msg, language_manager
from ..scheduling.teaching_resources import Resource, ResourceCatalog

RESOURCE_TITLES = {'teacher': 'Docentes', 'student_group': 'Grupos de estudiantes',
                   'student': 'Estudiantes individuales'}


class _ResourceFormDialog(QDialog):
    """Keep resource form actions reachable while native text grows."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        content = QWidget()
        content.setObjectName('resourceContent')
        self.body = QVBoxLayout(content)
        self.scroll.setWidget(content)
        self.outer.addWidget(self.scroll, 1)
        self._focus_reveal_timer = QTimer(self)
        self._focus_reveal_timer.setSingleShot(True)
        self._focus_reveal_timer.timeout.connect(self._reveal_focus)
        self.scroll.viewport().installEventFilter(self)
        content.installEventFilter(self)
        QApplication.instance().focusChanged.connect(self._scroll_to_focus)

    def _finish(self, actions, submit):
        self.buttons = ResponsiveDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(submit)
        self.buttons.rejected.connect(self.reject)
        self.outer.addWidget(self.buttons)
        self._responsive_actions = ResponsiveActionLabels(self.scroll, actions, self)

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
                min(self.scroll.viewport().height() // 2, focused.height() // 2 + 12))


class ResourceEditor(_ResourceFormDialog):
    def __init__(self, resource, time_model, parent=None):
        super().__init__(parent)
        self.resource, self.time_model = resource, time_model
        self.result_resource = None
        self.setWindowTitle(msg('Editar recurso'))
        self.resize(540, 420)
        layout = self.body
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
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
        self.windows.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.windows.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.windows.setMinimumHeight(160)
        layout.addWidget(self.windows)
        actions = QVBoxLayout()
        self.add = QPushButton(msg('Agregar franja'))
        self.add.clicked.connect(lambda: self._add_window((1, 480, 600)))
        self.remove = QPushButton(msg('Quitar franja'))
        self.remove.clicked.connect(self._remove_window)
        actions.addWidget(self.add); actions.addWidget(self.remove)
        layout.addLayout(actions)
        self.declared.toggled.connect(self._availability_state)
        for window in resource.availability or ():
            self._add_window(window)
        self._availability_state()
        self.error = QLabel(''); self.error.setWordWrap(True)
        self.error.setAccessibleName(msg('Resultado de validación'))
        self.error.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                          Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.error.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.error.hide()
        layout.addWidget(self.error)
        self._finish([self.declared, self.add, self.remove], self._submit)
        self._set_tab_order()
        self.windows.installEventFilter(self)
        self._fit_window_columns()

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
        if hasattr(self, 'buttons'):
            self._set_tab_order()
        self._fit_window_columns()

    def _remove_window(self):
        self.windows.removeRow(self.windows.currentRow())
        self._set_tab_order()

    def _set_tab_order(self):
        ordered = [self.label, self.declared, self.windows]
        ordered.extend(self.windows.cellWidget(row, column)
                       for row in range(self.windows.rowCount()) for column in range(3))
        ordered.extend([self.add, self.remove, self.error,
                        self.buttons.button(QDialogButtonBox.StandardButton.Save),
                        self.buttons.button(QDialogButtonBox.StandardButton.Cancel)])
        for previous, following in zip(ordered, ordered[1:]):
            self.setTabOrder(previous, following)

    def eventFilter(self, watched, event):
        if watched is getattr(self, 'windows', None) and event.type() in (
                QEvent.Type.FontChange, QEvent.Type.StyleChange, QEvent.Type.LayoutRequest):
            self._fit_window_columns()
        return super().eventFilter(watched, event)

    def _fit_window_columns(self):
        # Each time must show all five HH:mm characters at the current font.
        # Only the table may scroll horizontally when those native minima need it.
        if not self.windows.rowCount():
            return
        control = self.windows.cellWidget(0, 1)
        if control is None:
            return
        option = QStyleOptionFrame()
        control.initStyleOption(option)
        text_size = control.fontMetrics().size(Qt.TextFlag.TextSingleLine, '00:00')
        text_size.setWidth(text_size.width() + 6)
        width = control.style().sizeFromContents(
            QStyle.ContentsType.CT_LineEdit, option, text_size, control).width()
        self.windows.horizontalHeader().setMinimumSectionSize(width)

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
            self.error.show()
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


class ResourceDialog(_ResourceFormDialog):
    def __init__(self, catalog, groups, time_model, parent=None):
        super().__init__(parent)
        self.catalog, self.groups, self.time_model = catalog, groups, time_model
        self.resources = list(catalog.resources)
        self.memberships = dict(catalog.memberships)
        self.result_catalog = None
        self.setWindowTitle(msg(RESOURCE_TITLES[catalog.kind]))
        self.resize(820, 620)
        layout = self.body
        intro = QLabel(msg('Agregue recursos y elija explícitamente sus sesiones. No se asignan personas automáticamente.'))
        intro.setWordWrap(True); layout.addWidget(intro)
        self.list = QListWidget(); self.list.setAccessibleName(msg('Recursos locales'))
        self.list.setMinimumHeight(100)
        layout.addWidget(self.list, 1)
        row = QVBoxLayout()
        self.resource_actions = []
        for label, handler in [('Agregar recurso', self._add), ('Editar recurso', self._edit), ('Quitar recurso', self._remove)]:
            button = QPushButton(msg(label)); button.clicked.connect(handler); row.addWidget(button)
            self.resource_actions.append(button)
        layout.addLayout(row)
        self.sessions = QTableWidget(len(groups), 3)
        self.sessions.setHorizontalHeaderLabels([msg('Sesión'), msg('Curso'), msg('Recursos asignados')])
        self.sessions.setAccessibleName(msg('Asignaciones de recursos por sesión'))
        self.sessions.setTabKeyNavigation(False)
        self.sessions.setMinimumHeight(160)
        self.sessions.setWordWrap(False)
        self.sessions.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.sessions.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sessions.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sessions.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.sessions.installEventFilter(self)
        self.sessions.viewport().installEventFilter(self)
        self.sessions.doubleClicked.connect(self._choose)
        layout.addWidget(self.sessions, 2)
        self.choose = QPushButton(msg('Elegir recursos de la sesión'))
        self.choose.clicked.connect(self._choose); layout.addWidget(self.choose)
        no_inference = QLabel(msg('Los grupos de estudiantes y las personas se asignan por separado. No se infieren matrículas ni pertenencias entre ellos.'))
        no_inference.setWordWrap(True); layout.addWidget(no_inference)
        self._finish([*self.resource_actions, self.choose], self._submit)
        language_manager().changed.connect(self._refresh)
        self._refresh()

    def _refresh(self):
        selected = self.list.currentRow()
        for row, resource in enumerate(self.resources):
            state = msg('Sin disponibilidad declarada') if resource.availability is None else msg('Disponibilidad declarada')
            item = self.list.item(row)
            if item is None:
                item = QListWidgetItem()
                self.list.addItem(item)
            item.setText(f'{resource.label} · {resource.id} · {state}')
            item.setToolTip(item.text())
        while self.list.count() > len(self.resources):
            self.list.takeItem(self.list.count() - 1)
        if selected >= 0:
            self.list.setCurrentRow(min(selected, len(self.resources)-1))
        labels = {r.id: f'{r.label} [{r.id}]' for r in self.resources}
        for row, group in enumerate(self.groups):
            for col, value in enumerate((group.group_id, group.course_name or group.course_code or '',
                    ', '.join(labels.get(r, r) for r in self.memberships.get(group.group_id) or ()) or msg('Sin recursos asignados'))):
                item = self.sessions.item(row, col)
                if item is None:
                    item = QTableWidgetItem()
                    self.sessions.setItem(row, col, item)
                item.setText(value)
                item.setToolTip(value)
        self._fit_session_columns()

    def eventFilter(self, watched, event):
        table = getattr(self, 'sessions', None)
        if table is not None and watched in (table, table.viewport()) and event.type() in (
                QEvent.Type.Resize, QEvent.Type.FontChange, QEvent.Type.StyleChange,
                QEvent.Type.LayoutRequest):
            self._fit_session_columns()
        return super().eventFilter(watched, event)

    def _fit_session_columns(self):
        # Headers must remain identifiable at enlarged fonts. Use native
        # caption hints and allow this table to scroll when all three cannot fit.
        header = self.sessions.horizontalHeader()
        widths = [header.sectionSizeHint(column) for column in range(3)]
        extra = max(0, self.sessions.viewport().width() - sum(widths))
        for column, width in enumerate(widths):
            self.sessions.setColumnWidth(column, width + extra // 3 + (column < extra % 3))

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
        dialog = _ResourceFormDialog(self)
        dialog.setWindowTitle(msg('Elegir recursos de la sesión'))
        dialog.resize(460, 400); layout = dialog.body
        label = QLabel(group.group_id)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setMinimumWidth(0)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                     Qt.TextInteractionFlag.TextSelectableByKeyboard)
        layout.addWidget(label)
        choices = QListWidget(); choices.setAccessibleName(msg('Recursos asignados'))
        choices.setMinimumHeight(140)
        # Teacher default is one; explicit multiple assignments require opt-in.
        multiple = QCheckBox(msg('Asignar varios recursos a esta sesión'))
        current = self.memberships.get(group.group_id) or ()
        multiple.setChecked(self.catalog.kind != 'teacher')
        multiple.setVisible(self.catalog.kind != 'teacher')
        layout.addWidget(multiple)
        for resource in self.resources:
            item = QListWidgetItem(f'{resource.label} [{resource.id}]')
            item.setToolTip(item.text())
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
        dialog._finish([multiple], dialog.accept)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.memberships[group.group_id] = tuple(choices.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(choices.count()) if choices.item(i).checkState() == Qt.CheckState.Checked)
            self._refresh()

    def _submit(self):
        self.result_catalog = replace(self.catalog, resources=tuple(self.resources),
                                      memberships=tuple(self.memberships.items()))
        self.accept()
