"""Bounded, session-local commands. Validate and persist before accepting state.

The caller owns rendering, never the history. Failed writes/validation do not move
stacks. Snapshots include all supplied fields so future constraints cannot be
silently dropped; an out-of-band mutation invalidates both branches explicitly.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json

from ..scheduling.time_model import TimeModel
from ..scheduling.validation import validate_schedule


class EditError(ValueError):
    def __init__(self, source, **parameters):
        super().__init__(source.format(**parameters))
        self.source, self.parameters = source, parameters

    def render(self, translate):
        return translate(self.source, **self.parameters)


def _canonical(value):
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (set, frozenset)):
        return sorted((_canonical(v) for v in value), key=str)
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if hasattr(value, 'to_data'):
        return _canonical(value.to_data())
    if hasattr(value, '__dict__'):
        return _canonical(vars(value))
    return value


def encoded(state):
    return json.dumps(_canonical(state), ensure_ascii=False, sort_keys=True).encode('utf-8')


def fingerprint(state):
    return hashlib.sha256(encoded(state)).hexdigest()


def validation_rooms(state):
    rooms = deepcopy(state['classrooms'])
    for name, room in rooms.items():
        room.allowed_courses = state['restrictions'].get(name)
    return rooms


def edit_time_model(state):
    calendar = state.get('calendar')
    return TimeModel.from_calendar(calendar) if calendar is not None else TimeModel.default()


def validate_edit(state):
    time_model = edit_time_model(state)
    courses = state['courses']
    codes = [course.code for course in courses]
    if any(not isinstance(code, str) or not code.strip() for code in codes) or len(set(codes)) != len(codes):
        raise EditError('Los códigos de curso deben ser únicos y no estar vacíos.')
    for c in courses:
        if (type(c.number_of_groups) is not int or c.number_of_groups < 1
                or type(c.duration_min) is not int or c.duration_min < 1
                or type(c.size) is not int or c.size < 0
                or c.required_room_type not in ('LAB', 'REGULAR')
                or c.preferred_day not in (None, *TimeModel.DAY_ORDER)):
            raise EditError('Datos de curso no válidos: {code}.', code=c.code)
    groups = [g for c in courses for g in c.generate_groups()]
    assignments = state['assignments'] or {}
    if not set(state.get('pinned_group_ids', ())).issubset(assignments):
        raise EditError('Las sesiones fijadas deben conservar una asignación válida.')
    if not set(state.get('lab_overrides', ())).issubset(assignments):
        raise EditError('Las excepciones LAB deben corresponder a sesiones asignadas.')
    extra = {'resources': state['resources']} if state.get('resources') is not None else {}
    errors = validate_schedule(assignments, groups, validation_rooms(state), time_model,
                               state.get('lab_overrides', ()), **extra)
    if errors:
        # Structured notices retain localization rather than leaking raw English.
        raise ScheduleEditError(errors)


class ScheduleEditError(EditError):
    def __init__(self, notices):
        self.notices = notices
        super().__init__('El cambio no es válido. Revise las asignaciones y las restricciones.')

    def render(self, translate):
        return '\n'.join(notice.render(translate) for notice in self.notices)


@dataclass(frozen=True)
class Command:
    label: str
    before: dict
    after: dict
    bytes: int


class EditHistory:
    MAX_COMMANDS = 50
    MAX_BYTES = 16 * 1024 * 1024

    def __init__(self, max_commands=MAX_COMMANDS, max_bytes=MAX_BYTES, validator=validate_edit):
        if max_commands < 1 or max_bytes < 1:
            raise ValueError('History limits must be positive')
        self.max_commands, self.max_bytes = max_commands, max_bytes
        self.validator = validator
        self._undo, self._redo = [], []
        self._expected = None
        self.reset_reason = None

    @property
    def can_undo(self):
        return bool(self._undo)

    @property
    def can_redo(self):
        return bool(self._redo)

    @property
    def bytes_used(self):
        return sum(c.bytes for c in self._undo + self._redo)

    def reset(self, state=None, reason='session'):
        self._undo.clear()
        self._redo.clear()
        self._expected = fingerprint(state) if state is not None else None
        self.reset_reason = reason

    def observe(self, state):
        actual = fingerprint(state)
        if self._expected is not None and self._expected != actual:
            self.reset(state, 'external_change')
            return True
        self._expected = actual
        return False

    def execute(self, before, after, persist, label, enabled=True):
        before, after = deepcopy(before), deepcopy(after)
        self.validator(after)
        if fingerprint(before) == fingerprint(after):
            return deepcopy(before)
        command = Command(label, before, after, len(encoded(before)) + len(encoded(after)))
        if enabled and command.bytes > self.max_bytes:
            raise EditError('El cambio supera el límite de memoria del historial. No se aplicó.')
        # No stack mutation, including redo invalidation, before a successful save.
        persist(deepcopy(after))
        self.observe(before)
        if enabled:
            self._redo.clear()
            self._undo.append(command)
            while len(self._undo) > self.max_commands or self.bytes_used > self.max_bytes:
                self._undo.pop(0)
            self._expected = fingerprint(after)
            self.reset_reason = None
        else:
            self.reset(after, 'feature_disabled_change')
        return deepcopy(after)

    def _travel(self, current, persist, undo):
        if self.observe(current):
            raise EditError('El historial se reinició por cambios fuera del historial.')
        source, destination = (self._undo, self._redo) if undo else (self._redo, self._undo)
        if not source:
            raise EditError('No hay cambios disponibles en el historial.')
        command = source[-1]
        target = deepcopy(command.before if undo else command.after)
        self.validator(target)
        persist(deepcopy(target))
        source.pop()
        destination.append(command)
        self._expected = fingerprint(target)
        return target

    def undo(self, current, persist):
        return self._travel(current, persist, True)

    def redo(self, current, persist):
        return self._travel(current, persist, False)


def course_change(state, courses):
    """Input edits preserve valid pins, explicitly invalidate other placements.

    Incompatible pins are rejected. Unpin is a separate explicit undoable action.
    """
    candidate = deepcopy(state)
    candidate['courses'] = deepcopy(courses)
    pins = set(candidate.get('pinned_group_ids', ()))
    candidate['assignments'] = {gid: value for gid, value in (state['assignments'] or {}).items() if gid in pins} or None
    candidate['lab_overrides'] = set(candidate.get('lab_overrides', ())) & pins
    candidate['schedule_present'] = bool(pins)
    if 'group_feedback' in candidate:
        candidate['group_feedback'] = {}
    old = {g.group_id: g for c in state['courses'] for g in c.generate_groups()}
    new = {g.group_id: g for c in courses for g in c.generate_groups()}
    for gid in pins:
        if gid not in new or gid not in old or (old[gid].parent_group_id, old[gid].total_subgroups, old[gid].subgroup_index) != (new[gid].parent_group_id, new[gid].total_subgroups, new[gid].subgroup_index):
            raise EditError('Desfije las sesiones afectadas antes de editar los cursos.')
    validate_edit(candidate)
    return candidate
