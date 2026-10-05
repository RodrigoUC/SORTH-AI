# src/gui/main_window.py

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFileDialog, QFrame, QPlainTextEdit, QMenu
)
from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtGui import (
    QIcon
)

from .course_manager_widget import CourseManagerWidget
from .schedule_viewer_widget import ScheduleViewerWidget
from ..infrastructure.excel_reader import ExcelReader, ExcelImportError
from ..infrastructure.schedule_exporter import ScheduleExporter
from ..infrastructure.session_repository import SessionRepository
from ..scheduling.time_model import TimeModel
from ..scheduling.classroom import Classroom

from .dialogs import ClassroomRestrictionsDialog, AddClassroomDialog, _InfoDialog
from .scheduler_worker import SchedulerWorker
from .import_controller import ImportController
from .theme import apply_theme, theme_manager
from .motion import MotionController, update_busy_indicator
from .features import FeaturePreferences
from .edit_view_state import EditViewState
from .manual_assignment_dialog import ManualAssignmentDialog
from dataclasses import replace
from ..scheduling.teaching_resources import SchedulingResources, RESOURCE_KINDS
from ..scheduling.validation import validate_schedule, unassigned_reason
from copy import deepcopy
from ..application.schedule_result import matches_requested_groups
from ..application.edit_history import EditHistory, EditError, course_change, normalized_group_feedback

from .i18n import msg, plural, language_manager, join_messages
from .locales import LANGUAGES
from .i18n_widgets import (
    QAction, QProgressBar, QComboBox, QCheckBox, QDialog, QDialogButtonBox, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSpinBox, QStatusBar, QTabWidget, QWidget
)


from ..scheduling.project_calendar import ProjectCalendar


