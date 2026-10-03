"""Import comparison of normalized domain inputs, independent of presentation."""
from dataclasses import dataclass

COURSE_FIELDS = ('name', 'number_of_groups', 'duration_min', 'required_room_type',
                 'size', 'suggested_classroom', 'preferred_day', 'preferred_start_min',
                 'group_suggestions', 'force_split')
ROOM_FIELDS = ('capacity', 'room_type', 'description', 'campus')


@dataclass(frozen=True)
class EntityDifference:
    added: tuple
    removed: tuple
    # Identity -> changed field names. Runtime occupancy is deliberately excluded.
    changed: dict


def compare_entities(old, new, fields):
    return EntityDifference(
        tuple(sorted(new.keys() - old.keys())),
        tuple(sorted(old.keys() - new.keys())),
        {key: tuple(field for field in fields if getattr(old[key], field) != getattr(new[key], field))
         for key in sorted(old.keys() & new.keys())
         if any(getattr(old[key], field) != getattr(new[key], field) for field in fields)},
    )


def import_difference(courses, classrooms, candidate):
    return (
        compare_entities({c.code: c for c in courses}, {c.code: c for c in candidate.courses}, COURSE_FIELDS),
        compare_entities(classrooms, candidate.classrooms, ROOM_FIELDS),
    )
