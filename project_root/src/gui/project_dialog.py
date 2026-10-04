"""Named snapshot workflows. Existing single-session autosave stays unchanged."""
import sqlite3
import tempfile
from pathlib import Path
from PyQt6.QtCore import QItemSelectionModel, QModelIndex, QSignalBlocker, Qt, QEvent, QTimer
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QBoxLayout, QAbstractItemView, QHeaderView,
                            QPlainTextEdit, QScrollArea, QFrame, QWidget, QStyle, QStyleOptionButton,
                            QApplication)
from .i18n_widgets import (QDialog, QLabel, QPushButton, QDialogButtonBox, QLineEdit,
                           QTableWidget, QTableWidgetItem, QMessageBox,
                           ResponsiveActionLabels, ResponsiveDialogButtonBox)
from .i18n import msg, join_messages, language_manager, Message
from ..infrastructure.project_repository import ProjectRepository
from ..infrastructure.session_repository import SessionRepository
from ..application.scenario_comparison import scenario_metadata, compare_scenarios, session_fingerprint, validate_scenario_metadata
from ..scheduling.validation import validate_schedule
from ..scheduling.time_model import TimeModel
from ..scheduling.project_calendar import ProjectCalendar, DAYS
from copy import deepcopy


def _readable_label(text=''):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse |
                                  Qt.TextInteractionFlag.TextSelectableByKeyboard)
    label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    return label


