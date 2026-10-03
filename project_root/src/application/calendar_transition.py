"""Pure preview: preserve weekday identity, never silently move or delete sessions."""
from dataclasses import dataclass, replace
from ..scheduling.time_model import TimeModel
from ..scheduling.validation import validate_schedule
from ..scheduling.teaching_resources import SchedulingResources


@dataclass(frozen=True)
class CalendarPreview:
    assignments: dict
    affected: tuple[str, ...]
    resources: SchedulingResources


def preview_calendar_change(old, new, assignments, groups, classrooms, lab_overrides=(), resources=None):
    previous, target = TimeModel.from_calendar(old), TimeModel.from_calendar(new)
    remapped, affected = {}, []
    for gid, (room, day, start, end) in (assignments or {}).items():
        name = previous.index_to_day.get(day)
        if name not in target.day_to_index:
            affected.append(gid)
            continue
        slot = (room, target.day_to_index[name], start, end)
        if not target.is_valid_interval(slot[1], start, end) or target.overlaps_lunch(start, end):
            affected.append(gid)
        else:
            remapped[gid] = slot
    catalogs = []
    for catalog in (resources or SchedulingResources()).catalogs:
        entries = []
        for resource in catalog.resources:
            availability = resource.availability
            if availability is not None:
                windows = []
                for day, start, end in availability:
                    name = previous.index_to_day.get(day)
                    if name not in target.day_to_index:
                        raise ValueError('Resource availability references a removed teaching day; edit it explicitly first')
                    windows.append((target.day_to_index[name], start, end))
                availability = tuple(windows)
            entries.append(replace(resource, availability=availability))
        catalogs.append(replace(catalog, resources=tuple(entries)))
    remapped_resources = SchedulingResources(tuple(catalogs))
    errors = validate_schedule(remapped, groups, classrooms, target, lab_overrides, remapped_resources)
    if errors:
        raise ValueError('; '.join(str(error) for error in errors))
    return CalendarPreview(remapped, tuple(sorted(affected)), remapped_resources)
