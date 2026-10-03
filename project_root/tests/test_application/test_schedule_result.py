from copy import deepcopy

import pytest

from src.application.schedule_result import matches_requested_groups
from src.scheduling.course import Course


def test_population_order_is_optional_but_preview_can_preserve_its_contract():
    expected = Course('C', 2, 60, 'REGULAR').generate_groups()
    assert matches_requested_groups(list(reversed(expected)), expected)
    assert not matches_requested_groups(list(reversed(expected)), expected, ordered=True)
    assert matches_requested_groups(deepcopy(expected), expected, ordered=True)


@pytest.mark.parametrize('field', ['group_id', 'duration_min', 'required_room_type', 'size',
    'suggested_classroom', 'course_code', 'preferred_start_min', 'preferred_day',
    'course_name', 'parent_group_id', 'subgroup_index', 'total_subgroups'])
def test_every_immutable_field_must_match(field):
    expected = Course('C', 2, 300, 'REGULAR').generate_groups()
    actual = deepcopy(expected)
    setattr(actual[-1], field, 'changed')
    assert not matches_requested_groups(actual, expected)


def test_mutable_solver_state_is_not_request_metadata():
    expected = Course('C', 1, 60, 'LAB').generate_groups()
    actual = deepcopy(expected)
    actual[0].domain = [('R', 1, 480)]
    actual[0].assignment = ('R', 1, 480, 540)
    actual[0].lab_override = actual[0].pinned = True
    actual[0].unassigned_reason = 'result feedback'
    assert matches_requested_groups(actual, expected)


def test_duplicate_authoritative_ids_fail_closed():
    expected = Course('C', 1, 60, 'LAB').generate_groups() * 2
    assert not matches_requested_groups(deepcopy(expected), expected)
