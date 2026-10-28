"""Own desktop session operations without expanding the main window."""
from pathlib import Path
from PyQt6.QtWidgets import QVBoxLayout
from ..infrastructure.session_repository import SessionRepository
from ..scheduling.project_calendar import ProjectCalendar
from ..scheduling.classroom_preferences import classroom_course_map
from ..scheduling.teaching_resources import SchedulingResources
from ..scheduling.time_model import TimeModel
from ..scheduling.validation import validate_schedule, unassigned_reason
from .i18n import msg, join_messages
from .i18n_widgets import QDialog, QDialogButtonBox, QLabel, QWidget


class SessionController:
    """Coordinate session presentation and explicit persistence boundaries."""

    def __init__(self, window):
        self.window = window

    def refresh_status(self):
        window = self.window
        if window._save_error:
            text = msg('Sesión no disponible') if window._restore_failed else msg('Cambios sin guardar')
        else:
            text = msg('Cambios sin guardar') if window._unsaved else msg('Sin cambios pendientes')
        if window._scenario_name:
            state = (msg('Comparación pendiente') if window._scenario_comparison_error else
                     msg('Cambios posteriores a la copia') if window._scenario_dirty else msg('Copia guardada'))
            text = msg('{name} · {state} · {save}', name=window._scenario_name, state=state, save=text)
        window._save_state_label.setText(text)
        window._save_state_label.setToolTip(window._save_error or window._scenario_comparison_error or window._scenario_name or "")
        window._retry_save_button.setVisible(bool(window._save_error or window._scenario_comparison_error))
        window._update_feature_notice()


    def record_error(self, error):
        window = self.window
        window._save_error = str(error)
        window.session.refresh_status()
        window.status_bar.showMessage(msg('No se pudo guardar o recuperar la sesión: {p1}', p1=error))


    def block_for_recovery(self):
        window = self.window
        window._set_busy(True)
        window._progress.setVisible(False)
        window.btn_generate.setText(msg('Recuperación pendiente'))


    def retry(self):
        window = self.window
        if window._restore_failed:
            # Do not write an empty/new working session over unreadable data.
            # Keep editing disabled until the original session is readable.
            try:
                if window._repo is None:
                    window._repo = SessionRepository()
                    window.course_manager._repo = window._repo
                # Retry is an explicit restore request. Never unlock merely
                # because SQLite is readable: widget materialization can fail,
                # and declining a second prompt would leave a partial session.
                window.session.restore(confirm=False)
                window.session.refresh_status()
            except Exception as error:
                window.session.record_error(error)
            return not window._restore_failed
        if window._scenario_comparison_error and not window._unsaved:
            # The working session is already durable; retry only its comparison.
            result = window.session.refresh_comparison()
            window.session.refresh_status()
            if result:
                window.status_bar.showMessage(msg('Comparación actualizada. La sesión sigue guardada.'))
            return result
        return window.session.save()


    def refresh_comparison(self):
        window = self.window
        try:
            if window._scenario_baseline is not None:
                from ..application.scenario_comparison import session_fingerprint
                window._scenario_dirty = session_fingerprint(window._repo.load_session()) != window._scenario_baseline
        except Exception as error:
            # Comparison is optional post-commit metadata, not a failed save.
            window._scenario_comparison_error = msg(
                'Sesión guardada. No se pudo comparar con la copia del escenario. Reintenta la comparación. {detail}',
                detail=str(error))
            window.status_bar.showMessage(window._scenario_comparison_error)
            return False
        window._scenario_comparison_error = None
        return True


    def save(self, *_):
        window = self.window
        if window._loading:
            return True
        had_history = window._history.can_undo or window._history.can_redo
        if window._history.observe(window._capture_edit_state()) and had_history:
            window.status_bar.showMessage(join_messages(' ', (window.status_bar.currentMessage(),
                msg('El historial se reinició por cambios fuera del historial.'))))
        window._update_history_actions()
        window._unsaved = True
        window._scenario_dirty = bool(window._scenario_name)
        if window._restore_failed:
            window.session.refresh_status()
            return False
        try:
            if window._preserve_previous:
                window._repo.backup_session()
                window._preserve_previous = False
            seed = None if window.chk_random_seed.isChecked() else window.seed_input.value()
            window._repo.save_session(
                excel_path=window.excel_path,
                seed=seed,
                classrooms=window._classrooms,
                courses=window.course_manager.get_courses(),
                restrictions=window.classroom_restrictions,
                assignments=window.current_schedule,
                calendar=window.calendar,
                resources=window.resources,
                pinned_group_ids=window.pinned_group_ids,
                lab_overrides={g.group_id for g in (window.current_groups or []) if g.lab_override},
            )
        except Exception as error:
            window.session.record_error(error)
            return False
        window._unsaved = False
        window._save_error = None
        window.session.refresh_comparison()
        window.session.refresh_status()
        return True


    def restore(self, confirm=True, show_status=True):
        window = self.window
        try:
            if not window._repo.has_session():
                return
            # Validate and deserialize before offering a restore or permitting
            # writes. Malformed sessions must remain recoverable on disk.
            data = window._repo.load_session()
            if data is not None:
                seed = data['seed']
                # QSpinBox silently clamps representable out-of-range integers.
                # Reject them before restoration can authorize a later autosave.
                if seed is not None and (type(seed) is not int or
                        not window.seed_input.minimum() <= seed <= window.seed_input.maximum()):
                    raise ValueError(msg('La semilla guardada está fuera del intervalo permitido.'))
        except Exception as error:
            window._restore_failed = True
            window.session.record_error(error)
            window.session.block_for_recovery()
            return

        if confirm:
            dlg = QDialog(window)
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
                window._preserve_previous = True
                return  # Keep the previous session until actual edits, then back it up.
        try:
            if not data:
                return

            window.calendar = data.get("calendar", ProjectCalendar())
            window.resources = data.get('resources', SchedulingResources())
            preferences = window._features.values()
            for catalog in window.resources.catalogs:
                preferences[catalog.kind] = catalog.enabled
            window.pinned_group_ids = set(data.get("pinned_group_ids", ()))
            window.excel_path = None
            window._classroom_course_map = {}
            window.current_schedule = None
            window.current_groups = None
            window.excel_path_label.setText(msg('Ningún archivo seleccionado'))
            window.schedule_viewer.display_schedule({}, TimeModel.from_calendar(window.calendar), [], {}, classrooms={})
            window._classrooms = data["classrooms"]
            window.classroom_restrictions = data["restrictions"]

            if data["excel_path"] and Path(data["excel_path"]).exists():
                window.excel_path = data["excel_path"]
                window.excel_path_label.setText(Path(data["excel_path"]).name)
                window.excel_path_label.setObjectName("successText")
            # The accepted snapshot is authoritative even if the source workbook
            # was edited or removed. Restoration never reimports external data.
            window._classroom_course_map = classroom_course_map(data['courses'], set(window._classrooms))

            window._loading = True
            window.course_manager.load_courses_from_excel(data["courses"])

            window.chk_random_seed.setChecked(data["seed"] is None)
            if data["seed"] is not None:
                window.seed_input.setValue(data["seed"])

            count = len(window.classroom_restrictions)
            if count:
                window.btn_restrictions.setText(msg('🔒 Restricciones ({p1})', p1=count))
            window.btn_restrictions.setEnabled(bool(window._classroom_course_map))
            window.btn_generate.setEnabled(bool(data["courses"]))

            if data["assignments"] is not None:
                window.current_schedule = data["assignments"] or {}
                time_model = TimeModel.from_calendar(window.calendar)
                course_name_map = {c.code: c.name for c in data["courses"] if c.name}
                # Regenerate groups so the viewer has full group info
                groups = []
                for c in data["courses"]:
                    groups.extend(c.generate_groups())
                # Re-attach assignments to groups
                for g in groups:
                    g.pinned = g.group_id in window.pinned_group_ids
                    g.lab_override = g.group_id in data.get("lab_overrides", set())
                    if g.group_id in window.current_schedule:
                        g.assignment = window.current_schedule[g.group_id]
                    else:
                        g.unassigned_reason = unassigned_reason(g, window._validation_classrooms(), time_model)
                errors = validate_schedule(window.current_schedule, groups,
                                           window._validation_classrooms(), time_model,
                                           data.get("lab_overrides", set()), resources=window.resources)
                if errors:
                    window.current_schedule = None
                    window.current_groups = None
                    raise ValueError("\n".join(error.render(msg) for error in errors))
                window.current_groups = groups
                window.schedule_viewer.display_schedule(
                    window.current_schedule, time_model, groups, course_name_map, classrooms=window._classrooms
                )
                window.export.refresh_actions()

            if not window._features.load_error and preferences != window._features.values():
                try:
                    window._features.save(preferences)
                except (OSError, ValueError) as error:
                    # Effective resource flags belong to this valid session;
                    # damaged/read-only optional UI preferences cannot erase them
                    # or prevent recovery of the user's schedule.
                    window._features.load_error = str(error)
            window._apply_feature_preferences()
            window._refresh_overview()
            window._loading = False
            window._unsaved = False
            window._save_error = None
            window.session.refresh_status()
            window.status_bar.showMessage(msg('✅ Sesión restaurada correctamente.'))
            window._reset_edit_history('restore')
            if window._restore_failed:
                window._restore_failed = False
                window._set_busy(False)
            if show_status and window.current_groups and len(window.current_schedule or {}) < len(window.current_groups):
                window._show_schedule_status()
        except Exception as e:
            window._loading = False
            window._restore_failed = True
            window.session.record_error(e)
            window.session.block_for_recovery()
