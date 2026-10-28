"""Own desktop export operations without expanding the main window."""
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog
from ..infrastructure.excel_reader import ExcelImportError
from ..infrastructure.schedule_exporter import ScheduleExporter
from ..scheduling.time_model import TimeModel
from ..scheduling.validation import validate_schedule, unassigned_reason
from .dialogs import _InfoDialog
from .i18n import msg, join_messages, language_manager
from .locales import LANGUAGES
from .i18n_widgets import QMessageBox


class ExportController:
    """Coordinate export presentation and explicit persistence boundaries."""

    def __init__(self, window):
        self.window = window

    def refresh_actions(self):
        window = self.window
        if not hasattr(window, "btn_export_filtered"):
            return
        count = len(window.schedule_viewer.filtered_assignments())
        ready = not window._busy and bool(window.current_schedule)
        window.btn_export.setEnabled(ready)
        window.btn_export_filtered.setText(msg('Exportar filtrado ({p1})', p1=count))
        window.btn_export_filtered.setEnabled(ready and count > 0)
        window.btn_export_filtered.setToolTip(
            msg('Exportar {p1} sesiones asignadas que coinciden con Buscar, Aula, Día y Estado.\nLa pestaña activa y el selector del aula de la cuadrícula no cambian este conjunto.', p1=count)
            + msg('\nEn Excel también se incluyen todas las sesiones pendientes del horario, aunque no coincidan con los filtros.')
        )


    def save(self, filtered=False):
        window = self.window
        if window._busy:
            return
        if not window.current_schedule:
            QMessageBox.warning(window, msg('Advertencia'), msg('No hay horario para exportar.'))
            return
        errors = validate_schedule(window.current_schedule or {}, window.current_groups or [],
                                   window._validation_classrooms(), TimeModel.from_calendar(window.calendar),
                                   {g.group_id for g in (window.current_groups or []) if g.lab_override}, resources=window.resources)
        if errors:
            QMessageBox.warning(window, msg('Horario no válido'), join_messages('\n', (error.render(msg) for error in errors)))
            return
        assignments = (window.schedule_viewer.filtered_assignments() if filtered
                       else dict(window.current_schedule))
        if not assignments:
            QMessageBox.information(window, msg('Sin coincidencias'),
                                    msg('No hay sesiones asignadas con estos filtros. Cambie o restablezca los filtros.'))
            return
        scope = msg('filtrado') if filtered else msg('todas las asignaciones')
        count = len(assignments)
        pending = len(window.current_groups or []) - len(window.current_schedule)
        if pending:
            scope = msg('{scope} · horario parcial, {pending} pendientes', scope=scope, pending=pending)
        file_path, selected_format = QFileDialog.getSaveFileName(
            window, msg('Guardar horario {p1} · {p3} sesiones', p1=scope, p3=count),
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
                    confirmation = QMessageBox(window)
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

            time_model = TimeModel.from_calendar(window.calendar)
            exporter = ScheduleExporter(time_model)
            courses = window.course_manager.get_courses()
            course_name_map = {c.code: c.name for c in courses if c.name}
            if file_path.lower().endswith(".pdf"):
                exporter.to_pdf(assignments, file_path, groups=window.current_groups,
                                course_name_by_code=course_name_map, filtered=filtered,
                                total_assigned=len(window.current_schedule), pending_count=pending,
                                filters=window.schedule_viewer.export_filter_description(),
                                labels=LANGUAGES[language_manager().language].messages)
            elif file_path.lower().endswith(".csv"):
                exporter.to_csv(assignments, file_path, groups=window.current_groups,
                                course_name_by_code=course_name_map)
            else:
                metadata = {}
                if pending or filtered:
                    rooms = window._validation_classrooms()
                    metadata = dict(
                        pending=[dict(group_id=group.group_id,
                                      reason=str(msg(group.unassigned_reason or
                                          unassigned_reason(group, rooms, time_model))))
                                 for group in window.current_groups or []
                                 if group.group_id not in window.current_schedule],
                        status="partial" if pending else "complete",
                        total_assigned=len(window.current_schedule), filtered=filtered,
                        filters=window.schedule_viewer.export_filter_description() if filtered else None)
                exporter.to_excel(assignments, file_path, groups=window.current_groups,
                                  course_name_by_code=course_name_map, include_grid=True,
                                  **metadata)
        except Exception as e:
            # Keep the latest attempt readable after its modal is dismissed.
            # Only expose the basename here; technical error details stay in
            # the existing error dialog rather than leaking into F6/status.
            window.status_bar.showMessage(msg(
                'No se pudo exportar a {filename}. El horario se conserva. Revise el destino y vuelva a intentarlo.',
                filename=Path(file_path).name))
            _InfoDialog(window, msg('Error'), msg('Error al exportar:\n{p1}', p1=e.render(msg) if isinstance(e, ExcelImportError) else str(e)), warning=True).exec()
        else:
            window.status_bar.showMessage(msg('Horario {p1}: {p3} sesiones exportadas a {p5}', p1=scope, p3=count, p5=Path(file_path).name))
            _InfoDialog(window, msg('Éxito'), msg('Horario {p1}: {p3} sesiones exportadas a:\n{p5}', p1=scope, p3=count, p5=file_path)).exec()
