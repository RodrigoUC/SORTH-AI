"""Named snapshot workflows. Existing single-session autosave stays unchanged."""
import sqlite3
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QAbstractItemView, QHeaderView, QPlainTextEdit
from .i18n_widgets import (QDialog, QLabel, QPushButton, QDialogButtonBox, QLineEdit,
                           QTableWidget, QTableWidgetItem, QMessageBox)
from .i18n import msg, join_messages, language_manager, Message
from ..infrastructure.project_repository import ProjectRepository
from ..infrastructure.session_repository import SessionRepository
from ..application.scenario_comparison import scenario_metadata, compare_scenarios, session_fingerprint, validate_scenario_metadata
from ..scheduling.validation import validate_schedule
from ..scheduling.time_model import TimeModel
from ..scheduling.project_calendar import ProjectCalendar, DAYS
from copy import deepcopy


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


class ProjectDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle(msg('Proyectos y escenarios'))
        self.resize(850, 540)
        self.catalog = ProjectRepository(Path(window._repo._db_path).with_name('sorth_projects.db'))
        persisted = window._repo.load_session()
        self.catalog.preserve_legacy(window._repo, scenario_metadata(calendar=(persisted or {}).get('calendar', ProjectCalendar())))
        layout = QVBoxLayout(self)
        hint = QLabel(msg('Cada escenario es una copia independiente. Guardar como nunca sobrescribe. Selecciona dos filas para comparar.'))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QTableWidget(0, 3)
        self._headers = [QTableWidgetItem(msg(text)) for text in ('Proyecto', 'Escenario', 'Guardado (UTC)')]
        for index, item in enumerate(self._headers):
            self.table.setHorizontalHeaderItem(index, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAccessibleName(msg('Escenarios guardados'))
        layout.addWidget(self.table)
        row = QHBoxLayout()
        layout.addLayout(row)
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
            button = QPushButton(msg(title))
            button.clicked.connect(lambda checked=False, action=handler: self._run(action))
            row.addWidget(button)
            self.buttons[key] = button
        self.feedback = QLabel()
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.refresh()
        language_manager().changed.connect(self._translate_headers)

    def _translate_headers(self, *_):
        for item, label in zip(self._headers, ('Proyecto', 'Escenario', 'Guardado (UTC)')):
            item.setText(msg(label))

    def _run(self, action):
        try:
            action()
        except sqlite3.IntegrityError:
            self.feedback.setText(msg('Ese nombre ya existe. Usa otro nombre; no se reemplazó ningún escenario.'))
        except Exception as error:
            self.feedback.setText(msg('No se pudo completar la operación. El escenario guardado se conserva. {detail}', detail=str(error)))

    def selected(self):
        return [self.rows[index.row()] for index in self.table.selectionModel().selectedRows()]

    def _selection_changed(self):
        count = len(self.selected())
        for key in ('save', 'open', 'duplicate', 'rename'):
            self.buttons[key].setEnabled(count == 1)
        self.buttons['compare'].setEnabled(count == 2)

    def refresh(self):
        self.rows = self.catalog.list_scenarios()
        self.table.setRowCount(len(self.rows))
        for index, row in enumerate(self.rows):
            for column, key in enumerate(('project_name', 'name', 'created_at')):
                self.table.setItem(index, column, QTableWidgetItem(row[key]))
        self._selection_changed()

    def _save_working(self):
        if not self.window._save_session():
            raise OSError(self.window._save_error or 'Working session could not be saved')

    def _saved(self, scenario_id):
        self.refresh()
        row = next(row for row in self.rows if row['id'] == scenario_id)
        self.window._scenario_id = scenario_id
        self.window._scenario_name = row['project_name'] + ' / ' + row['name']
        self.window._scenario_baseline = session_fingerprint(self.catalog.read(scenario_id)[0])
        self.window._scenario_dirty = False
        self.window._scenario_comparison_error = None
        self.window._update_save_state()
        self.feedback.setText(msg('Escenario guardado. Las ediciones posteriores no cambian esta copia.'))

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
        if QMessageBox.question(self, msg('Abrir escenario'),
                msg('Se guardará una copia de recuperación de la sesión actual antes de abrir {name}. ¿Continuar?', name=row['name']),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self._save_working()
        self.window._repo.backup_session()
        self.window._repo.save_session(**data)
        self.window._restore_session_if_exists(confirm=False)
        if self.window._restore_failed:
            raise ValueError(self.window._save_error)
        self.window._algorithm_version = metadata.get('algorithm_version')
        self._saved(row['id'])
        self.accept()

    def compare(self):
        a, b = self.selected()
        result = compare_scenarios(self.catalog.read(a['id']), self.catalog.read(b['id']))
        ComparisonDialog(self, a, b, result).exec()


class ComparisonDialog(QDialog):
    def __init__(self, parent, a, b, result):
        super().__init__(parent)
        self.setWindowTitle(msg('Comparar escenarios'))
        self.resize(800, 580)
        layout = QVBoxLayout(self)
        warning = QLabel(msg('Indicadores descriptivos, sin ganador ni puntuación global.'))
        warning.setWordWrap(True)
        layout.addWidget(warning)
        if not result['comparable']:
            warning2 = QLabel(msg('No son directamente comparables: cambian entradas, reglas o versiones, o la versión del algoritmo es desconocida.'))
            warning2.setWordWrap(True)
            layout.addWidget(warning2)
        labels = dict(courses='Cursos', classrooms='Aulas', restrictions='Restricciones', resources='Recursos', pins='Sesiones fijas',
                      seed='Semilla', calendar='Calendario', algorithm_version='Versión del algoritmo', metrics_version='Versión de métricas', format_version='Versión del formato')
        differences = QLabel(msg('Diferencias: {details}', details=join_messages(', ', [msg(labels[key]) for key in result['differences']]) or msg('Ninguna')))
        differences.setWordWrap(True)
        layout.addWidget(differences)
        if result['difference_values']:
            import json
            detail = QPlainTextEdit()
            detail.setReadOnly(True)
            detail.setAccessibleName(msg('Valores diferentes (izquierda / derecha)'))
            detail.setMaximumHeight(150)
            self._difference_detail = detail
            self._difference_labels = labels
            self._difference_values = result['difference_values']
            detail.setPlainText('\n\n'.join(str(msg(labels[key])) + '\n' +
                json.dumps(values, ensure_ascii=False, sort_keys=True, default=lambda value: sorted(value))
                for key, values in result['difference_values'].items()))
            layout.addWidget(detail)
        table = QTableWidget(0, 3)
        table.setAccessibleName(msg('Comparar escenarios'))
        self._headers = [QTableWidgetItem(text) for text in (msg('Indicador'), a['name'], b['name'])]
        for index, item in enumerate(self._headers):
            table.setHorizontalHeaderItem(index, item)
        self._metric_items = []
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(table)
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
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        language_manager().changed.connect(self._refresh_detail)

    def _refresh_detail(self, *_):
        self._headers[0].setText(msg('Indicador'))
        if hasattr(self, '_difference_detail'):
            import json
            self._difference_detail.setPlainText('\n\n'.join(
                str(msg(self._difference_labels[key])) + '\n' +
                json.dumps(values, ensure_ascii=False, sort_keys=True, default=lambda value: sorted(value))
                for key, values in self._difference_values.items()))
