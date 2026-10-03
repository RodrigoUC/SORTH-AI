from copy import deepcopy

import pytest

from src.application.scheduling_service import SchedulingService
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.validation import validate_schedule
from src.scheduling.time_model import TimeModel


def run(courses, pins, seed=42, rooms=None, **kwargs):
    return SchedulingService(None, seed).run(courses=courses,
        classrooms=rooms if rooms is not None else {'R': Classroom('R', 30, 'REGULAR')},
        pinned_assignments=pins, **kwargs)


@pytest.mark.parametrize('seed', [None, 0, 42, 999])
def test_pins_survive_repeated_regeneration_and_seed_changes(seed):
    courses = [Course('BIO', 4, 60, 'REGULAR')]
    pins = {'BIO-G2': ('R', 3, 600, 660)}
    for _ in range(3):
        result, groups = run(courses, pins, seed)
        assert result['BIO-G2'] == pins['BIO-G2']
        assert next(g for g in groups if g.group_id == 'BIO-G2').pinned
        assert len(result) == 4
        assert not validate_schedule(result, groups, {'R': Classroom('R', 30, 'REGULAR')}, TimeModel.default())
    result, groups = run(courses, {})
    assert not any(g.pinned for g in groups)


@pytest.mark.parametrize('pins', [
    {'BIO-G1': ('R', 1, 480, 540), 'BIO-G2': ('R', 1, 510, 570)},
    {'REMOVED-G1': ('R', 1, 480, 540)},
    {'BIO-G1': ('REMOVED', 1, 480, 540)},
    {'BIO-G1': ('R', 1, 480, 600)},
    {'BIO-G1': ('R', 1, 720, 780)},
])
def test_invalid_pins_fail_atomically(pins):
    courses = [Course('BIO', 2, 60, 'REGULAR')]
    rooms = {'R': Classroom('R', 30, 'REGULAR')}
    before = deepcopy(pins)
    with pytest.raises(ValueError):
        run(courses, pins, rooms=rooms)
    assert pins == before
    assert rooms['R'].occupancy == {}


def test_restriction_capacity_and_lab_are_not_bypassed():
    pins = {'BIO-G1': ('R', 1, 480, 540)}
    with pytest.raises(ValueError):
        run([Course('BIO', 1, 60, 'REGULAR', size=40)], pins)
    with pytest.raises(ValueError):
        run([Course('BIO', 1, 60, 'REGULAR')], pins, classroom_restrictions={'R': {'OTHER'}})
    with pytest.raises(ValueError):
        run([Course('BIO', 1, 60, 'LAB')], pins)
    assignments, groups = run([Course('BIO', 2, 60, 'LAB')], pins, lab_overrides={'BIO-G1'})
    assert assignments == pins  # another LAB never inherits the exception
    assert groups[0].lab_override and groups[0].pinned
    assert not groups[1].is_assigned() and not groups[1].lab_override


def test_partial_split_pins_reserve_day_and_time_for_remaining_parts():
    pins = {'BIO-G1-P1': ('R', 2, 480, 600)}
    assignments, groups = run([Course('BIO', 1, 360, 'REGULAR')], pins)
    assert assignments['BIO-G1-P1'] == pins['BIO-G1-P1']
    assert len(assignments) == 3
    assert len({p[1] for p in assignments.values()}) == 3
    assert {p[2] for p in assignments.values()} == {480}
    with pytest.raises(ValueError):
        run([Course('BIO', 1, 360, 'REGULAR')],
            {**pins, 'BIO-G1-P2': ('R', 3, 600, 720)})