class MainWindow(QMainWindow):
    # Content visibility is independent from the whitespace budget. Keep these
    # transitions deterministic while reserving room for native font metrics,
    # focused frames and four normal-height consultation rows.
    _COMPACT_HEIGHT = 802
    _COMPACT_HINT_HEIGHT = 760
    # These decisions never depend on the current viewport, avoiding
    # compact/spacious feedback or resize oscillation.
    _DENSE_HEIGHT = 920

    def __init__(self, repo=None, restore_session=True, feature_settings=None):
        super().__init__()
        self._history = EditHistory()
        self._busy = False
        self._loading = False
        self._worker = None
        self._generation_cancelled = False
        self._generation_result_committed = False
        self._close_after_generation = False
        self.excel_path: str | None = None
        self.current_schedule: dict | None = None
        self.current_groups: list | None = None
        self.calendar = ProjectCalendar()
        self.pinned_group_ids: set[str] = set()
        self.resources = SchedulingResources()
        self.classroom_restrictions: dict[str, set[str]] = {}
        self._classroom_course_map: dict[str, list[str]] = {}
        self._classrooms: dict[str, Classroom] = {}
        self._unsaved = False
        self._scenario_id = None
        self._scenario_name = None
        self._scenario_dirty = False
        self._scenario_baseline = None
        self._scenario_comparison_error = None
        self._algorithm_version = None
        self._save_error = None
        self._restore_failed = False
        self._preserve_previous = False
        self._repo = repo
        if self._repo is None:
            try:
                self._repo = SessionRepository()
            except Exception as error:
                self._save_error = str(error)
                self._restore_failed = True

        self._features = FeaturePreferences(feature_settings)
        # Resource activation belongs exclusively to the accepted SQLite
        # session. Cached UI preference flags never activate a fresh project.
        self._motion = MotionController(self)
        self._init_ui()
        self._import = ImportController(self)
        self._update_save_state()
        if self._restore_failed:
            self._record_save_error(self._save_error)
            self._block_for_recovery()
        if restore_session and self._repo is not None:
            self._restore_session_if_exists()
        self._apply_feature_preferences()
        self.chk_random_seed.toggled.connect(self._save_session)
        self.seed_input.valueChanged.connect(self._save_session)

    def _refresh_theme_recovery_notice(self, _theme=None):
        notice = self._theme_recovery_notice
        manager = theme_manager()
        if manager.startup_issue:
            notice.setText(msg('No se pudo preparar la apariencia guardada. Se muestra Original claro sin cambiar el archivo guardado. Abra Configuración → Apariencia para intentarlo de nuevo.'))
        else:
            notice.setText(msg('No se pudo leer la apariencia guardada. Se muestra Original claro y el archivo original se conserva. Abra Configuración → Apariencia para revisarlo o recuperarlo.'))
        notice.setVisible(bool(manager.recovery_issue or manager.startup_issue))

    def _init_ui(self):
        self.setWindowTitle(msg('SORTH - Sistema de Organización de Horarios'))
        self._set_window_icon()
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(960, 640)
        apply_theme(self)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = self._main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 20, 24, 12)
        main_layout.setSpacing(8)

        self._workspace_chrome = QWidget()
        chrome_layout = QVBoxLayout(self._workspace_chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)
        chrome_layout.setSpacing(0)
        # Keep child visibility independent: asynchronous status/theme updates
        # must never uncover the shell while the schedule is expanded.
        main_layout.addWidget(self._workspace_chrome)
        chrome_layout.addLayout(self._create_file_section())
        self._feature_notice = QLabel()
        self._feature_notice.setWordWrap(True)
        self._feature_notice.setAccessibleName(msg('Datos de funciones desactivadas'))
        chrome_layout.addWidget(self._feature_notice)
        self._theme_recovery_notice = QLabel()
        self._theme_recovery_notice.setObjectName('themeRecoveryNotice')
        self._theme_recovery_notice.setWordWrap(True)
        chrome_layout.addWidget(self._theme_recovery_notice)
        theme_manager().changed.connect(self._refresh_theme_recovery_notice)
        self._refresh_theme_recovery_notice()
        from .resource_dialog import RESOURCE_TITLES
        resource_actions = QHBoxLayout()
        self.resource_buttons = {}
        for kind in RESOURCE_KINDS:
            button = QPushButton(msg(RESOURCE_TITLES[kind]))
            button.clicked.connect(lambda _checked=False, key=kind: self._edit_resources(key))
            resource_actions.addWidget(button)
            self.resource_buttons[kind] = button
        resource_actions.addStretch()
        chrome_layout.addLayout(resource_actions)
        self._compact_tools = QWidget()
        compact_row = QHBoxLayout(self._compact_tools)
        compact_row.setContentsMargins(0, 0, 0, 0)
        self._compact_summary = QLabel()
        compact_row.addWidget(self._compact_summary, 1)
        self._compact_tools_button = QPushButton(msg('Herramientas del horario (F7)'))
        self._compact_tools_button.setAccessibleName(msg('Herramientas del horario (F7)'))
        compact_row.addWidget(self._compact_tools_button)
        compact_menu = QMenu(self._compact_tools_button)
        self._compact_tools_button.setMenu(compact_menu)
        self._compact_resource_actions = {}
        for kind in RESOURCE_KINDS:
            action = QAction(msg(RESOURCE_TITLES[kind]), self)
            action.triggered.connect(lambda _checked=False, key=kind: self._edit_resources(key))
            compact_menu.addAction(action)
            self._compact_resource_actions[kind] = action
        compact_menu.addSeparator()
        self._compact_summary_action = QAction(msg('Ver resumen'), self)
        self._compact_summary_action.triggered.connect(lambda: self.schedule_viewer._show_summary())
        compact_menu.addAction(self._compact_summary_action)
        self._compact_clear_action = QAction(msg('Limpiar horario'), self)
        self._compact_clear_action.triggered.connect(lambda: self.schedule_viewer._clear_schedule())
        compact_menu.addAction(self._compact_clear_action)
        detail_action = QAction(msg('Leer estado (F6)'), self)
        detail_action.triggered.connect(self._show_accessible_status)
        compact_menu.addAction(detail_action)
        compact_menu.aboutToShow.connect(self._update_compact_overview)
        shortcut = QAction(self)
        shortcut.setShortcut('F7')
        shortcut.triggered.connect(lambda: self._compact_tools_button.showMenu() if self._compact_tools.isVisible() else None)
        self.addAction(shortcut)
        self._compact_tools.hide()
        chrome_layout.addWidget(self._compact_tools)

        self.tabs = QTabWidget()
        self.course_manager = CourseManagerWidget(repo=self._repo, calendar_provider=lambda: self.calendar)
        self.tabs.addTab(self.course_manager, msg('📚 Gestión de Cursos'))
        self.tabs.setTabToolTip(0, msg('Ver, agregar, editar y eliminar los cursos a programar'))
        self.course_manager.courses_changed.connect(self._on_inputs_changed)
        self.course_manager.commit_handler = self._commit_course_edit
        self.course_manager.change_guard = self._confirm_course_inputs
        self.schedule_viewer = ScheduleViewerWidget()
        self.tabs.addTab(self.schedule_viewer, msg('📅 Horario Generado'))
        self.tabs.setTabToolTip(1, msg('Visualizar el horario generado en lista, cuadrícula o por aula'))
        self.schedule_viewer.edit_course_requested.connect(self._edit_course_from_viewer)
        self.schedule_viewer.group_removed.connect(self._on_group_removed)
        self.schedule_viewer.remove_handler = self._on_group_removed
        self.schedule_viewer.clear_handler = self._on_schedule_cleared
        self.schedule_viewer.pin_requested.connect(self._toggle_pin)
        self.schedule_viewer.schedule_cleared.connect(self._on_schedule_cleared)
        main_layout.addWidget(self.tabs, 1)
        self.tabs.currentChanged.connect(self._on_main_view_changed)
        self.schedule_viewer.tabs.currentChanged.connect(
            lambda _index: self._motion.reveal(self.schedule_viewer.tabs.currentWidget()))

        self._workspace_actions = QWidget()
        self._workspace_actions.setLayout(self._create_actions_section())
        self._workspace_actions.layout().setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._workspace_actions)
        self.schedule_viewer.expanded_changed.connect(self._set_schedule_expanded)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self._progress = QProgressBar()
        self._progress.setAccessibleName(msg('Progreso de generación'))
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setFixedWidth(160)
        self._progress.setFixedHeight(16)
        self._progress.setVisible(False)
        self.status_bar.addPermanentWidget(self._progress)
        self._cancel_button = QPushButton(msg('Cancelar generación'))
        self._cancel_button.clicked.connect(self._cancel_generation)
        self._cancel_button.setVisible(False)
        self.status_bar.addPermanentWidget(self._cancel_button)

        self._cancel_import_button = QPushButton(msg('Cancelar importación'))
        self._cancel_import_button.setAccessibleName(msg('Cancelar importación'))
        self._cancel_import_button.clicked.connect(lambda: self._import.cancel())
        self._cancel_import_button.setVisible(False)
        self.status_bar.addPermanentWidget(self._cancel_import_button)

        self.chk_reduce_motion = QCheckBox(msg('Reducir animaciones'))
        self.chk_reduce_motion.setToolTip(msg('Desactiva las transiciones y el indicador animado.'))
        self.chk_reduce_motion.setChecked(self._motion.reduced)
        self.chk_reduce_motion.toggled.connect(self._set_reduced_motion)
        self.status_bar.addPermanentWidget(self.chk_reduce_motion)
        update_busy_indicator(self._progress, False, self._motion.reduced)

        self._save_state_label = QLabel()
        self._save_state_label.setMaximumWidth(360)
        self._save_state_label.setAccessibleName(msg('Estado de guardado'))
        self._retry_save_button = QPushButton(msg('Reintentar'))
        self._retry_save_button.clicked.connect(self._retry_session)
        self.status_bar.addPermanentWidget(self._save_state_label)
        self.status_bar.addPermanentWidget(self._retry_save_button)
        self.btn_projects = QPushButton(msg('Proyectos y escenarios'))
        self.btn_projects.clicked.connect(self._show_projects)
        self.status_bar.addPermanentWidget(self.btn_projects)
        self._undo_action = QAction(msg('Deshacer'), self)
        self._undo_action.setShortcut('Ctrl+Z')
        self._undo_action.triggered.connect(lambda: self._travel_history(True))
        self.addAction(self._undo_action)
        self._redo_action = QAction(msg('Rehacer'), self)
        self._redo_action.setShortcuts(['Ctrl+Shift+Z', 'Ctrl+Y'])
        self._redo_action.triggered.connect(lambda: self._travel_history(False))
        self.addAction(self._redo_action)
        self.btn_undo = QPushButton(msg('Deshacer'))
        self.btn_undo.setToolTip(msg('Deshacer el último cambio (Ctrl+Z). Historial de esta sesión: máximo 50 cambios o 16 MiB.'))
        self.btn_undo.clicked.connect(lambda: self._travel_history(True))
        self.btn_redo = QPushButton(msg('Rehacer'))
        self.btn_redo.setToolTip(msg('Rehacer el último cambio (Ctrl+Shift+Z).'))
        self.btn_redo.clicked.connect(lambda: self._travel_history(False))
        self.course_manager.edit_actions.insertWidget(3, self.btn_undo)
        self.course_manager.edit_actions.insertWidget(4, self.btn_redo)
        self.btn_bulk = QPushButton(msg('Editar en lote'))
        self.btn_bulk.clicked.connect(self._show_bulk_edit)
        self.course_manager.edit_actions.insertWidget(5, self.btn_bulk)
        self.course_manager.table.itemSelectionChanged.connect(self._update_history_actions)
        # Filtering can hide selected rows without changing native selection.
        self.course_manager._search.textChanged.connect(self._update_history_actions)
        self.status_bar.showMessage(msg('Listo. Cargue un archivo Excel para comenzar.'))
        self._status_action = QAction(msg('Leer estado (F6)'), self)
        self._status_action.setShortcut('F6')
        self._status_action.triggered.connect(self._show_accessible_status)
        self.addAction(self._status_action)
        self._status_button = QPushButton(msg('Leer estado (F6)'))
        self._status_button.clicked.connect(self._show_accessible_status)
        self.status_bar.addPermanentWidget(self._status_button)

    # ------------------------------------------------------------------
    # UI builders
    # ------------------------------------------------------------------

    def _bind_command_shortcut(self, button, sequence):
        # Native button captions own their mnemonic: replacing the text also
        # replaces QPushButton's shortcut. Keep explicit application commands
        # on a separate action so locale/busy labels cannot erase them. The
        # associated button still gates the action by visibility and enabled
        # state, and the default WindowShortcut excludes child modal dialogs.
        action = QAction(button)
        action.setShortcut(sequence)
        action.triggered.connect(button.click)
        button.addAction(action)

    def _show_accessible_status(self):
        """On-demand, focusable status; no unsupported screen-reader promises."""
        dialog = QDialog(self)
        dialog.setWindowTitle(msg('Estado actual'))
        dialog.resize(620, 420)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setAccessibleName(msg('Estado actual'))
        text.setPlainText(join_messages('\n\n', filter(None, (
            self.status_bar.currentMessage(),
            msg('Archivo de la sesión: {filename}', filename=Path(self.excel_path).name) if self.excel_path else None,
            self._save_state_label.text(),
            self.overview_label.text(), self.schedule_viewer._summary_label.text(),
            self.schedule_viewer._result_label.text(), self._feature_notice.text(), self._feature_notice.toolTip(),
            self._theme_recovery_notice.text() if (theme_manager().recovery_issue or theme_manager().startup_issue) else '',
            self._save_error, self._scenario_comparison_error))).render())
        layout.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        text.setFocus()
        dialog.exec()

    def _create_file_section(self) -> QVBoxLayout:
        layout = self._file_layout = QVBoxLayout()

        header = QFrame()
        header.setObjectName("brandHeader")
        heading = QHBoxLayout(header)
        heading.setContentsMargins(16, 6, 16, 6)
        title = QLabel("SORTH")
        title.setObjectName("appTitle")
        heading.addWidget(title)
        subtitle = QLabel(msg('Organización de horarios académicos'))
        subtitle.setObjectName("subtitle")
        heading.addWidget(subtitle)
        heading.addStretch()
        self.language_selector = QComboBox()
        for language in LANGUAGES.values():
            self.language_selector.addItem(language.native_name, language.code)
        self.language_selector.setCurrentIndex(
            self.language_selector.findData(language_manager().language))
        self.language_selector.setAccessibleName(msg('Idioma de la interfaz'))
        self.language_selector.setToolTip(msg('Cambiar idioma sin modificar los datos ni los formatos de exportación'))
        self.language_selector.currentIndexChanged.connect(
            lambda: language_manager().set_language(self.language_selector.currentData()))
        language_manager().changed.connect(self._sync_language_selector)
        language_label = QLabel(msg('Idioma:'))
        language_label.setBuddy(self.language_selector)
        language_label.setObjectName("headerMutedText")
        heading.addWidget(language_label)
        heading.addWidget(self.language_selector)
        self.btn_settings = QPushButton(msg('Configuración'))
        self.btn_settings.setObjectName("headerAction")
        self.btn_settings.clicked.connect(self._show_settings)
        heading.addWidget(self.btn_settings)
        help_button = QPushButton(msg('Guía rápida'))
        help_button.setObjectName("headerAction")
        help_button.setCheckable(True)
        heading.addWidget(help_button)
        layout.addWidget(header)
        info = QLabel(
            msg('1. Cargue un Excel con las hojas Aulas y Cursos (nombres exactos).\n2. Revise los cursos y configure aulas o restricciones.\n3. Genere el horario, revise los grupos pendientes y exporte.')
        )
        info.setWordWrap(True)
        info.setObjectName("helpText")
        info.setVisible(False)
        help_button.toggled.connect(info.setVisible)
        layout.addWidget(info)
        self.overview_label = QLabel(msg('Cargue un Excel o agregue cursos y aulas para comenzar.'))
        self.overview_label.setObjectName("overview")
        self.overview_label.setWordWrap(True)
        layout.addWidget(self.overview_label)

        file_row = QHBoxLayout()
        lbl = QLabel(msg('Archivo Excel:'))
        lbl.setStyleSheet("font-weight: bold;")
        self.excel_path_label = QLabel(msg('Sin archivo seleccionado'))
        self.excel_path_label.setWordWrap(True)
        self.excel_path_label.setTextFormat(Qt.TextFormat.PlainText)

        btn_load = self.btn_load = QPushButton(msg('Cargar Excel'))
        self._bind_command_shortcut(btn_load, "Ctrl+O")
        btn_load.setToolTip(
            msg('Abrir un archivo Excel (.xlsx) con las hojas:\n  • Aulas: # DE AULA y CAPACIDAD (entero ≥ 0)\n  • Cursos: Curso; cada fila es un grupo sugerido\nOpcionales: Nombre de Curso, Horas (0800-1055), Aula y Días (L,I,M,J,V,S).\nLos encabezados van en la fila 1; el orden de columnas no importa.')
        )
        btn_load.clicked.connect(self._load_excel)

        self.btn_add_classroom = QPushButton(msg('Agregar aula'))
        self.btn_add_classroom.setToolTip(
            msg('Agregar un aula nueva a la sesión actual.\nÚtil para aulas que no están en el Excel pero deben estar disponibles.')
        )
        self.btn_add_classroom.clicked.connect(self._add_classroom)

        self.btn_restrictions = QPushButton(msg('Restricciones de aulas'))
        self.btn_restrictions.setToolTip(
            msg('Configurar qué aulas están reservadas exclusivamente para ciertos cursos.\nLos cursos restringidos SOLO pueden asignarse a su aula designada.')
        )
        self.btn_restrictions.clicked.connect(self._configure_restrictions)
        self.btn_restrictions.setEnabled(False)

        file_row.addWidget(lbl)
        file_row.addWidget(self.excel_path_label, 1)
        file_row.addWidget(btn_load)
        file_row.addWidget(self.btn_add_classroom)
        file_row.addWidget(self.btn_restrictions)
        layout.addLayout(file_row)

        # The accepted filename above belongs to the current session. Keep the
        # uncommitted candidate separate and inspectable without a hover target.
        self._import_candidate_row = QWidget()
        candidate_row = QHBoxLayout(self._import_candidate_row)
        candidate_row.setContentsMargins(0, 0, 0, 0)
        candidate_label = QLabel(msg('Archivo en importación:'))
        self._import_candidate_field = QLineEdit()
        self._import_candidate_field.setReadOnly(True)
        self._import_candidate_field.setAccessibleName(msg('Archivo en importación'))
        self._import_candidate_field.setAccessibleDescription(
            msg('Archivo pendiente de aceptar. La sesión actual se conserva. Lea el estado completo con F6.'))
        candidate_label.setBuddy(self._import_candidate_field)
        candidate_row.addWidget(candidate_label)
        candidate_row.addWidget(self._import_candidate_field, 1)
        self._import_candidate_row.hide()
        layout.addWidget(self._import_candidate_row)

        return layout

    def _sync_language_selector(self, language):
        self.language_selector.blockSignals(True)
        self.language_selector.setCurrentIndex(self.language_selector.findData(language))
        self.language_selector.blockSignals(False)

    def _create_actions_section(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        seed_label = QLabel(msg('Semilla:'))
        seed_label.setToolTip(
            msg('Desempata opciones con la misma prioridad.\nMismos datos y semilla fija → mismo horario.\nSemilla aleatoria → puede ofrecer alternativas, sin garantizar un horario distinto.')
        )

        self.chk_random_seed = QCheckBox(msg('Aleatoria'))
        self.chk_random_seed.setObjectName('randomSeed')
        self.chk_random_seed.setToolTip(msg('Activar para usar una semilla aleatoria en cada generación'))
        self.chk_random_seed.setChecked(False)

        self.seed_input = QSpinBox()
        self.seed_input.setAccessibleName(msg('Semilla fija'))
        seed_label.setBuddy(self.seed_input)
        self.seed_input.setRange(0, 999999)
        self.seed_input.setValue(42)
        self.seed_input.setPrefix(msg('Valor: '))
        self.seed_input.setToolTip(msg('Valor de semilla fija para resultados reproducibles'))
        self.chk_random_seed.toggled.connect(self.seed_input.setDisabled)

        self.btn_generate = QPushButton(msg('Generar horario'))
        self.btn_generate.setObjectName("primaryAction")
        self._bind_command_shortcut(self.btn_generate, "Ctrl+Return")
        self.btn_generate.setToolTip(
            msg('Ejecutar el algoritmo de programación con los cursos y aulas cargados.\nEl resultado se muestra en la pestaña Horario Generado.')
        )
        self.btn_generate.clicked.connect(self._generate_schedule)
        self.btn_generate.setEnabled(False)

        self.btn_export = QPushButton(msg('Exportar todas las asignaciones'))
        self._bind_command_shortcut(self.btn_export, "Ctrl+S")
        self.btn_export.setToolTip(
            msg('Guardar el horario generado en Excel (.xlsx), CSV o PDF.\nEl Excel incluye una grilla visual; el PDF, tablas por aula para imprimir.')
        )
        self.btn_export.clicked.connect(lambda: self._export_schedule())
        self.btn_export.setEnabled(False)
        self.btn_export_filtered = QPushButton(msg('Exportar filtrado (0)'))
        self.btn_export_filtered.setEnabled(False)
        self.btn_export_filtered.clicked.connect(lambda: self._export_schedule(filtered=True))
        self.schedule_viewer.filters_changed.connect(self._update_export_actions)
        self.schedule_viewer.manual_assignment_requested.connect(self._manual_assignment)
        self.schedule_viewer.placement_options_requested.connect(self._placement_options)

        layout.addStretch()
        layout.addWidget(seed_label)
        layout.addWidget(self.chk_random_seed)
        layout.addWidget(self.seed_input)
        layout.addWidget(self.btn_generate)
        layout.addWidget(self.btn_export)
        layout.addWidget(self.btn_export_filtered)

        return layout

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _load_excel(self):
        if (self._busy and not self._import.active) or self._import.closing:
            return
        if self._import.active:
            self._import.cancel()
        file_path, _ = QFileDialog.getOpenFileName(
            self, msg('Seleccionar archivo Excel'), "", msg('Libro de Excel (*.xlsx)'))
        if file_path:
            self._import.start(file_path)

    def _set_import_candidate(self, filename):
        self._import_candidate_field.setText(filename or '')
        self._import_candidate_field.setCursorPosition(0)
        self._import_candidate_row.setVisible(filename is not None)

    def _set_import_busy(self, busy):
        self._set_busy(busy)
        # Loading another file supersedes the current reader; editing stays locked.
        self.btn_load.setEnabled(True)
        self.btn_settings.setEnabled(not busy)
        self.btn_projects.setEnabled(not busy)
        self._retry_save_button.setEnabled(not busy)
        self._cancel_import_button.setVisible(busy)
        self.btn_generate.setText(msg('Generar horario'))
        self._progress.setAccessibleName(msg('Progreso de importación') if busy else msg('Progreso de generación'))
        if self._restore_failed:
            self._block_for_recovery()

    def _commit_import(self, candidate, retained_pins, resources=None):
        """Present and persist one accepted import, rolling both back on failure."""
        imported = candidate.imported
        resources = self.resources if resources is None else resources
        assignments = {gid: value for gid, value in (self.current_schedule or {}).items()
                       if gid in retained_pins} or None
        overrides = {g.group_id for g in (self.current_groups or []) if g.lab_override and g.group_id in retained_pins}
        # Preflight only the presentation the accepted import will materialize.
        # With no retained pins, _invalidate_schedule clears the schedule: building
        # a hidden table of every pending group would validate an unused view.
        # No dialogs, signals to the window, repository writes or event pumping.
        preview = CourseManagerWidget()
        preview_schedule = None
        try:
            preview.load_courses_from_excel(imported.courses)
            if retained_pins:
                preview_schedule = ScheduleViewerWidget()
                time_model = TimeModel.from_calendar(self.calendar)
                rooms = deepcopy(imported.classrooms)
                for room in rooms.values():
                    room.allowed_courses = None  # Import clears classroom restrictions.
                groups = [group for course in imported.courses for group in course.generate_groups()]
                for group in groups:
                    group.assignment = (assignments or {}).get(group.group_id)
                    group.pinned = group.group_id in retained_pins
                    group.lab_override = group.group_id in overrides
                    if not group.assignment:
                        group.unassigned_reason = unassigned_reason(group, rooms, time_model)
                preview_schedule.display_schedule(assignments or {}, time_model, groups,
                                                  classrooms=imported.classrooms)
        finally:
            preview.deleteLater()
            if preview_schedule is not None:
                preview_schedule.deleteLater()
        previous = {name: getattr(self, name) for name in (
            'pinned_group_ids', '_classroom_course_map', '_classrooms', 'excel_path',
            'classroom_restrictions', 'current_schedule', 'current_groups',
            '_preserve_previous', '_unsaved', '_save_error', '_scenario_dirty', 'resources')}
        previous_history = deepcopy(vars(self._history))
        previous_courses = self.course_manager.courses
        previous_label = self.excel_path_label.text()
        previous_view = EditViewState.capture(self)
        viewer = self.schedule_viewer
        if self._preserve_previous:
            self._repo.backup_session()
        seed = None if self.chk_random_seed.isChecked() else self.seed_input.value()

        def present():
            self.resources = resources
            self.pinned_group_ids = set(retained_pins)
            self._classroom_course_map = imported.classroom_course_map
            self._classrooms = imported.classrooms
            self.excel_path = candidate.path
            self.excel_path_label.setText(Path(candidate.path).name)
            if self.course_manager.load_courses_from_excel(imported.courses) is False:
                raise ValueError('The accepted import could not be presented')
            self.classroom_restrictions = {}
            self._invalidate_schedule()
            self._refresh_overview()
            self._preserve_previous = False
            self._unsaved = False
            self._save_error = None
            self._scenario_dirty = bool(self._scenario_name)
            self._update_save_state()
            self._update_feature_notice()
            self._reset_edit_history('import')
            self.status_bar.showMessage(msg('✅ Excel cargado: {p1}  ({p3} aulas, {p5} cursos)',
                                      p1=Path(candidate.path).name, p3=len(imported.classrooms), p5=len(imported.courses)))

        self._loading = True
        signal_guard = QSignalBlocker(self.course_manager)
        try:
            self._repo.save_session(excel_path=candidate.path, seed=seed,
                                   classrooms=imported.classrooms, courses=imported.courses,
                                   restrictions={}, assignments=assignments,
                                   pinned_group_ids=retained_pins, lab_overrides=overrides,
                                   resources=resources, calendar=self.calendar, before_commit=present)
        except Exception:
            # Restore the underlying state first, independently of rendering APIs.
            # In particular, don't call the failing import loader a second time.
            for name, value in previous.items():
                setattr(self, name, value)
            vars(self._history).clear()
            vars(self._history).update(previous_history)
            self.course_manager.courses = previous_courses
            try:
                self.course_manager._refresh_table()
                self.excel_path_label.setText(previous_label)
                if self.current_groups is None:
                    viewer._clear()
                else:
                    viewer.display_schedule(
                        self.current_schedule or {}, TimeModel.from_calendar(self.calendar), self.current_groups,
                        {c.code: c.name for c in previous_courses if c.name}, classrooms=self._classrooms)
                previous_view.restore(self)
                self._refresh_overview()
                self._update_save_state()
                self._update_history_actions()
            except Exception as recovery_error:
                # SQL and domain data remain original; a damaged view is explicitly
                # locked so it cannot overwrite the preserved session on disk.
                self._view_recovery_failure(recovery_error, committed=False)
            raise
        finally:
            signal_guard.unblock()
            self._loading = False

    def _add_classroom(self):
        dialog = AddClassroomDialog(self)
        if not dialog.exec():
            return
        classroom = dialog.get_classroom()
        if classroom.name in self._classrooms:
            QMessageBox.warning(self, msg('Duplicado'),
                                msg("El aula '{p1}' ya existe.", p1=classroom.name))
            return
        self._classrooms[classroom.name] = classroom
        self._invalidate_schedule()
        self._refresh_overview()
        self.btn_generate.setEnabled(bool(self.course_manager.get_courses()))
        self.status_bar.showMessage(
            msg("✅ Aula '{p1}' agregada ({p3}, cap={p5})", p1=classroom.name, p3=classroom.room_type, p5=classroom.capacity)
        )
        self._save_session()

    def _configure_restrictions(self):
        if not self._classroom_course_map:
            QMessageBox.information(self, msg('Info'),
                                    msg('No hay aulas con cursos asociados en el Excel.'))
            return

        dialog = ClassroomRestrictionsDialog(
            self, self._classroom_course_map,
            existing=self.classroom_restrictions or None
        )

        if dialog.exec():
            restrictions = dialog.get_restrictions()
            # Accepting unchanged selections is not an input edit. Preserve the
            # accepted schedule and history before invalidating any placements.
            if restrictions == (self.classroom_restrictions or {}):
                return
            if not self._confirm_pin_inputs(restrictions=restrictions):
                return
            self.classroom_restrictions = restrictions
            self._invalidate_schedule()
            count = len(self.classroom_restrictions)
            if count:
                self.btn_restrictions.setText(msg('🔒 Restricciones ({p1})', p1=count))
                self.status_bar.showMessage(
                    msg('✅ {p1} aula(s) con restricciones configuradas.', p1=count)
                )
            else:
                self.btn_restrictions.setText(msg('🔒 Aulas con Restricciones'))
                self.status_bar.showMessage(msg('Restricciones de aulas eliminadas.'))
            self._save_session()

    def _cancel_generation(self):
        if self._busy and self._worker is not None:
            self._generation_cancelled = True
            self._worker.requestInterruption()
            self._cancel_button.setEnabled(False)
            self._cancel_button.setText(msg('Cancelando…'))
            self.status_bar.showMessage(msg('Cancelando generación; se conservarán el horario y las sesiones fijadas.'))

    def _generate_schedule(self):
        if self._busy:
            return
        self._generation_cancelled = False
        self._generation_result_committed = False
        if not self._classrooms:
            QMessageBox.warning(self, msg('Advertencia'),
                                msg('Cargue un Excel o agregue al menos un aula primero.'))
            return

        courses = self.course_manager.get_courses()
        if not courses:
            QMessageBox.warning(self, msg('Advertencia'),
                                msg('Por favor agregue al menos un curso.'))
            return

        seed = None if self.chk_random_seed.isChecked() else self.seed_input.value()

        self._worker = SchedulerWorker(
            excel_path=self.excel_path,
            courses=courses,
            classrooms=self._classrooms or None,
            restrictions=self.classroom_restrictions,
            seed=seed,
            calendar=self.calendar,
            resources=self.resources,
            pinned_assignments=self._pinned_assignments(),
            lab_overrides={g.group_id for g in (self.current_groups or []) if g.lab_override and g.group_id in self.pinned_group_ids},
        )
        worker = self._worker
        worker.result_ready.connect(lambda assignments, groups: self._on_schedule_done(assignments, groups)
                                    if self._worker is worker else None)
        worker.finished.connect(lambda: self._generation_finished(worker))
        worker.error.connect(lambda message: self._on_schedule_error(message)
                             if self._worker is worker else None)
        worker.cancelled.connect(lambda: self.status_bar.showMessage(msg('Generación cancelada. Se conserva el horario anterior.'))
                                 if self._worker is worker else None)

        self._set_busy(True)
        self.status_bar.showMessage(msg('⏳ Generando horario...'))
        self._worker.start()

    def _generation_finished(self, worker):
        if self._worker is not worker:
            return
        # Retire worker ownership before any fallible presentation. A subsequent
        # close must never see a stale running thread, even if a widget fails.
        self._worker = None
        try:
            worker.deleteLater()
            self._set_busy(self._restore_failed)
            if self._restore_failed:
                self._progress.setVisible(False)
                self.btn_generate.setText(msg('Recuperación pendiente'))
            elif self._generation_cancelled:
                self.status_bar.showMessage(msg('Generación cancelada. Se conserva el horario anterior.'))
        except Exception as error:
            self._view_recovery_failure(error, committed=self._generation_result_committed)

        close_requested = self._close_after_generation
        self._close_after_generation = False
        if self._restore_failed:
            # Do not hide a new recovery notice through an earlier deferred
            # close request. An explicit later close remains available.
            self._import.closing = False
        elif close_requested:
            try:
                self.close()
            except Exception as error:
                self._import.closing = False
                self._view_recovery_failure(error, committed=self._generation_result_committed)

    def _on_schedule_done(self, assignments, groups):
        if self._generation_cancelled:
            return

        self._generation_result_committed = False
        if assignments is not None and groups is not None:
            # Worker copies and result metadata cannot redefine the requested
            # population, including pending groups and every split-session part.
            expected_groups = [g for c in self.course_manager.get_courses()
                               for g in c.generate_groups()]
            if (not isinstance(assignments, dict)
                    or not matches_requested_groups(groups, expected_groups)):
                self._on_schedule_error(msg('La generación cambió u omitió grupos solicitados. Se conserva el horario anterior.'))
                return
            errors = validate_schedule(assignments, groups, self._validation_classrooms(),
                                       TimeModel.from_calendar(self.calendar),
                                       {g.group_id for g in groups if g.lab_override}, resources=self.resources)
            if errors:
                self._on_schedule_error(join_messages('\n', (error.render(msg) for error in errors)))
                return
            if any(assignments.get(gid) != placement for gid, placement in self._pinned_assignments().items()):
                self._on_schedule_error(msg('La generación cambió sesiones fijadas. Se conserva el horario anterior.'))
                return
            candidate = self._capture_edit_state()
            candidate.update(assignments=deepcopy(assignments), schedule_present=True,
                lab_overrides={g.group_id for g in groups if g.lab_override},
                group_feedback={g.group_id: g.unassigned_reason for g in groups})
            try:
                # Generation is not an undo command, but must use the same
                # guarded SQLite/materialization boundary as accepted edits.
                self._persist_edit_state(candidate, result_groups=groups)
            except Exception as error:
                if not self._restore_failed:
                    try:
                        self._edit_failed(error)
                    except Exception as feedback_error:
                        self._view_recovery_failure(feedback_error, committed=False)
                return

            self._generation_result_committed = True
            from ..application.scenario_comparison import ALGORITHM_VERSION
            self._algorithm_version = ALGORITHM_VERSION
            try:
                # Invalidate commands before fingerprinting the committed result;
                # even a failed snapshot must not leave earlier commands usable.
                self._history.reset(reason='generation')
                self._history.observe(self._capture_edit_state())
                already_showing_results = self.tabs.currentIndex() == 1
                self.tabs.setCurrentIndex(1)
                if already_showing_results:
                    self._motion.reveal(self.schedule_viewer)
                self._update_history_actions()
                self._show_schedule_status()
            except Exception as error:
                self._committed_view_failure(error)

        else:
            self.status_bar.showMessage(msg('❌ No se pudo generar el horario'))
            dlg = _InfoDialog(
                self, msg('Sin resultado'),
                msg('No se obtuvo un resultado. Revise los datos y vuelva a generar el horario.'),
                warning=True
            )
            dlg.exec()

    def _show_schedule_status(self):
        total = len(self.current_groups or [])
        assigned = len(self.current_schedule or {})
        pending = total - assigned
        self.status_bar.showMessage(msg(
            '⚠️ Horario parcial: {p1}/{p3} grupos; {pending} pendientes' if pending
            else '✅ Horario generado: {p1}/{p3} grupos',
            p1=assigned, p3=total, pending=pending))

    def _on_schedule_error(self, message):
        if self._generation_cancelled:
            return
        self.status_bar.showMessage(msg('❌ Error al generar horario'))
        _InfoDialog(self, msg('Error'), msg('Error al generar el horario:\n{p1}', p1=message), warning=True).exec()

    def _update_export_actions(self):
        if not hasattr(self, "btn_export_filtered"):
            return
        count = len(self.schedule_viewer.filtered_assignments())
        ready = not self._busy and bool(self.current_schedule)
        self.btn_export.setEnabled(ready)
        self.btn_export_filtered.setText(msg('Exportar filtrado ({p1})', p1=count))
        self.btn_export_filtered.setEnabled(ready and count > 0)
        self.btn_export_filtered.setToolTip(
            msg('Exportar {p1} sesiones asignadas que coinciden con Buscar, Aula, Día y Estado.\nLa pestaña activa y el selector del aula de la cuadrícula no cambian este conjunto.', p1=count)
            + msg('\nEn Excel también se incluyen todas las sesiones pendientes del horario, aunque no coincidan con los filtros.')
        )

    def _export_schedule(self, filtered=False):
        if self._busy:
            return
        if not self.current_schedule:
            QMessageBox.warning(self, msg('Advertencia'), msg('No hay horario para exportar.'))
            return
        errors = validate_schedule(self.current_schedule or {}, self.current_groups or [],
                                   self._validation_classrooms(), TimeModel.from_calendar(self.calendar),
                                   {g.group_id for g in (self.current_groups or []) if g.lab_override}, resources=self.resources)
        if errors:
            QMessageBox.warning(self, msg('Horario no válido'), join_messages('\n', (error.render(msg) for error in errors)))
            return
        assignments = (self.schedule_viewer.filtered_assignments() if filtered
                       else dict(self.current_schedule))
        if not assignments:
            QMessageBox.information(self, msg('Sin coincidencias'),
                                    msg('No hay sesiones asignadas con estos filtros. Cambie o restablezca los filtros.'))
            return
        scope = msg('filtrado') if filtered else msg('todas las asignaciones')
        count = len(assignments)
        pending = len(self.current_groups or []) - len(self.current_schedule)
        if pending:
            scope = msg('{scope} · horario parcial, {pending} pendientes', scope=scope, pending=pending)
        file_path, selected_format = QFileDialog.getSaveFileName(
            self, msg('Guardar horario {p1} · {p3} sesiones', p1=scope, p3=count),
            "horario_filtrado.xlsx" if filtered else "horario.xlsx",
            msg('Archivos Excel (*.xlsx);;Archivos CSV (*.csv);;Documentos PDF (*.pdf)')
        )
        if not file_path:
            return
        try:
            if Path(file_path).suffix.lower() not in {".xlsx", ".csv", ".pdf"}:
                file_path += (".pdf" if "*.pdf" in selected_format else
                              ".csv" if "*.csv" in selected_format else ".xlsx")
                # The native picker approved its returned path, not this newly
                # resolved destination. Confirm only this extra collision; a
                # supported explicit suffix was already handled by the picker.
                destination = Path(file_path)
                if destination.exists() or destination.is_symlink():
                    confirmation = QMessageBox(self)
                    confirmation.setWindowTitle(msg('Confirmar reemplazo'))
                    confirmation.setIcon(QMessageBox.Icon.Question)
                    confirmation.setTextFormat(Qt.TextFormat.PlainText)
                    confirmation.setText(msg('El archivo ya existe:\n{path}\n\n¿Desea reemplazarlo?', path=file_path))
                    confirmation.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    confirmation.setDefaultButton(QMessageBox.StandardButton.No)
                    try:
                        if confirmation.exec() != QMessageBox.StandardButton.Yes:
                            return
                    finally:
                        confirmation.deleteLater()

            time_model = TimeModel.from_calendar(self.calendar)
            exporter = ScheduleExporter(time_model)
            courses = self.course_manager.get_courses()
            course_name_map = {c.code: c.name for c in courses if c.name}
            if file_path.lower().endswith(".pdf"):
                exporter.to_pdf(assignments, file_path, groups=self.current_groups,
                                course_name_by_code=course_name_map, filtered=filtered,
                                total_assigned=len(self.current_schedule), pending_count=pending,
                                filters=self.schedule_viewer.export_filter_description(),
                                labels=LANGUAGES[language_manager().language].messages)
            elif file_path.lower().endswith(".csv"):
                exporter.to_csv(assignments, file_path, groups=self.current_groups,
                                course_name_by_code=course_name_map)
            else:
                metadata = {}
                if pending or filtered:
                    rooms = self._validation_classrooms()
                    metadata = dict(
                        pending=[dict(group_id=group.group_id,
                                      reason=str(msg(group.unassigned_reason or
                                          unassigned_reason(group, rooms, time_model))))
                                 for group in self.current_groups or []
                                 if group.group_id not in self.current_schedule],
                        status="partial" if pending else "complete",
                        total_assigned=len(self.current_schedule), filtered=filtered,
                        filters=self.schedule_viewer.export_filter_description() if filtered else None)
                exporter.to_excel(assignments, file_path, groups=self.current_groups,
                                  course_name_by_code=course_name_map, include_grid=True,
                                  **metadata)
        except Exception as e:
            # Keep the latest attempt readable after its modal is dismissed.
            # Only expose the basename here; technical error details stay in
            # the existing error dialog rather than leaking into F6/status.
            self.status_bar.showMessage(msg(
                'No se pudo exportar a {filename}. El horario se conserva. Revise el destino y vuelva a intentarlo.',
                filename=Path(file_path).name))
            _InfoDialog(self, msg('Error'), msg('Error al exportar:\n{p1}', p1=e.render(msg) if isinstance(e, ExcelImportError) else str(e)), warning=True).exec()
        else:
            self.status_bar.showMessage(msg('Horario {p1}: {p3} sesiones exportadas a {p5}', p1=scope, p3=count, p5=Path(file_path).name))
            _InfoDialog(self, msg('Éxito'), msg('Horario {p1}: {p3} sesiones exportadas a:\n{p5}', p1=scope, p3=count, p5=file_path)).exec()

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def _show_settings(self):
        if self._busy or self._restore_failed:
            return
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        try:
            # done() keeps exec() alive until pending MCP cleanup has finished.
            dialog.exec()
        finally:
            # Closed settings own native controls and signal connections. Do not
            # leave their release to cyclic GC on a long-lived main window.
            dialog.deleteLater()

    def _show_calendar(self):
        if self._busy or self._restore_failed or not self._features.enabled('project_calendar'):
            return
        from .calendar_dialog import CalendarDialog
        CalendarDialog(self).exec()

    def _apply_calendar(self, calendar, preview, expected=None):
        if self._busy or self._restore_failed or set(preview.affected) & self.pinned_group_ids:
            return False
        candidate = self._capture_edit_state()
        candidate['calendar'] = calendar
        candidate['resources'] = preview.resources
        candidate['assignments'] = dict(preview.assignments)
        candidate['lab_overrides'].intersection_update(preview.assignments)
        for gid in preview.affected:
            candidate['group_feedback'].pop(gid, None)
        return self._commit_edit(candidate, 'Cambiar calendario', expected=expected)

    def _apply_feature_preferences(self):
        self.schedule_viewer.set_suggestion_controls_visible(self._features.enabled('placement_suggestions'))
        self.schedule_viewer.set_pin_controls_visible(self._features.enabled('pinned_sessions'))
        self.btn_projects.setVisible(self._features.enabled('project_scenarios'))
        for kind, button in self.resource_buttons.items():
            button.setVisible(self.resources.catalog(kind).enabled)
        self._update_history_actions()
        self._update_feature_notice()

    def _update_history_actions(self):
        enabled = self._features.enabled('undo_redo')
        for control in (self.btn_undo, self.btn_redo):
            control.setVisible(enabled)
        active = enabled and not self._busy and not self._restore_failed
        self._undo_action.setEnabled(active and self._history.can_undo)
        self._redo_action.setEnabled(active and self._history.can_redo)
        self.btn_undo.setEnabled(self._undo_action.isEnabled())
        self.btn_redo.setEnabled(self._redo_action.isEnabled())
        if hasattr(self, 'btn_bulk'):
            bulk = self._features.enabled('bulk_operations')
            self.btn_bulk.setVisible(bulk)
            self.btn_bulk.setEnabled(bulk and active and bool(self.course_manager.selected_course_codes()))
            self.btn_bulk.setToolTip(msg('Seleccione cursos y active Deshacer y rehacer en Configuración.'))
            table = self.course_manager.table
            table.setSelectionMode(table.SelectionMode.ExtendedSelection if bulk else table.SelectionMode.SingleSelection)

    def _show_bulk_edit(self):
        if (not self._features.enabled('bulk_operations') or not self._features.enabled('undo_redo')
                or self._busy or self._restore_failed):
            return
        from .bulk_course_dialog import BulkCourseDialog
        BulkCourseDialog(self).exec()

    def _capture_edit_state(self):
        return deepcopy(dict(
            calendar=self.calendar, resources=self.resources,
            excel_path=self.excel_path,
            seed=None if self.chk_random_seed.isChecked() else self.seed_input.value(),
            classrooms=self._classrooms, courses=self.course_manager.get_courses(),
            restrictions=self.classroom_restrictions, assignments=self.current_schedule,
            pinned_group_ids=self.pinned_group_ids,
            lab_overrides={g.group_id for g in (self.current_groups or []) if g.lab_override},
            schedule_present=self.current_groups is not None,
            group_feedback={g.group_id: g.unassigned_reason for g in (self.current_groups or [])},
            classroom_course_map=self._classroom_course_map,
        ))

    def _persist_edit_state(self, state, result_groups=None):
        if self._repo is None or self._restore_failed:
            raise OSError(msg('Sesión no disponible'))
        before = self._capture_edit_state()
        before_view = EditViewState.capture(self)
        courses, assignments, groups = (self.course_manager.courses,
                                        self.current_schedule, self.current_groups)
        group_values = [(group, deepcopy(vars(group))) for group in (groups or [])]
        model_references = {key: getattr(self, key) for key in (
            '_classrooms', 'classroom_restrictions', 'excel_path', '_classroom_course_map',
            'resources', 'calendar') if hasattr(self, key)}
        bookkeeping = {key: getattr(self, key) for key in (
            '_unsaved', '_save_error', '_scenario_dirty', '_preserve_previous', '_loading')}
        materialized = False

        def restore_references():
            self.course_manager.courses = courses
            self.current_schedule = assignments
            self.current_groups = groups
            self.pinned_group_ids = set(before['pinned_group_ids'])
            for key, value in model_references.items():
                setattr(self, key, value)
            for group, values in group_values:
                vars(group).clear()
                vars(group).update(deepcopy(values))
            for key, value in bookkeeping.items():
                setattr(self, key, value)

        def materialize():
            nonlocal materialized
            materialized = True
            # Synchronous, no dialogs/event loops. _loading suppresses autosaves.
            if result_groups is None:
                self._display_edit_state(state)
            else:
                self._display_edit_state(state, result_groups=result_groups)

        if self._preserve_previous or state['calendar'] != self.calendar:
            self._repo.backup_session()
        try:
            self._repo.save_session(**{key: state[key] for key in (
                'excel_path', 'seed', 'classrooms', 'courses', 'restrictions',
                'assignments', 'lab_overrides', 'pinned_group_ids', 'calendar', 'resources')}, before_commit=materialize)
        except Exception:
            if materialized:
                restore_references()
                try:
                    self._display_edit_state(before)
                    before_view.restore(self)
                except Exception as recovery_error:
                    # The database transaction has rolled back. Preserve model
                    # references and lock the UI when its renderer cannot recover.
                    restore_references()
                    self._view_recovery_failure(recovery_error, committed=False)
                else:
                    restore_references()
                    self._update_save_state()
                    self._update_history_actions()
            raise

    def _finish_edit_commit(self, message=None):
        # Commit and history acceptance are already durable. A presentation-only
        # failure here must never claim the previous edit was preserved.
        try:
            self._update_history_actions()
            self._update_feature_notice()
            if message is not None:
                self._edit_status(message)
        except Exception as error:
            self._committed_view_failure(error)
            return False
        return True

    def _committed_view_failure(self, error):
        self._view_recovery_failure(error, committed=True)

    def _view_recovery_failure(self, error, committed):
        self._restore_failed = True
        self._save_error = str(error)
        self._busy = True
        message = (msg('El cambio se guardó, pero no se pudo actualizar la vista. Reintente recuperar la sesión.')
                   if committed else msg('No se pudo restaurar la vista. Los datos se conservaron; reintente recuperar la sesión. {detail}',
                                         detail=str(error)))
        # Set the recovery guard before touching potentially failed widgets. Even
        # if another presentation setter fails, no exception escapes a Qt slot.
        updates = [lambda: self._save_state_label.setText(message),
                   lambda: self._retry_save_button.setVisible(True),
                   lambda: self.status_bar.showMessage(message),
                   lambda: self._progress.setVisible(False),
                   lambda: self._cancel_button.setVisible(False),
                   lambda: self.btn_generate.setText(msg('Recuperación pendiente'))]
        for control in (self.course_manager, self.schedule_viewer, self.btn_load,
                        self.btn_add_classroom, self.btn_generate, self.btn_restrictions,
                        self.chk_random_seed, self.seed_input, self._undo_action, self._redo_action):
            updates.append(lambda control=control: control.setEnabled(False))
        for update in updates:
            try:
                update()
            except Exception as secondary:
                self._save_error += '\n' + str(secondary)

    def _display_edit_state(self, state, result_groups=None):
        self._loading = True
        previous_calendar = self.calendar
        previous_groups = {g.group_id: g for g in (self.current_groups or [])}
        view = EditViewState.capture(self)
        try:
            self.calendar = state['calendar']
            self.resources = state['resources']
            self.course_manager.courses = state['courses']
            self.course_manager._refresh_table()
            self.current_schedule = state['assignments']
            self.pinned_group_ids = set(state['pinned_group_ids'])
            self.current_groups = None
            if state['schedule_present']:
                generated = (result_groups if result_groups is not None else
                             [g for c in state['courses'] for g in c.generate_groups()])
                feedback = normalized_group_feedback(state, generated)
                dynamic = {'assignment', 'pinned', 'lab_override', 'unassigned_reason', 'domain'}
                self.current_groups = []
                for group in generated:
                    previous = previous_groups.get(group.group_id) if result_groups is None else None
                    if previous is not None and all(getattr(previous, key, None) == value
                            for key, value in vars(group).items() if key not in dynamic):
                        # Preserve existing viewer references only after durable
                        # acceptance, when the underlying session identity matches.
                        group = previous
                    self.current_groups.append(group)
                for group in self.current_groups:
                    group.assignment = (self.current_schedule or {}).get(group.group_id)
                    group.pinned = group.group_id in self.pinned_group_ids
                    group.lab_override = group.group_id in state['lab_overrides']
                    group.unassigned_reason = feedback[group.group_id]
            self.schedule_viewer.display_schedule(self.current_schedule or {}, TimeModel.from_calendar(self.calendar),
                self.current_groups or [], classrooms=self._classrooms)
            if previous_calendar != self.calendar:
                name = TimeModel.from_calendar(previous_calendar).index_to_day.get(view.filters[1])
                view.filters = (view.filters[0], TimeModel.from_calendar(self.calendar).day_to_index.get(name), view.filters[2])
            view.restore(self)
            self._preserve_previous = False
            self._unsaved = False
            self._save_error = None
            if self._scenario_baseline is not None:
                from ..application.scenario_comparison import session_fingerprint
                self._scenario_dirty = session_fingerprint(state) != self._scenario_baseline
                self._scenario_comparison_error = None
            self.btn_generate.setEnabled(bool(self._classrooms and state['courses']) and not self._busy)
            self._refresh_overview()
            self._update_export_actions()
            self._update_save_state()
            self._update_history_actions()
            self._update_feature_notice()
        finally:
            self._loading = False

    def _edit_status(self, message):
        if self.current_groups is not None:
            self._show_schedule_status()
            message = join_messages(' ', (self.status_bar.currentMessage(), message))
        self.status_bar.showMessage(message)

    def _edit_failed(self, error):
        detail = error.render(msg) if isinstance(error, EditError) else str(error)
        QMessageBox.warning(self, msg('Cambio no aplicado'),
            msg('Se conservan los datos, el horario y el historial. {detail}', detail=detail))
        self._update_history_actions()

    def _commit_edit(self, candidate, label, expected=None):
        if self._busy or self._restore_failed:
            return False
        try:
            before = self._capture_edit_state()
            if expected is not None:
                from ..application.edit_history import fingerprint
                if fingerprint(before) != expected:
                    raise EditError('La sesión cambió desde la revisión. Vuelva a revisar el cambio.')
            # Record the feedback materialization will display, so derived
            # pending reasons cannot look like a later out-of-band edit.
            candidate = {**candidate, 'group_feedback': normalized_group_feedback(candidate)}
            accepted = self._history.execute(before, candidate, self._persist_edit_state,
                label, enabled=self._features.enabled('undo_redo'))
        except Exception as error:
            self._edit_failed(error)
            return False
        self._finish_edit_commit(msg('Cambio guardado.'))
        return True

    def _commit_course_edit(self, courses, label):
        before = self._capture_edit_state()
        known = {g.group_id for c in courses for g in c.generate_groups()}
        orphaned = {gid for c in before['resources'].catalogs for gid, _ in c.memberships if gid not in known}
        if orphaned:
            answer = QMessageBox.question(self, msg('Recursos por revisar'), msg(
                'Este cambio elimina {count} sesiones con relaciones de recursos guardadas. Se quitarán esas relaciones, pero se conservarán los recursos. ¿Continuar?', count=len(orphaned)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                return False
            before['resources'] = SchedulingResources(tuple(replace(c,
                memberships=tuple((gid, ids) for gid, ids in c.memberships if gid in known))
                for c in before['resources'].catalogs))
        try:
            candidate = course_change(before, courses)
        except EditError as error:
            if not before['pinned_group_ids']:
                self._edit_failed(error)
                return False
            answer = QMessageBox.warning(self, msg('Sesiones fijadas en conflicto'),
                msg('Este cambio invalida sesiones fijadas:\n{details}\n\n¿Desfijar todas las sesiones y aplicar el cambio? Cancelar conserva los datos y el horario.',
                    details=error.render(msg)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                return False
            # Clear only a private candidate; the accepted pin set survives a
            # cancelled dialog, invalid course, or failed database transaction.
            unpinned = deepcopy(before)
            unpinned['pinned_group_ids'] = set()
            try:
                candidate = course_change(unpinned, courses)
            except Exception as error:
                self._edit_failed(error)
                return False
        except Exception as error:
            # Candidate preparation may reject text that cannot be serialized.
            # Keep the failure inside the Qt action just like commit failures.
            self._edit_failed(error)
            return False
        return self._commit_edit(candidate, label)

    def _travel_history(self, undo):
        if not self._features.enabled('undo_redo') or self._busy or self._restore_failed:
            return False
        try:
            method = self._history.undo if undo else self._history.redo
            accepted = method(self._capture_edit_state(), self._persist_edit_state)
        except Exception as error:
            self._edit_failed(error)
            return False
        self._finish_edit_commit(msg('Cambio deshecho.') if undo else msg('Cambio rehecho.'))
        return True

    def _reset_edit_history(self, reason='session'):
        self._history.reset(self._capture_edit_state(), reason)
        self._update_history_actions()
        if self._features.enabled('undo_redo'):
            self.status_bar.showMessage(msg('Historial reiniciado al importar o restaurar una sesión.'))

    def _update_feature_notice(self):
        notices = []
        if self.calendar != ProjectCalendar():
            notices.append(msg('Calendario personalizado activo: se respeta aunque el editor esté oculto. Puedes revisarlo en Configuración.'))
        if self._features.load_error:
            notices.append(msg('No se pudo leer la configuración opcional. Abre Configuración para conservarla y recuperarla.'))
        from .resource_dialog import RESOURCE_TITLES
        resource_details = []
        resource_summaries = []
        for catalog in self.resources.catalogs:
            if catalog.resources or catalog.enabled:
                state = msg('Activo') if catalog.enabled else msg('Desactivado: datos conservados, sin restricciones')
                count = len({r for _g, ids in catalog.memberships for r in ids or ()})
                resource_details.append(msg('{name}: {state}. {count} recursos con sesiones asignadas.',
                    name=msg(RESOURCE_TITLES[catalog.kind]), state=state, count=count))
                resource_summaries.append(msg('{name}: {state} ({count})',
                    name=msg(RESOURCE_TITLES[catalog.kind]), state=state, count=count))
        notices.extend([join_messages(' · ', resource_summaries)] if self.height() <= self._COMPACT_HEIGHT and resource_summaries
                       else resource_details)
        if self._features.enabled('undo_redo') and self._history.reset_reason == 'feature_disabled_change':
            notices.append(msg('El historial se reinició por cambios realizados con Deshacer y rehacer desactivado.'))
        if self._features.enabled('bulk_operations') and not self._features.enabled('undo_redo'):
            notices.append(msg('Active Deshacer y rehacer en Configuración antes de editar en lote.'))
        if self.pinned_group_ids and not self._features.enabled('pinned_sessions'):
            notices.append(msg('Hay sesiones fijadas: siguen protegidas. Activa Sesiones fijadas en Configuración para modificarlas.'))
        catalog_path = getattr(self._repo, '_db_path', None)
        catalog_exists = bool(catalog_path and Path(catalog_path).with_name('sorth_projects.db').exists())
        if (self._scenario_name or catalog_exists) and not self._features.enabled('project_scenarios'):
            notices.append(msg('Hay datos de escenarios conservados. Activa Proyectos y escenarios en Configuración para acceder.'))
        self._feature_notice.setToolTip(join_messages('\n', resource_details))
        self._feature_notice.setAccessibleDescription(join_messages('\n', resource_details))
        self._feature_notice.setText(join_messages('\n', notices))
        self._feature_notice.setVisible(bool(notices))
        if hasattr(self, '_compact_tools'):
            self._update_compact_overview()

    def _confirm_course_inputs(self, courses, classrooms=None, restrictions=None):
        known = {g.group_id for c in courses for g in c.generate_groups()}
        orphaned = {gid for c in self.resources.catalogs for gid, _ids in c.memberships if gid not in known}
        if orphaned and QMessageBox.question(self, msg('Recursos por revisar'), msg(
                'Este cambio elimina {count} sesiones con relaciones de recursos guardadas. Se quitarán esas relaciones, pero se conservarán los recursos. ¿Continuar?', count=len(orphaned)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
            return False
        proposed = self.resources
        if orphaned:
            proposed = SchedulingResources(tuple(replace(c,
                memberships=tuple((gid, ids) for gid, ids in c.memberships if gid in known))
                for c in self.resources.catalogs))
        if not self._confirm_pin_inputs(courses=courses, classrooms=classrooms, restrictions=restrictions, resources=proposed):
            return False
        self.resources = proposed
        return True

    def _edit_resources(self, kind):
        if self._busy or self._restore_failed or not self.resources.catalog(kind).enabled:
            return
        from .resource_dialog import ResourceDialog
        groups = [g for c in self.course_manager.get_courses() for g in c.generate_groups()]
        dialog = ResourceDialog(self.resources.catalog(kind), groups, TimeModel.from_calendar(self.calendar), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        proposed = self.resources.with_catalog(dialog.result_catalog)
        errors = validate_schedule(self.current_schedule or {}, groups,
                    self._validation_classrooms(), TimeModel.from_calendar(self.calendar),
                    {g.group_id for g in self.current_groups or [] if g.lab_override}, proposed)
        if errors and QMessageBox.question(self, msg('Recursos por revisar'), msg(
                'Los cambios entran en conflicto con el horario. Se retirará el resultado y se desfijarán sus sesiones para regenerarlo. ¿Aplicar cambios?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
            return
        self._commit_resource_change(proposed, clear_schedule=bool(errors))

    def _resource_parameter_changes(self, values):
        return [kind for kind in RESOURCE_KINDS
                if self.resources.catalog(kind).enabled != values[kind]]

    def _apply_resource_parameters(self, values):
        if self._busy or self._restore_failed:
            return False
        changed = self._resource_parameter_changes(values)
        if not changed:
            return True
        proposed = self.resources
        for kind in changed:
            proposed = proposed.with_catalog(replace(proposed.catalog(kind), enabled=values[kind]))
        return self._commit_resource_change(proposed, clear_schedule=True)

    def _commit_resource_change(self, proposed, clear_schedule=False):
        # Resource catalogs and activation flags use the same validated,
        # rollback-safe unit of work as calendar edits and manual placements.
        candidate = self._capture_edit_state()
        candidate['resources'] = proposed
        if clear_schedule:
            candidate.update(assignments=None, schedule_present=False,
                             pinned_group_ids=set(), lab_overrides=set(), group_feedback={})
        return self._commit_edit(candidate, 'Actualizar recursos')

    def _show_projects(self):
        if not self._features.enabled('project_scenarios') or self._busy or self._restore_failed:
            return
        try:
            from .project_dialog import ProjectDialog
            ProjectDialog(self).exec()
        except Exception as error:
            QMessageBox.warning(self, msg('Proyectos y escenarios'),
                                msg('No se pudo abrir el catálogo. La sesión actual se conserva. {detail}', detail=str(error)))

    def _update_save_state(self):
        if self._save_error:
            text = msg('Sesión no disponible') if self._restore_failed else msg('Cambios sin guardar')
        else:
            text = msg('Cambios sin guardar') if self._unsaved else msg('Sin cambios pendientes')
        if self._scenario_name:
            state = (msg('Comparación pendiente') if self._scenario_comparison_error else
                     msg('Cambios posteriores a la copia') if self._scenario_dirty else msg('Copia guardada'))
            text = msg('{name} · {state} · {save}', name=self._scenario_name, state=state, save=text)
        self._save_state_label.setText(text)
        self._save_state_label.setToolTip(self._save_error or self._scenario_comparison_error or self._scenario_name or "")
        self._retry_save_button.setVisible(bool(self._save_error or self._scenario_comparison_error))
        self._update_feature_notice()

    def _record_save_error(self, error):
        self._save_error = str(error)
        self._update_save_state()
        self.status_bar.showMessage(msg('No se pudo guardar o recuperar la sesión: {p1}', p1=error))

    def _block_for_recovery(self):
        self._set_busy(True)
        self._progress.setVisible(False)
        self.btn_generate.setText(msg('Recuperación pendiente'))

    def _retry_session(self):
        if self._restore_failed:
            # Do not write an empty/new working session over unreadable data.
            # Keep editing disabled until the original session is readable.
            try:
                if self._repo is None:
                    self._repo = SessionRepository()
                    self.course_manager._repo = self._repo
                # Retry is an explicit restore request. Never unlock merely
                # because SQLite is readable: widget materialization can fail,
                # and declining a second prompt would leave a partial session.
                self._restore_session_if_exists(confirm=False)
                self._update_save_state()
            except Exception as error:
                self._record_save_error(error)
            return not self._restore_failed
        if self._scenario_comparison_error and not self._unsaved:
            # The working session is already durable; retry only its comparison.
            result = self._refresh_scenario_comparison()
            self._update_save_state()
            if result:
                self.status_bar.showMessage(msg('Comparación actualizada. La sesión sigue guardada.'))
            return result
        return self._save_session()

    def _refresh_scenario_comparison(self):
        try:
            if self._scenario_baseline is not None:
                from ..application.scenario_comparison import session_fingerprint
                self._scenario_dirty = session_fingerprint(self._repo.load_session()) != self._scenario_baseline
        except Exception as error:
            # Comparison is optional post-commit metadata, not a failed save.
            self._scenario_comparison_error = msg(
                'Sesión guardada. No se pudo comparar con la copia del escenario. Reintenta la comparación. {detail}',
                detail=str(error))
            self.status_bar.showMessage(self._scenario_comparison_error)
            return False
        self._scenario_comparison_error = None
        return True

    def _save_session(self, *_):
        if self._loading:
            return True
        had_history = self._history.can_undo or self._history.can_redo
        if self._history.observe(self._capture_edit_state()) and had_history:
            self.status_bar.showMessage(join_messages(' ', (self.status_bar.currentMessage(),
                msg('El historial se reinició por cambios fuera del historial.'))))
        self._update_history_actions()
        self._unsaved = True
        self._scenario_dirty = bool(self._scenario_name)
        if self._restore_failed:
            self._update_save_state()
            return False
        try:
            if self._preserve_previous:
                self._repo.backup_session()
                self._preserve_previous = False
            seed = None if self.chk_random_seed.isChecked() else self.seed_input.value()
            self._repo.save_session(
                excel_path=self.excel_path,
                seed=seed,
                classrooms=self._classrooms,
                courses=self.course_manager.get_courses(),
                restrictions=self.classroom_restrictions,
                assignments=self.current_schedule,
                calendar=self.calendar,
                resources=self.resources,
                pinned_group_ids=self.pinned_group_ids,
                lab_overrides={g.group_id for g in (self.current_groups or []) if g.lab_override},
            )
        except Exception as error:
            self._record_save_error(error)
            return False
        self._unsaved = False
        self._save_error = None
        self._refresh_scenario_comparison()
        self._update_save_state()
        return True

    def _restore_session_if_exists(self, confirm=True, show_status=True):
        try:
            if not self._repo.has_session():
                return
            # Validate and deserialize before offering a restore or permitting
            # writes. Malformed sessions must remain recoverable on disk.
            data = self._repo.load_session()
            if data is not None:
                seed = data['seed']
                # QSpinBox silently clamps representable out-of-range integers.
                # Reject them before restoration can authorize a later autosave.
                if seed is not None and (type(seed) is not int or
                        not self.seed_input.minimum() <= seed <= self.seed_input.maximum()):
                    raise ValueError(msg('La semilla guardada está fuera del intervalo permitido.'))
        except Exception as error:
            self._restore_failed = True
            self._record_save_error(error)
            self._block_for_recovery()
            return

        if confirm:
            dlg = QDialog(self)
            dlg.setWindowTitle(msg('Sesión anterior'))
            dlg.setModal(True)
            dlg.setMinimumWidth(500)
            outer = QVBoxLayout()
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            hdr = QLabel(msg('  💾  Sesión anterior encontrada'))
            hdr.setObjectName('dialogInfoHeader')
            outer.addWidget(hdr)
            body = QWidget()
            bl = QVBoxLayout(body)
            bl.setContentsMargins(28, 20, 28, 20)
            bl.setSpacing(20)
            lbl = QLabel(msg('Se encontró una sesión guardada.\n¿Deseas restaurarla?'))
            lbl.setStyleSheet("font-size: 11pt;")
            lbl.setMinimumWidth(440)
            bl.addWidget(lbl)
            btns = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
            )
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            bl.addWidget(btns)
            outer.addWidget(body)
            dlg.setLayout(outer)

            if dlg.exec() != QDialog.DialogCode.Accepted:
                self._preserve_previous = True
                return  # Keep the previous session until actual edits, then back it up.
        try:
            if not data:
                return

            self.calendar = data.get("calendar", ProjectCalendar())
            self.resources = data.get('resources', SchedulingResources())
            preferences = self._features.values()
            for catalog in self.resources.catalogs:
                preferences[catalog.kind] = catalog.enabled
            self.pinned_group_ids = set(data.get("pinned_group_ids", ()))
            self.excel_path = None
            self._classroom_course_map = {}
            self.current_schedule = None
            self.current_groups = None
            self.excel_path_label.setText(msg('Ningún archivo seleccionado'))
            self.schedule_viewer.display_schedule({}, TimeModel.from_calendar(self.calendar), [], {}, classrooms={})
            self._classrooms = data["classrooms"]
            self.classroom_restrictions = data["restrictions"]

            if data["excel_path"] and Path(data["excel_path"]).exists():
                self.excel_path = data["excel_path"]
                self.excel_path_label.setText(Path(data["excel_path"]).name)
                self.excel_path_label.setObjectName("successText")
                # Reload classroom-course map from Excel for restrictions dialog
                try:
                    from ..infrastructure.excel_reader import ExcelReader as _ER
                    r = _ER(data["excel_path"])
                    self._classroom_course_map = r.load_course_classroom_map(
                        known_classrooms=set(self._classrooms.keys())
                    )
                except Exception:
                    pass

            self._loading = True
            self.course_manager.load_courses_from_excel(data["courses"])

            self.chk_random_seed.setChecked(data["seed"] is None)
            if data["seed"] is not None:
                self.seed_input.setValue(data["seed"])

            count = len(self.classroom_restrictions)
            if count:
                self.btn_restrictions.setText(msg('🔒 Restricciones ({p1})', p1=count))
            self.btn_restrictions.setEnabled(bool(self._classroom_course_map))
            self.btn_generate.setEnabled(bool(data["courses"]))

            if data["courses"] or data["assignments"]:
                self.current_schedule = data["assignments"] or {}
                time_model = TimeModel.from_calendar(self.calendar)
                course_name_map = {c.code: c.name for c in data["courses"] if c.name}
                # Regenerate groups so the viewer has full group info
                groups = []
                for c in data["courses"]:
                    groups.extend(c.generate_groups())
                # Re-attach assignments to groups
                for g in groups:
                    g.pinned = g.group_id in self.pinned_group_ids
                    g.lab_override = g.group_id in data.get("lab_overrides", set())
                    if g.group_id in self.current_schedule:
                        g.assignment = self.current_schedule[g.group_id]
                        room = self._classrooms.get(g.assignment[0])
                        if g.required_room_type == "LAB" and room and room.room_type != "LAB" and not g.lab_override:
                            if g.pinned:
                                raise ValueError(msg("La sesión fijada {gid} requiere confirmar una excepción LAB.", gid=g.group_id))
                            del self.current_schedule[g.group_id]
                            g.assignment = None
                            g.unassigned_reason = "Asignación antigua en aula regular retirada: requiere confirmar una excepción manual."
                    else:
                        g.unassigned_reason = unassigned_reason(g, self._validation_classrooms(), time_model)
                errors = validate_schedule(self.current_schedule, groups,
                                           self._validation_classrooms(), time_model,
                                           data.get("lab_overrides", set()), resources=self.resources)
                if errors:
                    self.current_schedule = None
                    self.current_groups = None
                    raise ValueError("\n".join(error.render(msg) for error in errors))
                self.current_groups = groups
                self.schedule_viewer.display_schedule(
                    self.current_schedule, time_model, groups, course_name_map, classrooms=self._classrooms
                )
                self._update_export_actions()

            if not self._features.load_error and preferences != self._features.values():
                try:
                    self._features.save(preferences)
                except (OSError, ValueError) as error:
                    # Effective resource flags belong to this valid session;
                    # damaged/read-only optional UI preferences cannot erase them
                    # or prevent recovery of the user's schedule.
                    self._features.load_error = str(error)
            self._apply_feature_preferences()
            self._refresh_overview()
            self._loading = False
            self._unsaved = False
            self._save_error = None
            self._update_save_state()
            self.status_bar.showMessage(msg('✅ Sesión restaurada correctamente.'))
            self._reset_edit_history('restore')
            if self._restore_failed:
                self._restore_failed = False
                self._set_busy(False)
            if show_status and self.current_groups and len(self.current_schedule or {}) < len(self.current_groups):
                self._show_schedule_status()
        except Exception as e:
            self._loading = False
            self._restore_failed = True
            self._record_save_error(e)
            self._block_for_recovery()

    def _validation_classrooms(self):
        rooms = deepcopy(self._classrooms)
        for name, room in rooms.items():
            room.allowed_courses = self.classroom_restrictions.get(name)
        return rooms

    def _placement_inputs(self):
        if self._busy or self.current_groups is None or not self._features.enabled('placement_suggestions'):
            return None
        calendar = getattr(self, 'calendar', None)
        time_model = TimeModel.from_calendar(calendar) if calendar is not None else TimeModel.default()
        return dict(assignments=self.current_schedule or {}, groups=self.current_groups,
                    classrooms=self._validation_classrooms(), time_model=time_model,
                    lab_overrides={g.group_id for g in self.current_groups if g.lab_override},
                    pinned=self.pinned_group_ids, resources=getattr(self, 'resources', None))

    def _placement_options(self, gid):
        from .placement_options_dialog import PlacementOptionsDialog
        inputs = self._placement_inputs()
        if inputs is None or gid in inputs['assignments'] or gid in self.pinned_group_ids:
            return
        PlacementOptionsDialog(gid, self._placement_inputs, self._apply_placement_option, self).exec()

    def _apply_placement_option(self, options, placement):
        from ..application.placement_suggestions import validate_choice
        from ..application.edit_history import fingerprint
        inputs = self._placement_inputs()
        if inputs is None or validate_choice(options, placement, **inputs):
            return False
        before = self._capture_edit_state()
        candidate = deepcopy(before)
        candidate['assignments'] = dict(candidate['assignments'] or {})
        candidate['assignments'][options.group_id] = placement
        candidate['lab_overrides'].discard(options.group_id)
        candidate['group_feedback'][options.group_id] = ''
        candidate['schedule_present'] = True
        return self._commit_edit(candidate, 'Asignar opción válida', expected=fingerprint(before))

    def _manual_assignment(self, gid):
        if self._busy or self.current_groups is None:
            return
        group = next((g for g in self.current_groups if g.group_id == gid), None)
        if group is None:
            return
        if gid in self.pinned_group_ids:
            QMessageBox.information(self, msg("Sesión fijada"), msg("Desfije la sesión antes de cambiar su asignación."))
            return
        dialog = ManualAssignmentDialog(group, self.current_groups, self.current_schedule or {},
                                        self._validation_classrooms(), TimeModel.from_calendar(self.calendar), self, resources=self.resources)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        candidate = self._capture_edit_state()
        candidate['assignments'] = dict(candidate['assignments'] or {})
        candidate['assignments'][gid] = dialog.result_assignment
        candidate['lab_overrides'].discard(gid)
        if dialog.lab_override:
            candidate['lab_overrides'].add(gid)
        candidate['schedule_present'] = True
        candidate['group_feedback'][gid] = ''
        self._commit_edit(candidate, 'Asignación manual')

    def _edit_course_from_viewer(self, course_code: str):
        """Open CourseDialog for the given course code from the schedule viewer."""
        self.tabs.setCurrentIndex(0)
        self.course_manager.edit_course_by_code(course_code)

    def _on_group_removed(self, gid: str):
        candidate = self._capture_edit_state()
        if gid in candidate['pinned_group_ids']:
            return
        candidate['assignments'] = dict(candidate['assignments'] or {})
        candidate['assignments'].pop(gid, None)
        candidate['lab_overrides'].discard(gid)
        candidate['group_feedback'].pop(gid, None)
        self._commit_edit(candidate, 'Quitar asignación')

    def _on_schedule_cleared(self):
        if self.pinned_group_ids:
            return
        candidate = self._capture_edit_state()
        candidate.update(assignments=None, lab_overrides=set(), schedule_present=False, group_feedback={})
        self._commit_edit(candidate, 'Eliminar horario')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_overview(self):
        courses = self.course_manager.get_courses()
        groups = sum(len(course.generate_groups()) for course in courses)
        text = (plural('course_count', len(courses))
                + '  ·  ' + plural('session_count', groups)
                + '  ·  ' + plural('classroom_count', len(self._classrooms)))
        if self.current_groups is not None:
            text += msg('  ·  {p1}/{p3} sesiones asignadas', p1=len(self.current_schedule or {}), p3=groups)
        elif courses:
            text += msg('  ·  Listo para generar')
        else:
            text += msg('  ·  Cargue un Excel para comenzar')
        self.overview_label.setText(text)

    def _pinned_assignments(self):
        return {gid: placement for gid, placement in (self.current_schedule or {}).items()
                if gid in self.pinned_group_ids}

    def _toggle_pin(self, gid):
        if not self._features.enabled('pinned_sessions'):
            return
        if self._busy or gid not in (self.current_schedule or {}):
            return
        candidate = self._capture_edit_state()
        if gid in candidate['pinned_group_ids']:
            candidate['pinned_group_ids'].remove(gid)
        else:
            candidate['pinned_group_ids'].add(gid)
        self._commit_edit(candidate, 'Cambiar sesión fijada')

    def _pin_input_errors(self, courses=None, classrooms=None, restrictions=None, resources=None):
        """Pure validation shared by edits and staged Excel replacement."""
        if not self.pinned_group_ids:
            return []
        courses = self.course_manager.get_courses() if courses is None else courses
        rooms = deepcopy(self._classrooms if classrooms is None else classrooms)
        restrictions = self.classroom_restrictions if restrictions is None else restrictions
        for name, room in rooms.items():
            room.allowed_courses = restrictions.get(name)
        groups = [group for course in courses for group in course.generate_groups()]
        pins = self._pinned_assignments()
        errors = validate_schedule(pins, groups, rooms, TimeModel.from_calendar(self.calendar),
                                   {g.group_id for g in (self.current_groups or []) if g.lab_override}, resources=self.resources if resources is None else resources)
        old = {g.group_id: g for g in (self.current_groups or [])}
        for group in groups:
            previous = old.get(group.group_id)
            if group.group_id in pins and previous and (
                    group.parent_group_id, group.total_subgroups, group.subgroup_index) != (
                    previous.parent_group_id, previous.total_subgroups, previous.subgroup_index):
                from ..scheduling.validation import ValidationNotice
                errors.append(ValidationNotice('La estructura dividida de {gid} cambió.', gid=group.group_id))
        return errors

    def _confirm_pin_inputs(self, courses=None, classrooms=None, restrictions=None, commit=True, resources=None):
        """Review proposed inputs before committing. Cancel changes nothing."""
        if self._loading or not self.pinned_group_ids:
            return True
        errors = self._pin_input_errors(courses, classrooms, restrictions, resources)
        if not errors:
            return True
        answer = QMessageBox.warning(
            self, msg('Sesiones fijadas en conflicto'),
            msg('Este cambio invalida sesiones fijadas:\n{details}\n\n¿Desfijar todas las sesiones y aplicar el cambio? Cancelar conserva los datos y el horario.',
                details=join_messages('\n', (e.render(msg) for e in errors))),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Yes:
            return False
        if commit:
            self.pinned_group_ids.clear()
        return True

    def _invalidate_schedule(self):
        if self.pinned_group_ids:
            # Only validated pins survive input changes; remaining sessions become
            # explicitly pending, with no stale generated placements presented.
            pins = self._pinned_assignments()
            overrides = {g.group_id for g in (self.current_groups or []) if g.lab_override}
            groups = [g for c in self.course_manager.get_courses() for g in c.generate_groups()]
            for g in groups:
                g.assignment = pins.get(g.group_id)
                g.pinned = g.group_id in self.pinned_group_ids
                g.lab_override = g.pinned and g.group_id in overrides
                if not g.assignment:
                    g.unassigned_reason = unassigned_reason(g, self._validation_classrooms(), TimeModel.from_calendar(self.calendar))
            self.current_schedule = pins
            self.current_groups = groups
            self.schedule_viewer.display_schedule(pins, TimeModel.from_calendar(self.calendar), groups, classrooms=self._classrooms)
            self._update_export_actions()
            return
        self.current_schedule = None
        self.current_groups = None
        self.schedule_viewer._clear()
        self._update_export_actions()

    def _on_inputs_changed(self):
        if self._loading:
            return
        self._invalidate_schedule()
        self._refresh_overview()
        self.btn_generate.setEnabled(bool(self._classrooms and self.course_manager.get_courses()))
        self.status_bar.showMessage(msg('Datos actualizados. Genere un nuevo horario para exportar.'))
        self._save_session()

    def _set_reduced_motion(self, reduced):
        self._motion.set_reduced(reduced)
        update_busy_indicator(self._progress, self._busy, self._motion.reduced)

    def _set_busy(self, busy):
        self._busy = busy
        self._update_history_actions()
        for control in (self.btn_load, self.btn_add_classroom, self.course_manager,
                        self.schedule_viewer, self.chk_random_seed, self.btn_settings,
                        *self.resource_buttons.values()):
            control.setEnabled(not busy)
        self.seed_input.setEnabled(not busy and not self.chk_random_seed.isChecked())
        self.btn_restrictions.setEnabled(not busy and bool(self._classroom_course_map))
        self.btn_generate.setEnabled(not busy and bool(self._classrooms and self.course_manager.get_courses()))
        self.btn_generate.setText(msg('Generando…') if busy else msg('Generar horario'))
        self._cancel_button.setText(msg('Cancelando…') if self._generation_cancelled else msg('Cancelar generación'))
        self._cancel_button.setVisible(busy and self._worker is not None)
        self._cancel_button.setEnabled(busy and not self._generation_cancelled)
        self._update_export_actions()
        update_busy_indicator(self._progress, busy, self._motion.reduced)

    def _set_schedule_expanded(self, expanded):
        self._motion.finish()
        self._workspace_chrome.setVisible(not expanded)
        self._workspace_actions.setVisible(not expanded)
        self.tabs.tabBar().setVisible(not expanded)
        self._update_compact_overview()

    def _on_main_view_changed(self, *_):
        if self.tabs.currentWidget() is not self.schedule_viewer:
            self.schedule_viewer.set_expanded(False)
        # Responsive chrome changes geometry. Finish that synchronous native
        # layout before revealing the new page, otherwise its resize correctly
        # cancels the just-started animation. No event pumping or delayed input.
        self._update_compact_overview()
        self._main_layout.activate()
        self._motion.reveal(self.tabs.currentWidget())

    def _update_compact_overview(self, *_):
        # Reclaim duplicate summaries and secondary toolbars, not table fonts or
        # window size. All secondary actions remain in the native F7 menu; F6
        # retains complete feature status and the full schedule summary.
        compact = self.height() <= self._COMPACT_HEIGHT and self.tabs.currentIndex() == 1
        compact_details = compact and self.height() <= self._COMPACT_HINT_HEIGHT
        self.overview_label.setVisible(not compact)
        # Retained-data warnings are reading content, not optional toolbar
        # chrome. Restore them with detail captions, including the default 800px
        # window, while secondary actions can still live in the F7 menu.
        self._feature_notice.setVisible(not compact_details and bool(self._feature_notice.text()))
        self._compact_tools.setVisible(compact)
        viewer = self.schedule_viewer
        viewer.set_compact_layout(compact_details,
                                  dense=self.height() <= self._DENSE_HEIGHT)
        tab_style = 'QTabBar::tab { padding-top: 7px; padding-bottom: 7px; }' if compact else ''
        if self.tabs.styleSheet() != tab_style:
            self.tabs.setStyleSheet(tab_style)
        for control in (viewer._summary_label, viewer._btn_summary, viewer._btn_clear_schedule):
            control.setVisible(not compact)
        for kind, button in self.resource_buttons.items():
            enabled = self.resources.catalog(kind).enabled
            button.setVisible(enabled and not compact)
            self._compact_resource_actions[kind].setVisible(enabled)
            self._compact_resource_actions[kind].setEnabled(not self._busy and not self._restore_failed)
        self._compact_summary_action.setEnabled(viewer._btn_summary.isEnabled())
        self._compact_clear_action.setEnabled(viewer._btn_clear_schedule.isEnabled() and not self._busy)
        summary = [join_messages(', ', (
            plural('compact_assigned_count', len(self.current_schedule or {})),
            plural('compact_pending_count', max(0, len(self.current_groups or [])-len(self.current_schedule or {}))))),
            msg('Parámetros activos: {count}', count=sum(c.enabled for c in self.resources.catalogs))]
        if self.calendar != ProjectCalendar():
            summary.append(msg('Calendario personalizado'))
        self._compact_summary.setText(join_messages(' · ', summary))
        self._compact_summary.setToolTip(self._feature_notice.text())
        self._compact_summary.setAccessibleDescription(self._feature_notice.text())
        # A hidden resource/notice row changes the nested shell's hint. Settle
        # it before the outer stretch budget on both navigation and resize.
        self._file_layout.activate()
        self._workspace_chrome.layout().activate()
        self._main_layout.activate()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_main_layout'):
            dense = self.height() <= self._DENSE_HEIGHT
            # Reclaim whitespace, not control height, for native Windows metrics.
            # Keep the schedule rows readable at the supported 960×640 minimum.
            # Native Segoe UI chrome consumes more height than the Linux
            # fallback at the same 10pt. Spend whitespace first, leaving fonts,
            # action targets, visible scopes and reading rows unchanged.
            # Segoe UI plus stable label borders needs this small whitespace
            # reserve to retain four full rows at compact threshold heights.
            self._main_layout.setSpacing(1 if dense else 8)
            self._main_layout.setContentsMargins(*(16, 2, 16, 2) if dense else (24, 20, 24, 12))
            self._file_layout.setSpacing(1 if dense else 16)
            self._workspace_chrome.layout().setSpacing(1 if dense else 8)
            if hasattr(self, '_feature_notice') and hasattr(self, '_history'):
                self._update_feature_notice()
                self._update_compact_overview()

    def closeEvent(self, event):
        # Import cancellation can leave its reader draining while generation
        # starts. Cancel both immediately, regardless of which finishes first.
        # Ownership lasts through queued result delivery, even after run() exits.
        if self._worker is not None:
            self._close_after_generation = True
            self._cancel_generation()
        if hasattr(self, "_import") and not self._import.prepare_close():
            event.ignore()
            return
        if self._worker is not None:
            self._import.closing = False
            event.ignore()
            return
        # No worker owns the UI now; Cancel in a failed-save prompt must leave
        # the accepted session editable rather than stranded in shutdown busy.
        self._set_import_busy(False)
        self._motion.finish()
        if not self._unsaved:
            event.accept()
            return
        while not self._save_session():
            choice = QMessageBox.warning(
                self, msg('Cambios sin guardar'),
                msg('No se pudo guardar la sesión. Si sales, perderás los cambios sin guardar.\nEl último guardado y las copias existentes se conservarán.\n\n{p1}', p1=self._save_error or ''),
                QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if choice == QMessageBox.StandardButton.Discard:
                event.accept()
                return
            if choice != QMessageBox.StandardButton.Retry:
                self._import.closing = False
                event.ignore()
                return
        event.accept()

    def _set_window_icon(self):
        try:
            if getattr(sys, 'frozen', False):
                icon_path = Path(sys._MEIPASS) / 'assets' / 'sorth.ico'
            else:
                icon_path = Path(__file__).parent.parent.parent / 'assets' / 'sorth.ico'
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
