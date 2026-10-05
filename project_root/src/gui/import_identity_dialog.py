"""Explicit review of positional identities; never remap or mutate a candidate."""
from pathlib import Path

from PyQt6.QtWidgets import QVBoxLayout, QPlainTextEdit

from .i18n import msg
from .i18n_widgets import QDialog, QLabel, QDialogButtonBox
from .import_preview_dialog import display_value
from .resource_dialog import RESOURCE_TITLES
from ..scheduling.time_model import TimeModel


class ImportIdentityDialog(QDialog):
    def __init__(self, window, candidate, affected_ids):
        super().__init__(window)
        self._window, self._candidate = window, candidate
        self._affected_ids = tuple(affected_ids)
        self.setWindowTitle(msg('Revisar asociaciones del Excel'))
        self.resize(780, 560)
        layout = QVBoxLayout(self)
        label = QLabel(msg(
            'Hay cambios en cursos con varios grupos y asociaciones guardadas. G1, G2 y sus partes dependen del orden de las filas. SORTH no puede comprobar que sigan representando al mismo grupo.'))
        label.setWordWrap(True)
        layout.addWidget(label)
        consequence = QLabel(msg(
            'Al continuar, las asociaciones y fijaciones compatibles se conservan por identificador, sin reasignarlas a otras filas. Las eliminaciones y los conflictos se revisan después. Cancelar conserva todos los datos actuales.'))
        consequence.setWordWrap(True)
        layout.addWidget(consequence)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setTabChangesFocus(True)
        self.details.setAccessibleName(msg('Asociaciones que requieren revisión'))
        self.details.setPlainText(self.describe())
        layout.addWidget(self.details)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.buttons.setButtonText(QDialogButtonBox.StandardButton.Ok, msg('Continuar sin reasignar'))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.details.setFocus()

    @staticmethod
    def _group_description(group):
        return msg('Duración: {minutes} min; tipo: {room_type}; estudiantes: {size}; aula preferida: {room}; día preferido: {day}; inicio preferido: {time}.',
                   minutes=group.duration_min, room_type=group.required_room_type, size=group.size,
                   room=display_value('suggested_classroom', group.suggested_classroom),
                   day=display_value('preferred_day', group.preferred_day),
                   time=display_value('preferred_start_min', group.preferred_start_min))

    def describe(self):
        window = self._window
        old = {g.group_id: g for c in window.course_manager.get_courses() for g in c.generate_groups()}
        new = {g.group_id: g for c in self._candidate.imported.courses for g in c.generate_groups()}
        lines = [msg('Archivo: {name}', name=Path(self._candidate.path).name)]
        days = TimeModel.from_calendar(window.calendar).index_to_day
        catalogs = [(catalog, {resource.id: resource.label for resource in catalog.resources})
                    for catalog in window.resources.catalogs]
        for gid in self._affected_ids:
            lines.extend(('', gid,
                          msg('Antes: {details}', details=self._group_description(old[gid]))))
            if gid in new:
                lines.append(msg('Excel propuesto: {details}', details=self._group_description(new[gid])))
            else:
                lines.append(msg('Este identificador ya no aparece en el Excel propuesto.'))
            for catalog, labels in catalogs:
                ids = catalog.ids_for(gid)
                if not ids:
                    continue
                lines.append(msg('{kind} ({state}): {resources}',
                                 kind=msg(RESOURCE_TITLES[catalog.kind]),
                                 state=msg('Activo') if catalog.enabled else msg('Inactivo'),
                                 resources=', '.join(f'{labels.get(rid, rid)} [{rid}]' for rid in ids)))
            if gid in window.pinned_group_ids:
                placement = (window.current_schedule or {}).get(gid)
                if placement:
                    room, day, start, end = placement
                    lines.append(msg('Fijada: {room}, {day}, {start}–{end}', room=room,
                                     day=msg(days.get(day, str(day))),
                                     start=TimeModel.minutes_to_hhmm(start),
                                     end=TimeModel.minutes_to_hhmm(end)))
                else:
                    lines.append(msg('Sesión fijada'))
        return '\n'.join(map(str, lines))

    def retranslate(self):
        super().retranslate()
        if hasattr(self, 'details'):
            self.details.setAccessibleName(msg('Asociaciones que requieren revisión'))
            self.details.setPlainText(self.describe())
