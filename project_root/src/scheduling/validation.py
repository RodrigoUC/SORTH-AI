"""Independent checks for generated, restored and manually edited results."""

class ValidationNotice(str):
    """Rendered default text with a stable source/parameters for GUI translation."""

    def __new__(cls, source, **parameters):
        value = super().__new__(cls, source.format(**parameters))
        value.source = source
        value.parameters = parameters
        return value

    def render(self, translate):
        return translate(self.source, **self.parameters)


def validate_schedule(assignments, groups, classrooms, time_model, lab_overrides=(), resources=None):
    errors = []
    known = {}
    for group in groups:
        if group.group_id in known:
            errors.append(ValidationNotice("{gid}: identificador de grupo duplicado", gid=group.group_id))
        known[group.group_id] = group
    occupied = {}
    split = {}
    for gid, placement in assignments.items():
        # Reject corrupt/restored/plugin results as notices, before arithmetic or
        # rendering can throw. bool is deliberately not accepted as an integer.
        if (not isinstance(placement, (tuple, list)) or len(placement) != 4
                or not isinstance(placement[0], str)
                or any(type(value) is not int for value in placement[1:])):
            errors.append(ValidationNotice("{gid}: asignación mal formada", gid=gid))
            continue
        room, day, start, end = placement
        group, classroom = known.get(gid), classrooms.get(room)
        if group is None or classroom is None:
            errors.append(ValidationNotice("{gid}: grupo o aula desconocido", gid=gid))
            continue
        if end - start != group.duration_min:
            errors.append(ValidationNotice("{gid}: duración incorrecta", gid=gid))
        if not time_model.is_valid_interval(day, start, end) or time_model.overlaps_lunch(start, end):
            errors.append(ValidationNotice("{gid}: horario fuera del intervalo permitido", gid=gid))
        if classroom.capacity < group.size:
            errors.append(ValidationNotice("{gid}: capacidad insuficiente", gid=gid))
        if group.required_room_type == 'LAB' and classroom.room_type != 'LAB' and gid not in lab_overrides:
            errors.append(ValidationNotice("{gid}: requiere laboratorio; falta confirmar la excepción manual", gid=gid))
        reserved = {c.name for c in classrooms.values()
                    if c.allowed_courses is not None and group.course_code in c.allowed_courses}
        if not classroom.allows_course(group.course_code) or (
                group.suggested_classroom in reserved and room not in reserved):
            errors.append(ValidationNotice("{gid}: restricción de aula", gid=gid))
        for other_start, other_end in occupied.setdefault((room, day), []):
            if start < other_end and end > other_start:
                errors.append(ValidationNotice("{gid}: conflicto de aula", gid=gid))
        occupied[(room, day)].append((start, end))
        if group.parent_group_id:
            for other_day, other_start in split.setdefault(group.parent_group_id, []):
                if day == other_day or start != other_start:
                    errors.append(ValidationNotice("{gid}: sesiones divididas deben usar días distintos y la misma hora", gid=gid))
            split[group.parent_group_id].append((day, start))
    if resources is not None:
        errors.extend(resources.validate(assignments, groups, time_model))
    return errors


def unassigned_reason(group, classrooms, time_model):
    rooms = list(classrooms.values())
    if group.required_room_type == 'LAB':
        rooms = [c for c in rooms if c.room_type == 'LAB']
        if not rooms:
            return 'No hay laboratorios configurados. Puede elegir un aula regular manualmente y confirmar la excepción.'
    rooms = [c for c in rooms if c.capacity >= group.size]
    if not rooms:
        return 'Ningún aula del tipo permitido tiene capacidad suficiente.'
    reserved = {c.name for c in classrooms.values()
                if c.allowed_courses is not None and group.course_code in c.allowed_courses}
    rooms = [c for c in rooms if c.allows_course(group.course_code)
             and (group.suggested_classroom not in reserved or c.name in reserved)]
    if not rooms:
        return 'Las restricciones de cursos excluyen todas las aulas compatibles.'
    # A coarse search grid is not a feasibility proof. Check continuous free
    # intervals, including off-grid break endpoints, before claiming no fit.
    cursor = time_model.day_start
    longest = 0
    for start, end in sorted(time_model.breaks):
        # Low-level TimeModel callers may retain the default lunch outside a
        # shortened day; those exclusions cannot enlarge its teaching window.
        start = min(time_model.day_end, max(time_model.day_start, start))
        end = min(time_model.day_end, max(time_model.day_start, end))
        longest = max(longest, start - cursor)
        cursor = max(cursor, end)
    longest = max(longest, time_model.day_end - cursor)
    if group.duration_min > longest:
        return 'La duración no cabe en el horario permitido sin cruzar los descansos.'
    return ('La búsqueda automática no encontró un horario compatible con las asignaciones actuales. '
            'Esto no demuestra que sea imposible; revise horarios, restricciones o asigne manualmente.')
