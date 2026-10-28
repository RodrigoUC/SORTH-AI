"""Derive classroom suggestions from the accepted courses, independently of files."""
from collections.abc import Iterable

from .cancellation import checkpoint
from .course import Course


def classroom_course_map(courses: Iterable[Course], known_classrooms: set[str], *, cancelled=None):
    """Return each known room's explicitly suggested courses in source order.

    Per-group suggestions take precedence over course defaults. Empty row
    suggestions do not create a new room restriction through a course fallback.
    """
    result: dict[str, list[str]] = {}
    for course in courses:
        checkpoint(cancelled)
        suggestions = course.group_suggestions or [{'aula': course.suggested_classroom}]
        for suggestion in suggestions:
            checkpoint(cancelled)
            room = suggestion.get('aula')
            if room in known_classrooms:
                codes = result.setdefault(room, [])
                if course.code not in codes:
                    codes.append(course.code)
    return result
