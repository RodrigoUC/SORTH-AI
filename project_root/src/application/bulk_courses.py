"""Explicit-field, identity-preserving bulk course previews and atomic commands."""
from copy import deepcopy
from dataclasses import dataclass
from .edit_history import EditError, course_change, fingerprint
from ..scheduling.time_model import TimeModel

ALLOWED_FIELDS = frozenset(('required_room_type', 'size', 'preferred_day'))


@dataclass(frozen=True)
class BulkPlan:
    revision: str
    selected_codes: tuple[str, ...]
    fields: tuple[tuple[str, object], ...]
    changes: tuple[tuple[str, str, object, object], ...]
    removed_assignments: tuple[str, ...]
    preserved_pins: tuple[str, ...]
    candidate: dict


def preview_bulk(state, selected_codes, fields):
    selected_codes = tuple(selected_codes)
    if not selected_codes or len(set(selected_codes)) != len(selected_codes):
        raise EditError('Seleccione al menos un curso; no repita identificadores.')
    if not fields or not set(fields).issubset(ALLOWED_FIELDS):
        raise EditError('Marque los campos que desea cambiar. Los códigos no se pueden editar en lote.')
    if 'size' in fields and (type(fields['size']) is not int or not 0 <= fields['size'] <= 100000):
        raise EditError('El tamaño debe ser un entero entre 0 y 100000.')
    if 'required_room_type' in fields and fields['required_room_type'] not in ('REGULAR', 'LAB'):
        raise EditError('Seleccione un tipo de aula válido.')
    if 'preferred_day' in fields and fields['preferred_day'] not in (None, *TimeModel.DAY_ORDER):
        raise EditError('Seleccione un día válido o borre la preferencia explícitamente.')
    known = {c.code for c in state['courses']}
    if not set(selected_codes).issubset(known):
        raise EditError('La selección cambió. Cierre y vuelva a seleccionar los cursos.')
    courses = deepcopy(state['courses'])
    changes = []
    for course in courses:
        if course.code in selected_codes:
            for field, value in fields.items():
                previous = getattr(course, field)
                if previous != value:
                    changes.append((course.code, field, previous, value))
                setattr(course, field, value)
    if not changes:
        raise EditError('Los valores elegidos no cambian ningún curso.')
    candidate = course_change(state, courses)
    removed = tuple(sorted(set(state['assignments'] or {}) - set(candidate['assignments'] or {})))
    return BulkPlan(fingerprint(state), selected_codes, tuple(sorted(fields.items())), tuple(changes), removed,
                    tuple(sorted(state.get('pinned_group_ids', ()))), candidate)


def apply_bulk(history, state, plan, selected_codes, persist, enabled):
    if not enabled:
        raise EditError('Active Deshacer y rehacer en Configuración antes de editar en lote.')
    if fingerprint(state) != plan.revision or tuple(selected_codes) != plan.selected_codes:
        raise EditError('La sesión o selección cambió desde la revisión. Vuelva a revisar el lote.')
    # Revalidate the complete candidate at execution, never trust preview alone.
    refreshed = preview_bulk(state, selected_codes, dict(plan.fields))
    return history.execute(state, refreshed.candidate, persist, 'Editar cursos en lote', enabled=True)
