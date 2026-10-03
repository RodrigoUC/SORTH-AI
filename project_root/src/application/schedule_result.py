"""Validate result population without trusting a scheduler's group metadata."""

# These are request-derived fields. Solver state (domain, assignment, pin/LAB
# flags and pending feedback) may legitimately change while scheduling.
_GROUP_FIELDS = ('group_id', 'duration_min', 'required_room_type', 'size',
                 'suggested_classroom', 'course_code', 'preferred_start_min',
                 'preferred_day', 'course_name', 'parent_group_id',
                 'subgroup_index', 'total_subgroups')
_MISSING = object()


def matches_requested_groups(groups, expected_groups, *, ordered=False):
    """Require every requested group exactly once, with unchanged metadata.

    GUI results may be reordered. Preview ports retain their existing ordered
    contract by opting in. Callers build expected groups independently of the
    solver, from their authoritative request; mutable result state is excluded.
    """
    if not isinstance(groups, list) or len(groups) != len(expected_groups):
        return False
    actual = [tuple(getattr(group, field, _MISSING) for field in _GROUP_FIELDS)
              for group in groups]
    expected = [tuple(getattr(group, field, _MISSING) for field in _GROUP_FIELDS)
                for group in expected_groups]
    if any(not isinstance(signature[0], str) for signature in actual + expected):
        return False
    actual_by_id = {signature[0]: signature for signature in actual}
    expected_by_id = {signature[0]: signature for signature in expected}
    if len(actual_by_id) != len(actual) or len(expected_by_id) != len(expected):
        return False
    return actual == expected if ordered else actual_by_id == expected_by_id