class _ScrollableProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sized_buttons = []
        self._reserving_buttons = False
        self.outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        content = QWidget()
        self.body = QVBoxLayout(content)
        self.scroll.setWidget(content)
        self.outer.addWidget(self.scroll, 1)
        self._focus_reveal_timer = QTimer(self)
        self._focus_reveal_timer.setSingleShot(True)
        self._focus_reveal_timer.timeout.connect(self._reveal_focus)
        self.scroll.viewport().installEventFilter(self)
        content.installEventFilter(self)
        QApplication.instance().focusChanged.connect(self._scroll_to_focus)

    def _scroll_to_focus(self, previous, focused):
        if (self.isVisible() and focused is not None
                and self.scroll.widget().isAncestorOf(focused)):
            self._reveal_focus()
            self._focus_reveal_timer.start(0)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.LayoutRequest,
                            QEvent.Type.FontChange, QEvent.Type.StyleChange,
                            QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self._reserve_button_heights()
            self._focus_reveal_timer.start(0)
        return super().eventFilter(watched, event)

    def _finish_buttons(self, buttons):
        self.close_buttons = buttons
        self._sized_buttons = [*getattr(self, 'buttons', {}).values(), *buttons.buttons()]
        for button in self._sized_buttons:
            button.installEventFilter(self)
        self._reserve_button_heights()

    def _reserve_button_heights(self):
        if self._reserving_buttons:
            return
        self._reserving_buttons = True
        try:
            for button in self._sized_buttons:
                option = QStyleOptionButton()
                # Standard footer buttons are constructed inside Qt, so SIP
                # cannot call their protected initStyleOption method.
                option.initFrom(button)
                option.text = button.text()
                if button.autoDefault():
                    option.features |= QStyleOptionButton.ButtonFeature.AutoDefaultButton
                if button.isDefault():
                    option.features |= QStyleOptionButton.ButtonFeature.DefaultButton
                option.state |= QStyle.StateFlag.State_HasFocus
                text = button.fontMetrics().size(Qt.TextFlag.TextShowMnemonic, button.text())
                size = button.style().sizeFromContents(
                    QStyle.ContentsType.CT_PushButton, option, text, button)
                if button.minimumHeight() != size.height():
                    button.setMinimumHeight(size.height())
                if button.parentWidget() is self.close_buttons and button.minimumWidth() != size.width():
                    button.setMinimumWidth(size.width())
        finally:
            self._reserving_buttons = False

    def _reveal_focus(self):
        focused = QApplication.focusWidget()
        if (self.isVisible() and focused is not None and focused.isVisible()
                and self.scroll.widget().isAncestorOf(focused)):
            center = focused.mapTo(self.scroll.widget(), focused.rect().center())
            self.scroll.ensureVisible(center.x(), center.y(), 0,
                min(self.scroll.viewport().height() // 2, focused.height() // 2 + 12))


def ask_name(parent, title):
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)
    label = QLabel(msg('Nombre (1–120 caracteres)'))
    edit = QLineEdit()
    edit.setMaxLength(120)
    label.setBuddy(edit)
    layout.addWidget(label)
    layout.addWidget(edit)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    edit.setFocus()
    return edit.text() if dialog.exec() == QDialog.DialogCode.Accepted else None


class ProjectDialog(_ScrollableProjectDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(msg('Proyectos y escenarios'))
        self.resize(850, 540)
        self.catalog = ProjectRepository(Path(window._repo._db_path).with_name('sorth_projects.db'))
        persisted = window._repo.load_session()
        self.catalog.preserve_legacy(window._repo, scenario_metadata(calendar=(persisted or {}).get('calendar', ProjectCalendar())))
        outer, layout = self.outer, self.body
        hint = _readable_label(msg('Cada escenario es una copia independiente. Guardar como nunca sobrescribe. Selecciona dos filas para comparar.'))
        layout.addWidget(hint)
        self.table = QTableWidget(0, 3)
        self._headers = [QTableWidgetItem(msg(text)) for text in ('Proyecto', 'Escenario', 'Guardado (UTC)')]
        for index, item in enumerate(self._headers):
            self.table.setHorizontalHeaderItem(index, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAccessibleName(msg('Escenarios guardados'))
        self.table.setMinimumHeight(180)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)
        row = QHBoxLayout()
        layout.addLayout(row)
        self._action_rows = [row]
        self._fitting_actions = False
        self.buttons = {}
        for key, title, handler in (
            ('new', 'Crear proyecto desde la sesión', self.create),
            ('save', 'Guardar como escenario', self.save_as),
            ('open', 'Abrir escenario', self.open_selected),
            ('duplicate', 'Duplicar', self.duplicate),
            ('rename', 'Renombrar', self.rename),
            ('compare', 'Comparar', self.compare),
        ):
            if key == 'duplicate':
                row = QHBoxLayout()
                layout.addLayout(row)
                self._action_rows.append(row)
            button = QPushButton(msg(title))
            button.clicked.connect(lambda checked=False, action=handler: self._run(action))
            row.addWidget(button)
            self.buttons[key] = button
        self.feedback = _readable_label()
        self.feedback.hide()
        layout.addWidget(self.feedback)
        close = ResponsiveDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        outer.addWidget(close)
        self._finish_buttons(close)
        self._responsive_actions = ResponsiveActionLabels(self.scroll, self.buttons.values(), self)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.refresh()
        language_manager().changed.connect(self._translate_headers)
        hint.setFocus()

    def _translate_headers(self, *_):
        for item, label in zip(self._headers, ('Proyecto', 'Escenario', 'Guardado (UTC)')):
            item.setText(msg(label))
        self._fit_action_rows()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.FontChange,
                            QEvent.Type.StyleChange, QEvent.Type.LayoutRequest):
            self._fit_action_rows()
        return super().eventFilter(watched, event)

    def _fit_action_rows(self):
        if not hasattr(self, '_action_rows') or self._fitting_actions:
            return
        self._fitting_actions = True
        try:
            margins = self.scroll.widget().layout().contentsMargins()
            available = self.scroll.viewport().width() - margins.left() - margins.right()
            for row in self._action_rows:
                required = row.spacing() * (row.count() - 1)
                for index in range(row.count()):
                    button = row.itemAt(index).widget()
                    option = QStyleOptionButton()
                    button.initStyleOption(option)
                    text = button.fontMetrics().size(Qt.TextFlag.TextShowMnemonic, button._presentation_text)
                    required += button.style().sizeFromContents(
                        QStyle.ContentsType.CT_PushButton, option, text, button).width() + 4
                direction = (QBoxLayout.Direction.TopToBottom if required > available
                             else QBoxLayout.Direction.LeftToRight)
                if row.direction() != direction:
                    row.setDirection(direction)
        finally:
            self._fitting_actions = False

    def _run(self, action):
        try:
            action()
        except sqlite3.IntegrityError:
            self._show_feedback(msg('Ese nombre ya existe. Usa otro nombre; no se reemplazó ningún escenario.'))
        except Exception as error:
            self._show_feedback(msg('No se pudo completar la operación. El escenario guardado se conserva. {detail}', detail=str(error)))

    def _show_feedback(self, message):
        self.feedback.setText(message)
        self.feedback.show()
        self.feedback.setFocus(Qt.FocusReason.OtherFocusReason)

    def selected(self):
        return [self.rows[index.row()] for index in self.table.selectionModel().selectedRows()]

    def _selection_changed(self):
        count = len(self.selected())
        for key in ('save', 'open', 'duplicate', 'rename'):
            self.buttons[key].setEnabled(count == 1)
        self.buttons['compare'].setEnabled(count == 2)

    def refresh(self):
        selected_ids = {row['id'] for row in self.selected()} if hasattr(self, 'rows') else set()
        current = self.table.currentIndex()
        current_id = self.rows[current.row()]['id'] if current.isValid() else None
        rows = self.catalog.list_scenarios()
        # Catalog ordering can insert rows before the selected scenarios. Keep
        # both multi-selection and the keyboard anchor attached to their IDs.
        with QSignalBlocker(self.table):
            self.rows = rows
            self.table.setRowCount(len(rows))
            self.table.clearSelection()
            model = self.table.selectionModel()
            model.setCurrentIndex(QModelIndex(), QItemSelectionModel.SelectionFlag.NoUpdate)
            for index, row in enumerate(rows):
                for column, key in enumerate(('project_name', 'name', 'created_at')):
                    self.table.setItem(index, column, QTableWidgetItem(row[key]))
                if row['id'] in selected_ids:
                    model.select(self.table.model().index(index, 0),
                                 QItemSelectionModel.SelectionFlag.Select |
                                 QItemSelectionModel.SelectionFlag.Rows)
                if row['id'] == current_id:
                    model.setCurrentIndex(self.table.model().index(index, current.column()),
                                          QItemSelectionModel.SelectionFlag.NoUpdate)
        self._selection_changed()

    def _save_working(self):
        if not self.window._save_session():
            raise OSError(self.window._save_error or 'Working session could not be saved')

    def _saved(self, scenario_id):
        self.refresh()
        row = next(row for row in self.rows if row['id'] == scenario_id)
        baseline = session_fingerprint(self.catalog.read(scenario_id)[0])
        self._activate_scenario(row, baseline)
        self.window._update_save_state()
        self._show_feedback(msg('Escenario guardado. Las ediciones posteriores no cambian esta copia.'))

    def _activate_scenario(self, row, baseline):
        # Resolve fallible reads/fingerprints first, so an incomplete readback
        # cannot combine a new scenario name with the previous copy's baseline.
        self.window._scenario_id = row['id']
        self.window._scenario_name = row['project_name'] + ' / ' + row['name']
        self.window._scenario_baseline = baseline
        self.window._scenario_dirty = False
        self.window._scenario_comparison_error = None

    def create(self):
        name = ask_name(self, msg('Crear proyecto desde la sesión'))
        if name is None:
            return
        self._save_working()
        _, scenario = self.catalog.create_project(name, '1', self.window._repo,
                                                  scenario_metadata(self.window._algorithm_version, self.window.calendar))
        self._saved(scenario)

    def save_as(self):
        selected = self.selected()[0]
        name = ask_name(self, msg('Guardar como escenario'))
        if name is None:
            return
        self._save_working()
        scenario = self.catalog.save_as(selected['project_id'], name, self.window._repo,
                                        scenario_metadata(self.window._algorithm_version, self.window.calendar))
        self._saved(scenario)

    def duplicate(self):
        name = ask_name(self, msg('Duplicar'))
        if name is not None:
            self.catalog.duplicate(self.selected()[0]['id'], name)
            self.refresh()

    def rename(self):
        name = ask_name(self, msg('Renombrar'))
        if name is not None:
            scenario_id = self.selected()[0]['id']
            self.catalog.rename(scenario_id, name)
            self.refresh()
            if self.window._scenario_id == scenario_id:
                row = next(row for row in self.rows if row['id'] == scenario_id)
                self.window._scenario_name = row['project_name'] + ' / ' + row['name']
                self.window._update_save_state()

    def _preflight_restore(self, data):
        seed = data['seed']
        if seed is not None and (type(seed) is not int or
                not self.window.seed_input.minimum() <= seed <= self.window.seed_input.maximum()):
            raise ValueError('Scenario seed is outside the supported range')
        # Exercise the same deserialization, domain reconstruction and Qt
        # rendering on an isolated temporary session/window. No current GUI or
        # persistent working state changes if a malformed value cannot render.
        from .main_window import MainWindow
        with tempfile.TemporaryDirectory(prefix='sorth-open-check-') as directory:
            repository = SessionRepository(str(Path(directory) / 'candidate.db'))
            repository.save_session(**data)
            from PyQt6.QtCore import QSettings
            candidate = MainWindow(repository, restore_session=False,
                feature_settings=QSettings(str(Path(directory) / "preferences.ini"), QSettings.Format.IniFormat))
            try:
                candidate._restore_session_if_exists(confirm=False, show_status=False)
                if candidate._restore_failed:
                    raise ValueError(candidate._save_error)
            finally:
                candidate._unsaved = False
                candidate.close()
                candidate.deleteLater()

    def open_selected(self):
        row = self.selected()[0]
        data, metadata = self.catalog.read(row['id'])
        validate_scenario_metadata(metadata, data.get("calendar", ProjectCalendar()))
        self._preflight_restore(data)
        # Validate before touching current memory/disk; no silent removal of pins
        # or manual exceptions. Work on detached room objects only.
        groups = [g for c in data['courses'] for g in c.generate_groups()]
        rooms = deepcopy(data['classrooms'])
        for name, room in rooms.items():
            room.allowed_courses = data['restrictions'].get(name)
        errors = validate_schedule(data['assignments'] or {}, groups, rooms, TimeModel.from_calendar(data.get("calendar", ProjectCalendar())),
                                   data.get('lab_overrides', set()), resources=data.get('resources'))
        if errors:
            raise ValueError('\n'.join(str(error.render(msg)) for error in errors))
        baseline = session_fingerprint(data)
        if QMessageBox.question(self, msg('Abrir escenario'),
                msg('Se guardará una copia de recuperación de la sesión actual antes de abrir {name}. ¿Continuar?', name=row['name']),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self._save_working()
        self.window._repo.backup_session()
        self.window._repo.save_session(**data)
        # The target is now durable. Adopt its identity before rendering so a
        # failed live restore and subsequent Retry recover that same scenario.
        # Reuse the already validated snapshot; no post-commit catalog read is
        # needed to decide which data and algorithm were opened.
        self._activate_scenario(row, baseline)
        self.window._algorithm_version = metadata.get('algorithm_version')
        self.window._restore_session_if_exists(confirm=False)
        if self.window._restore_failed:
            raise ValueError(self.window._save_error)
        self.accept()

    def compare(self):
        a, b = self.selected()
        result = compare_scenarios(self.catalog.read(a['id']), self.catalog.read(b['id']))
        ComparisonDialog(self, a, b, result).exec()


class ComparisonDialog(_ScrollableProjectDialog):
    def __init__(self, parent, a, b, result):
        super().__init__(parent)
        self.setWindowTitle(msg('Comparar escenarios'))
        self.resize(800, 580)
        outer, layout = self.outer, self.body
        warning = _readable_label(msg('Indicadores descriptivos, sin ganador ni puntuación global.'))
        layout.addWidget(warning)
        if not result['comparable']:
            warning2 = _readable_label(msg('No son directamente comparables: cambian entradas, reglas o versiones, o la versión del algoritmo es desconocida.'))
            layout.addWidget(warning2)
        labels = dict(courses='Cursos', classrooms='Aulas', restrictions='Restricciones', resources='Recursos', pins='Sesiones fijas',
                      seed='Semilla', calendar='Calendario', algorithm_version='Versión del algoritmo', metrics_version='Versión de métricas', format_version='Versión del formato')
        differences = _readable_label(msg('Diferencias: {details}', details=join_messages(', ', [msg(labels[key]) for key in result['differences']]) or msg('Ninguna')))
        layout.addWidget(differences)
        if result['difference_values']:
            import json
            detail = QPlainTextEdit()
            detail.setReadOnly(True)
            detail.setTabChangesFocus(True)
            detail.setAccessibleName(msg('Valores diferentes (izquierda / derecha)'))
            detail.setMinimumHeight(100)
            detail.setMaximumHeight(150)
            self._difference_detail = detail
            self._difference_labels = labels
            self._difference_values = result['difference_values']
            detail.setPlainText('\n\n'.join(str(msg(labels[key])) + '\n' +
                json.dumps(values, ensure_ascii=False, sort_keys=True, default=lambda value: sorted(value))
                for key, values in result['difference_values'].items()))
            layout.addWidget(detail)
        table = QTableWidget(0, 3)
        self.table = table
        table.setAccessibleName(msg('Comparar escenarios'))
        table.setMinimumHeight(200)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._headers = [QTableWidgetItem(text) for text in (msg('Indicador'), a['name'], b['name'])]
        for index, item in enumerate(self._headers):
            table.setHorizontalHeaderItem(index, item)
        self._metric_items = []
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(table, 1)
        if result['left'] is None:
            warning.setText(msg('El formato, las métricas o el calendario guardados no son compatibles. No se recalcularon indicadores con reglas diferentes.'))
        else:
            metrics = [
                ('Sesiones asignadas / total', lambda q: f"{q['coverage']['assigned_sessions']} / {q['coverage']['sessions']}"),
                ('Sesiones pendientes', lambda q: q['coverage']['pending_sessions']),
                ('Preferencia de día: satisfechas / evaluadas', lambda q: f"{q['preferences']['day']['satisfied']} / {q['preferences']['day']['evaluated']}"),
                ('Preferencia de hora: satisfechas / evaluadas', lambda q: f"{q['preferences']['time']['satisfied']} / {q['preferences']['time']['evaluated']}"),
                ('Preferencia de aula: satisfechas / evaluadas', lambda q: f"{q['preferences']['room']['satisfied']} / {q['preferences']['room']['evaluated']}"),
                ('Ocupación: minutos-aula / disponibles', lambda q: f"{q['occupancy']['occupied_minutes']} / {q['occupancy']['available_minutes']}"),
                ('Excepciones activas', lambda q: len(q['manual_exceptions']['active_ids'])),
            ]
            for key, label in (('day', 'Día: preferencias pendientes / desconocidas'),
                               ('time', 'Hora: preferencias pendientes / desconocidas'),
                               ('room', 'Aula: preferencias pendientes / desconocidas')):
                metrics.append((label, lambda q, k=key: f"{q['preferences'][k]['pending']} / {q['preferences'][k]['unknown']}"))
            # Day indices are local to each calendar: day 1 may be Monday in
            # one scenario and Tuesday in the other. Align the union by weekday
            # identity and distinguish an absent teaching day from zero load.
            teaching_days = {row['name'] for side in ('left', 'right')
                             for row in result[side]['day_load']}
            for day in DAYS:
                if day in teaching_days:
                    metrics.append((msg('Docencia, día {day} (min)', day=msg(day)),
                                    lambda q, d=day: next((x['teaching_minutes'] for x in q['day_load']
                                                          if x['name'] == d), msg('No lectivo'))))
            table.setRowCount(len(metrics))
            for index, (label, read) in enumerate(metrics):
                item = QTableWidgetItem(label if isinstance(label, Message) else msg(label))
                self._metric_items.append(item)
                table.setItem(index, 0, item)
                for column, side in enumerate(('left', 'right'), 1):
                    value = read(result[side])
                    if index in (0, 2, 3, 4, 5) and str(value) == '0 / 0':
                        value = msg('No aplica')
                    table.setItem(index, column, QTableWidgetItem(value if isinstance(value, Message) else str(value)))
        close = ResponsiveDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        outer.addWidget(close)
        self._finish_buttons(close)
        language_manager().changed.connect(self._refresh_detail)
        warning.setFocus()

    def _refresh_detail(self, *_):
        self._headers[0].setText(msg('Indicador'))
        if hasattr(self, '_difference_detail'):
            import json
            self._difference_detail.setPlainText('\n\n'.join(
                str(msg(self._difference_labels[key])) + '\n' +
                json.dumps(values, ensure_ascii=False, sort_keys=True, default=lambda value: sorted(value))
                for key, values in self._difference_values.items()))
