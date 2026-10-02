# src/gui/main_window.py

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt
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
from .theme import apply_theme, COLORS
from .motion import MotionController, update_busy_indicator
from .manual_assignment_dialog import ManualAssignmentDialog
from ..scheduling.validation import validate_schedule, unassigned_reason
from copy import deepcopy

from .i18n import msg, plural, language_manager, join_messages
from .locales import LANGUAGES
from .i18n_widgets import (
    QProgressBar, QComboBox, QCheckBox, QDialog, QDialogButtonBox, QLabel, QMainWindow, QMessageBox, QPushButton, QSpinBox, QStatusBar, QTabWidget, QWidget
)


class MainWindow(QMainWindow):

    def __init__(self, repo=None, restore_session=True):
        super().__init__()
        self._busy = False
        self._loading = False
        self._worker = None
        self.excel_path: str | None = None
        self.current_schedule: dict | None = None
        self.current_groups: list | None = None
        self.classroom_restrictions: dict[str, set[str]] = {}
        self._classroom_course_map: dict[str, list[str]] = {}
        self._classrooms: dict[str, Classroom] = {}
        self._unsaved = False
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

        self._motion = MotionController(self)
        self._init_ui()
        self._update_save_state()
        if self._restore_failed:
            self._record_save_error(self._save_error)
            self._block_for_recovery()
        if restore_session and self._repo is not None:
            self._restore_session_if_exists()
        self.chk_random_seed.toggled.connect(self._save_session)
        self.seed_input.valueChanged.connect(self._save_session)

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
        main_layout.setSpacing(16)

        main_layout.addLayout(self._create_file_section())

        self.tabs = QTabWidget()
        self.course_manager = CourseManagerWidget(repo=self._repo)
        self.tabs.addTab(self.course_manager, msg('📚 Gestión de Cursos'))
        self.tabs.setTabToolTip(0, msg('Ver, agregar, editar y eliminar los cursos a programar'))
        self.course_manager.courses_changed.connect(self._on_inputs_changed)
        self.schedule_viewer = ScheduleViewerWidget()
        self.tabs.addTab(self.schedule_viewer, msg('📅 Horario Generado'))
        self.tabs.setTabToolTip(1, msg('Visualizar el horario generado en lista, cuadrícula o por aula'))
        self.schedule_viewer.edit_course_requested.connect(self._edit_course_from_viewer)
        self.schedule_viewer.group_removed.connect(self._on_group_removed)
        self.schedule_viewer.schedule_cleared.connect(self._on_schedule_cleared)
        main_layout.addWidget(self.tabs, 1)
        self.tabs.currentChanged.connect(
            lambda _index: self._motion.reveal(self.tabs.currentWidget()))
        self.schedule_viewer.tabs.currentChanged.connect(
            lambda _index: self._motion.reveal(self.schedule_viewer.tabs.currentWidget()))

        main_layout.addLayout(self._create_actions_section())

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setFixedWidth(160)
        self._progress.setFixedHeight(16)
        self._progress.setVisible(False)
        self.status_bar.addPermanentWidget(self._progress)

        self.chk_reduce_motion = QCheckBox(msg('Reducir animaciones'))
        self.chk_reduce_motion.setToolTip(msg('Desactiva las transiciones y el indicador animado.'))
        self.chk_reduce_motion.setChecked(self._motion.reduced)
        self.chk_reduce_motion.toggled.connect(self._set_reduced_motion)
        self.status_bar.addPermanentWidget(self.chk_reduce_motion)
        update_busy_indicator(self._progress, False, self._motion.reduced)

        self._save_state_label = QLabel()
        self._save_state_label.setAccessibleName(msg('Estado de guardado'))
        self._retry_save_button = QPushButton(msg('Reintentar'))
        self._retry_save_button.clicked.connect(self._retry_session)
        self.status_bar.addPermanentWidget(self._save_state_label)
        self.status_bar.addPermanentWidget(self._retry_save_button)
        self.status_bar.showMessage(msg('Listo. Cargue un archivo Excel para comenzar.'))

    # ------------------------------------------------------------------
    # UI builders
    # ------------------------------------------------------------------

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
        language_label.setStyleSheet(f"color: {COLORS['on_navy_muted']};")
        heading.addWidget(language_label)
        heading.addWidget(self.language_selector)
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
        btn_load.setShortcut("Ctrl+O")
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

        return layout

    def _sync_language_selector(self, language):
        self.language_selector.blockSignals(True)
        self.language_selector.setCurrentIndex(self.language_selector.findData(language))
        self.language_selector.blockSignals(False)

    def _create_actions_section(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        seed_label = QLabel(msg('Semilla:'))
        seed_label.setToolTip(
            msg('Controla la aleatoriedad del algoritmo.\nSemilla fija → mismo horario cada vez (reproducible).\nSemilla aleatoria → resultados distintos en cada ejecución.')
        )

        self.chk_random_seed = QCheckBox(msg('Aleatoria'))
        self.chk_random_seed.setToolTip(msg('Activar para usar una semilla aleatoria en cada generación'))
        self.chk_random_seed.setChecked(False)

        self.seed_input = QSpinBox()
        self.seed_input.setRange(0, 999999)
        self.seed_input.setValue(42)
        self.seed_input.setPrefix(msg('Valor: '))
        self.seed_input.setToolTip(msg('Valor de semilla fija para resultados reproducibles'))
        self.chk_random_seed.toggled.connect(self.seed_input.setDisabled)

        self.btn_generate = QPushButton(msg('Generar horario'))
        self.btn_generate.setObjectName("primaryAction")
        self.btn_generate.setShortcut("Ctrl+Return")
        self.btn_generate.setToolTip(
            msg('Ejecutar el algoritmo de programación con los cursos y aulas cargados.\nEl resultado se muestra en la pestaña Horario Generado.')
        )
        self.btn_generate.clicked.connect(self._generate_schedule)
        self.btn_generate.setEnabled(False)

        self.btn_export = QPushButton(msg('Exportar completo'))
        self.btn_export.setShortcut("Ctrl+S")
        self.btn_export.setToolTip(
            msg('Guardar el horario generado en formato Excel (.xlsx) o CSV.\nEl Excel incluye una grilla visual por aula.')
        )
        self.btn_export.clicked.connect(lambda: self._export_schedule())
        self.btn_export.setEnabled(False)
        self.btn_export_filtered = QPushButton(msg('Exportar filtrado (0)'))
        self.btn_export_filtered.setEnabled(False)
        self.btn_export_filtered.clicked.connect(lambda: self._export_schedule(filtered=True))
        self.schedule_viewer.filters_changed.connect(self._update_export_actions)
        self.schedule_viewer.manual_assignment_requested.connect(self._manual_assignment)

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
        if self._busy:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, msg('Seleccionar archivo Excel'), "",
            msg('Libro de Excel (*.xlsx)')
        )
        if not file_path:
            return

        try:
            reader = ExcelReader(file_path)
            imported = reader.load_validated()
            classrooms = imported.classrooms
            courses = imported.courses
            classroom_course_map = imported.classroom_course_map
            if imported.warnings:
                review = QMessageBox(self)
                review.setWindowTitle(msg('Revisar importación'))
                review.setIcon(QMessageBox.Icon.Warning)
                review.setTextFormat(Qt.TextFormat.PlainText)
                review.setText(msg('Avisos del archivo: {count}', count=len(imported.warnings)))
                review.setInformativeText(join_messages('\n', (item.render(msg) for item in imported.warnings[:3])) + msg('\n\nRevise los detalles antes de continuar. Cancelar conserva la sesión actual.'))
                review.setDetailedText(join_messages('\n', (item.render(msg) for item in imported.warnings)))
                review.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
                review.setDefaultButton(QMessageBox.StandardButton.Cancel)
                review.setButtonText(QMessageBox.StandardButton.Ok, msg('Importar con avisos'))
                review.setButtonText(QMessageBox.StandardButton.Cancel, msg('Cancelar'))
                if review.exec() != QMessageBox.StandardButton.Ok:
                    return
            self._loading = True
            self._classroom_course_map = classroom_course_map
            self._classrooms = classrooms

            self.excel_path = file_path
            self.excel_path_label.setText(Path(file_path).name)
            self.excel_path_label.setStyleSheet("color: green;")

            # Load courses into the manager widget
            self.course_manager.load_courses_from_excel(courses)

            # Reset restrictions when a new file is loaded
            self.classroom_restrictions = {}

            self._loading = False
            self._invalidate_schedule()
            self._refresh_overview()
            self.btn_generate.setEnabled(bool(courses and classrooms))
            self.btn_restrictions.setEnabled(bool(self._classroom_course_map))

            self.status_bar.showMessage(
                msg('✅ Excel cargado: {p1}  ({p3} aulas, {p5} cursos)', p1=Path(file_path).name, p3=len(classrooms), p5=len(courses))
            )
            self._save_session()

        except Exception as e:
            QMessageBox.critical(self, msg('Error'),
                                 msg('Error al cargar archivo Excel:\n{p1}', p1=e.render(msg) if isinstance(e, ExcelImportError) else str(e)))
            self._loading = False
            self.status_bar.showMessage(msg('No se cargó el archivo. La sesión anterior se conserva.'))

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
            self.classroom_restrictions = dialog.get_restrictions()
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

    def _generate_schedule(self):
        if self._busy:
            return
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
        )
        self._worker.result_ready.connect(self._on_schedule_done)
        self._worker.finished.connect(lambda: self._set_busy(False))
        self._worker.error.connect(self._on_schedule_error)

        self._set_busy(True)
        self.status_bar.showMessage(msg('⏳ Generando horario...'))
        self._worker.start()

    def _on_schedule_done(self, assignments, groups):

        if assignments is not None and groups is not None:
            self.current_schedule = assignments
            self.current_groups   = groups

            courses = self.course_manager.get_courses()
            time_model = TimeModel.default()
            course_name_map = {c.code: c.name for c in courses if c.name}

            self.schedule_viewer.display_schedule(
                assignments, time_model, groups, course_name_map
            )
            already_showing_results = self.tabs.currentIndex() == 1
            self.tabs.setCurrentIndex(1)
            if already_showing_results:
                self._motion.reveal(self.schedule_viewer)
            self._update_export_actions()

            total      = len(groups)
            assigned   = len(assignments)
            unassigned = total - assigned

            lines = [
                msg('Grupos asignados:    {p1} / {p3}', p1=assigned, p3=total),
                msg('Aulas utilizadas:    {p1}', p1=len(set(v[0] for v in assignments.values()))),
                msg('Cursos programados:  {p1}', p1=len(set(gid.rsplit('-G',1)[0] for gid in assignments))),
            ]
            if unassigned:
                lines.append(msg('\n⚠️  {p1} grupo(s) sin asignar.\nRevisa la Lista Detallada (marcados en rojo).', p1=unassigned))

            self.status_bar.showMessage(msg('✅ Horario generado: {p1}/{p3} grupos', p1=assigned, p3=total))
            self._refresh_overview()
            self._save_session()
        else:
            self.status_bar.showMessage(msg('❌ No se pudo generar el horario'))
            dlg = _InfoDialog(
                self, msg('Sin solución'),
                msg('No se pudo generar un horario válido.\n\nPosibles causas:\n  • No hay suficientes aulas disponibles\n  • Restricciones demasiado estrictas\n  • Conflictos de horario entre cursos'),
                warning=True
            )
            dlg.exec()

    def _on_schedule_error(self, message):
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
        )

    def _export_schedule(self, filtered=False):
        if self._busy:
            return
        if not self.current_schedule:
            QMessageBox.warning(self, msg('Advertencia'), msg('No hay horario para exportar.'))
            return
        errors = validate_schedule(self.current_schedule or {}, self.current_groups or [],
                                   self._validation_classrooms(), TimeModel.default(),
                                   {g.group_id for g in (self.current_groups or []) if g.lab_override})
        if errors:
            QMessageBox.warning(self, msg('Horario no válido'), join_messages('\n', (error.render(msg) for error in errors)))
            return
        assignments = (self.schedule_viewer.filtered_assignments() if filtered
                       else dict(self.current_schedule))
        if not assignments:
            QMessageBox.information(self, msg('Sin coincidencias'),
                                    msg('No hay sesiones asignadas con estos filtros. Cambie o restablezca los filtros.'))
            return
        scope = msg('filtrado') if filtered else msg('completo')
        count = len(assignments)
        file_path, selected_format = QFileDialog.getSaveFileName(
            self, msg('Guardar horario {p1} · {p3} sesiones', p1=scope, p3=count),
            "horario_filtrado.xlsx" if filtered else "horario.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )
        if not file_path:
            return
        if not Path(file_path).suffix:
            file_path += ".csv" if selected_format.startswith("CSV") else ".xlsx"

        try:
            time_model = TimeModel.default()
            exporter = ScheduleExporter(time_model)
            courses = self.course_manager.get_courses()
            course_name_map = {c.code: c.name for c in courses if c.name}
            if file_path.lower().endswith(".csv"):
                exporter.to_csv(assignments, file_path, groups=self.current_groups,
                                course_name_by_code=course_name_map)
            else:
                exporter.to_excel(assignments, file_path, groups=self.current_groups,
                                  course_name_by_code=course_name_map, include_grid=True)
            self.status_bar.showMessage(msg('Horario {p1}: {p3} sesiones exportadas a {p5}', p1=scope, p3=count, p5=Path(file_path).name))
            _InfoDialog(self, msg('Éxito'), msg('Horario {p1}: {p3} sesiones exportadas a:\n{p5}', p1=scope, p3=count, p5=file_path)).exec()
        except Exception as e:
            _InfoDialog(self, msg('Error'), msg('Error al exportar:\n{p1}', p1=e.render(msg) if isinstance(e, ExcelImportError) else str(e)), warning=True).exec()

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def _update_save_state(self):
        if self._save_error:
            text = msg('Sesión no disponible') if self._restore_failed else msg('Cambios sin guardar')
        else:
            text = msg('Cambios sin guardar') if self._unsaved else msg('Sin cambios pendientes')
        self._save_state_label.setText(text)
        self._save_state_label.setToolTip(self._save_error or "")
        self._retry_save_button.setVisible(bool(self._save_error))

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
                self._repo.load_session()
                self._restore_failed = False
                self._save_error = None
                self._set_busy(False)
                self._restore_session_if_exists()
                self._update_save_state()
            except Exception as error:
                self._record_save_error(error)
            return not self._restore_failed
        return self._save_session()

    def _save_session(self, *_):
        if self._loading:
            return True
        self._unsaved = True
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
                lab_overrides={g.group_id for g in (self.current_groups or []) if g.lab_override},
            )
        except Exception as error:
            self._record_save_error(error)
            return False
        self._unsaved = False
        self._save_error = None
        self._update_save_state()
        return True

    def _restore_session_if_exists(self):
        try:
            if not self._repo.has_session():
                return
            # Validate and deserialize before offering a restore or permitting
            # writes. Malformed sessions must remain recoverable on disk.
            data = self._repo.load_session()
        except Exception as error:
            self._restore_failed = True
            self._record_save_error(error)
            self._block_for_recovery()
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(msg('Sesión anterior'))
        dlg.setModal(True)
        dlg.setMinimumWidth(500)
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        hdr = QLabel(msg('  💾  Sesión anterior encontrada'))
        hdr.setStyleSheet(
            "background-color: #1967D2; color: #FFFFFF; "
            "font-size: 12pt; font-weight: bold; padding: 14px 20px;"
        )
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

            self._classrooms = data["classrooms"]
            self.classroom_restrictions = data["restrictions"]

            if data["excel_path"] and Path(data["excel_path"]).exists():
                self.excel_path = data["excel_path"]
                self.excel_path_label.setText(Path(data["excel_path"]).name)
                self.excel_path_label.setStyleSheet("color: green;")
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

            if data["courses"]:
                self.current_schedule = data["assignments"] or {}
                time_model = TimeModel.default()
                course_name_map = {c.code: c.name for c in data["courses"] if c.name}
                # Regenerate groups so the viewer has full group info
                groups = []
                for c in data["courses"]:
                    groups.extend(c.generate_groups())
                # Re-attach assignments to groups
                for g in groups:
                    g.lab_override = g.group_id in data.get("lab_overrides", set())
                    if g.group_id in self.current_schedule:
                        g.assignment = self.current_schedule[g.group_id]
                        room = self._classrooms.get(g.assignment[0])
                        if g.required_room_type == "LAB" and room and room.room_type != "LAB" and not g.lab_override:
                            del self.current_schedule[g.group_id]
                            g.assignment = None
                            g.unassigned_reason = "Asignación antigua en aula regular retirada: requiere confirmar una excepción manual."
                    else:
                        g.unassigned_reason = unassigned_reason(g, self._validation_classrooms(), time_model)
                self.current_groups = groups
                self.schedule_viewer.display_schedule(
                    self.current_schedule, time_model, groups, course_name_map
                )
                self._update_export_actions()

            self._refresh_overview()
            self._loading = False
            self._unsaved = False
            self._save_error = None
            self._update_save_state()
            self.status_bar.showMessage(msg('✅ Sesión restaurada correctamente.'))
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

    def _manual_assignment(self, gid):
        if self._busy or self.current_groups is None:
            return
        group = next((g for g in self.current_groups if g.group_id == gid), None)
        if group is None:
            return
        dialog = ManualAssignmentDialog(group, self.current_groups, self.current_schedule or {},
                                        self._validation_classrooms(), TimeModel.default(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        group.assignment = dialog.result_assignment
        group.lab_override = dialog.lab_override
        group.unassigned_reason = ""
        if self.current_schedule is None:
            self.current_schedule = {}
        self.current_schedule[gid] = group.assignment
        self.schedule_viewer.display_schedule(self.current_schedule, TimeModel.default(), self.current_groups)
        self._update_export_actions()
        self._refresh_overview()
        self._save_session()

    def _edit_course_from_viewer(self, course_code: str):
        """Open CourseDialog for the given course code from the schedule viewer."""
        self.tabs.setCurrentIndex(0)
        self.course_manager.edit_course_by_code(course_code)

    def _on_group_removed(self, gid: str):
        if self.current_schedule and gid in self.current_schedule:
            del self.current_schedule[gid]
        if self.current_groups:
            for g in self.current_groups:
                if g.group_id == gid and g.is_assigned():
                    g.assignment = None
                    g.lab_override = False

        self._update_export_actions()
        self._refresh_overview()
        self._save_session()

    def _on_schedule_cleared(self):
        self.current_schedule = None
        self.current_groups = None
        self._update_export_actions()
        self._refresh_overview()
        self.status_bar.showMessage(msg('Horario eliminado.'))
        self._save_session()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_overview(self):
        courses = self.course_manager.get_courses()
        groups = sum(len(course.generate_groups()) for course in courses)
        text = (plural('course_count', len(courses))
                + '  ·  ' + plural('session_count', groups)
                + '  ·  ' + plural('classroom_count', len(self._classrooms)))
        if self.current_schedule:
            text += msg('  ·  {p1}/{p3} sesiones asignadas', p1=len(self.current_schedule), p3=groups)
        elif courses:
            text += msg('  ·  Listo para generar')
        else:
            text += msg('  ·  Cargue un Excel para comenzar')
        self.overview_label.setText(text)

    def _invalidate_schedule(self):
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
        for control in (self.btn_load, self.btn_add_classroom, self.course_manager,
                        self.schedule_viewer, self.chk_random_seed):
            control.setEnabled(not busy)
        self.seed_input.setEnabled(not busy and not self.chk_random_seed.isChecked())
        self.btn_restrictions.setEnabled(not busy and bool(self._classroom_course_map))
        self.btn_generate.setEnabled(not busy and bool(self._classrooms and self.course_manager.get_courses()))
        self.btn_generate.setText(msg('Generando…') if busy else msg('Generar horario'))
        self._update_export_actions()
        update_busy_indicator(self._progress, busy, self._motion.reduced)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_main_layout'):
            compact = self.height() <= 700
            # Reclaim whitespace, not control height, for native Windows metrics.
            # Keep the schedule rows readable at the supported 960×640 minimum.
            self._main_layout.setSpacing(6 if compact else 16)
            self._main_layout.setContentsMargins(*(16, 8, 16, 6) if compact else (24, 20, 24, 12))
            self._file_layout.setSpacing(4 if compact else 16)

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            self.status_bar.showMessage(msg('Espere a que termine la generación antes de cerrar.'))
            event.ignore()
            return
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
