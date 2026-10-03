"""Detached calendar editor: preview first, atomic project transition second."""
from PyQt6.QtCore import QTime, Qt, QEvent, QTimer
from PyQt6.QtWidgets import (QVBoxLayout, QGridLayout,
                            QHeaderView, QScrollArea, QWidget, QFrame, QApplication)
from .i18n_widgets import (QDialog, QLabel, QPushButton, QCheckBox, QTableWidget,
                           QDialogButtonBox, QMessageBox, ResponsiveActionLabels,
                           ResponsiveDialogButtonBox, QFormLayout, QTimeEdit)
from .i18n import msg
from ..scheduling.project_calendar import ProjectCalendar, DAYS
from ..application.calendar_transition import preview_calendar_change


class CalendarDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(msg('Calendario del proyecto'))
        self.resize(620, 540)
        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        content = QWidget()
        content.setObjectName('calendarContent')
        layout = QVBoxLayout(content)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)
        hint = QLabel(msg('Define días lectivos, horas y descansos. El calendario guardado se respeta aunque ocultes el editor.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        # Keep complete localized day names at desktop accessibility font sizes.
        # The body scrolls vertically rather than growing beyond the screen.
        days = QGridLayout()
        layout.addLayout(days)
        self.days = {}
        for index, day in enumerate(DAYS):
            control = QCheckBox(msg(day))
            control.setAccessibleName(msg(day))
            days.addWidget(control, index // 2, index % 2)
            self.days[day] = control
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
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
        self.breaks.setTabKeyNavigation(False)
        self.breaks.setHorizontalHeaderLabels([msg('Inicio'), msg('Fin')])
        self.breaks.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.breaks.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.breaks.setMinimumHeight(160)
        layout.addWidget(self.breaks)
        row = QVBoxLayout()
        layout.addLayout(row)
        self.break_actions = []
        for title, action in [('Añadir descanso', self.add_break), ('Quitar descanso seleccionado', self.remove_break),
                              ('Restablecer calendario predeterminado', lambda: self.load(ProjectCalendar()))]:
            button = QPushButton(msg(title))
            button.clicked.connect(lambda _=False, callback=action: callback())
            row.addWidget(button)
            self.break_actions.append(button)
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        self.feedback.setAccessibleName(msg('Resultado de la revisión del calendario'))
        self.feedback.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                              Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.feedback.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.feedback.hide()
        layout.addWidget(self.feedback)
        self.buttons = ResponsiveDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.apply_button = QPushButton(msg('Revisar y aplicar'))
        self.buttons.addButton(self.apply_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        outer.addWidget(self.buttons)
        self._responsive_actions = ResponsiveActionLabels(
            self.scroll, [*self.days.values(), *self.break_actions], self)
        self._focus_reveal_timer = QTimer(self)
        self._focus_reveal_timer.setSingleShot(True)
        self._focus_reveal_timer.timeout.connect(self._reveal_focus)
        self.scroll.viewport().installEventFilter(self)
        content.installEventFilter(self)
        QApplication.instance().focusChanged.connect(self._scroll_to_focus)
        self.load(window.calendar)

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
            # Reveal the whole input frame; QTimeEdit's cursor rectangle alone
            # can leave its border or spin buttons outside a compact viewport.
            center = focused.mapTo(self.scroll.widget(), focused.rect().center())
            self.scroll.ensureVisible(center.x(), center.y(), 0,
                                      min(self.scroll.viewport().height() // 2,
                                          focused.height() // 2 + 12))

    def _show_feedback(self, message):
        self.feedback.setText(message)
        self.feedback.show()
        self.feedback.setFocus(Qt.FocusReason.OtherFocusReason)

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
        self._set_tab_order()

    def remove_break(self):
        row = self.breaks.currentRow()
        if row >= 0:
            self.breaks.removeRow(row)
            self._set_tab_order()

    def load(self, calendar):
        for day, control in self.days.items():
            control.setChecked(day in calendar.days)
        self.opening.setTime(QTime(calendar.day_start // 60, calendar.day_start % 60))
        self.closing.setTime(QTime((calendar.day_end // 60) % 24, calendar.day_end % 60))
        self.breaks.setRowCount(0)
        for start, end in calendar.breaks:
            self.add_break(start, end)
        self._set_tab_order()

    def _set_tab_order(self):
        # Cell widgets are created after the footer and on repeated Add/Reset.
        # Place them beside their table rather than at the end of Qt's chain.
        ordered = [*self.days.values(), self.opening, self.closing, self.breaks]
        ordered.extend(self.breaks.cellWidget(row, column)
                       for row in range(self.breaks.rowCount()) for column in range(2))
        ordered.extend([*self.break_actions, self.feedback, self.apply_button,
                        self.buttons.button(QDialogButtonBox.StandardButton.Cancel)])
        for previous, following in zip(ordered, ordered[1:]):
            self.setTabOrder(previous, following)

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
            self._show_feedback(msg('Revisa días, horas y descansos: deben ser válidos, no solaparse y dejar tiempo lectivo. {detail}', detail=msg(str(error))))
            return
        if set(preview.affected) & window.pinned_group_ids:
            self._show_feedback(msg('Hay sesiones fijadas afectadas. Desfíjalas explícitamente antes de cambiar el calendario.'))
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
            self._show_feedback(msg('No se pudo guardar el calendario. No se aplicaron cambios.'))
