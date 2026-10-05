"""Conservative review of positional identities when normalized courses change.

Course rows have no stable external identity: a saved relationship belongs to a
generated ordinal group ID. This detector requests review; it never establishes
row identity or proposes a remapping. In particular, permuting identical
normalized rows is unobservable and cannot be detected here.
"""
from collections.abc import Iterable

from ..scheduling.course import Course
from ..scheduling.group import Group
from ..scheduling.teaching_resources import SchedulingResources


def _meaningful_suggestions(course: Course) -> tuple:
    # Only the suggestions consumed by generate_groups are meaningful. Missing
    # rows and empty suggestions have the same normalized values. Retain the
    # distinction between an absent preference and an explicit one even when a
    # course-level fallback happens to make their generated groups look equal.
    return tuple(
        (suggestion.get('aula') or None,
         suggestion.get('preferred_day') or None,
         suggestion.get('preferred_start_min'))
        for suggestion in (
            course.group_suggestions[index]
            if index < len(course.group_suggestions) else {}
            for index in range(course.number_of_groups)
        )
    )


def _generated_properties(groups: list[Group]) -> tuple:
    # Compare the domain's effective values, including split structure. Neither
    # display names nor runtime placement state establish source-row identity.
    return tuple(
        (group.group_id, group.duration_min, group.required_room_type,
         group.size, group.suggested_classroom, group.preferred_day,
         group.preferred_start_min, group.parent_group_id,
         group.subgroup_index, group.total_subgroups)
        for group in groups
    )


def affected_identity_groups(
    old_courses: Iterable[Course],
    new_courses: Iterable[Course],
    resources: SchedulingResources,
    pinned_group_ids: Iterable[str],
) -> tuple[str, ...]:
    """Return linked old sessions of changed, shared repeated-code courses.

    A course is repeated when either version has multiple source groups, not
    merely multiple split parts. Changes to the count, ordered meaningful row
    suggestions or effective generated properties require review for *all* its
    saved memberships and pins, including disappearing sessions and inactive
    resource catalogs. Equal per-session properties cannot prove stable identity.

    Inputs are already normalized domain data and are never mutated. References
    are matched against actual generated IDs rather than parsing course codes.
    Entirely removed courses remain the responsibility of ordinary orphan/pin
    review. An empty result does not certify source-row identity.
    """
    linked_ids = set(pinned_group_ids)
    linked_ids.update(
        group_id
        for catalog in resources.catalogs
        for group_id, resource_ids in catalog.memberships
        if resource_ids
    )
    if not linked_ids:
        return ()

    old_by_code = {course.code: course for course in old_courses}
    new_by_code = {course.code: course for course in new_courses}
    affected = set()
    for code in old_by_code.keys() & new_by_code.keys():
        old, new = old_by_code[code], new_by_code[code]
        if old.number_of_groups <= 1 and new.number_of_groups <= 1:
            continue
        old_groups = old.generate_groups()
        linked_course_ids = linked_ids & {group.group_id for group in old_groups}
        if not linked_course_ids:
            continue
        if (old.number_of_groups != new.number_of_groups
                or _meaningful_suggestions(old) != _meaningful_suggestions(new)
                or _generated_properties(old_groups) != _generated_properties(new.generate_groups())):
            affected.update(linked_course_ids)
    return tuple(sorted(affected))
