import pytest

from benchmark import benchmark_excel, run_once, validate_schedule
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


def test_benchmark_uses_fresh_objects_for_each_run():
    classrooms = {"A1": Classroom("A1", 30, "REGULAR")}
    courses = [Course("BIO", 2, 60, "REGULAR", size=10)]
    first_elapsed, first, first_groups = run_once(classrooms, courses)
    second_elapsed, second, second_groups = run_once(classrooms, courses)

    assert first_elapsed >= 0
    assert second_elapsed >= 0
    assert first.assignments == second.assignments
    assert len(first.assignments) == 2
    assert first_groups[0] is not second_groups[0]
    assert not classrooms["A1"].occupancy


def test_benchmark_rejects_zero_repeats_before_loading_input():
    with pytest.raises(ValueError, match="repeats"):
        benchmark_excel("does-not-exist.xlsx", repeats=0)


def test_benchmark_validation_detects_an_overlapping_reservation():
    classrooms = {"A1": Classroom("A1", 30, "REGULAR")}
    courses = [Course("BIO", 1, 60, "REGULAR", size=10)]
    _, state, groups = run_once(classrooms, courses)
    room, day, start, end = groups[0].assignment
    state.classrooms[room].occupy(day, start, end)

    with pytest.raises(AssertionError):
        validate_schedule(state, groups)
