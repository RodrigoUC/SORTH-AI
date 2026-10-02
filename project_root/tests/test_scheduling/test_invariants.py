"""Reproducible mixed workloads exercise hard constraints independently of scores."""

import random

import pytest

from src.scheduling.classroom import Classroom
from src.scheduling.group import Group
from src.scheduling.schedule_state import ScheduleState
from src.scheduling.scheduler import Scheduler
from src.scheduling.time_model import TimeModel


@pytest.mark.parametrize("seed", range(12))
def test_mixed_schedules_preserve_hard_constraints(seed):
    rng = random.Random(seed)
    tm = TimeModel(["Lunes", "Martes", "Miércoles"], day_start=540, day_end=960)
    rooms = [Classroom(f"A{i}", capacity=15 + i * 10,
                       room_type="LAB" if i == 0 else "REGULAR")
             for i in range(4)]
    rooms[0].set_allowed_courses({"C0", "C1"})
    rooms[1].occupy(1, 540, 600)
    state = ScheduleState(tm, rooms)
    groups = [
        Group(f"G{i}", rng.choice([60, 90, 120]), rng.choice(["LAB", "REGULAR"]),
              size=rng.choice([10, 20, 30, 40, 50]), course_code=f"C{i % 4}",
              preferred_day=rng.choice([None, "Lunes", "Martes"]),
              preferred_start_min=rng.choice([None, 600, 720, 810]))
        for i in range(18)
    ]
    groups.extend(Group(f"SPLIT-P{i}", 90, "LAB", size=10, course_code="C0",
                        parent_group_id="SPLIT", subgroup_index=i, total_subgroups=3,
                        suggested_classroom="A0")
                  for i in range(1, 4))

    success = Scheduler(seed=seed).schedule(state, groups)

    assert success == all(group.is_assigned() for group in groups)
    assert len(state.assignments) == sum(group.is_assigned() for group in groups)
    for group in groups:
        if not group.is_assigned():
            assert group.group_id not in state.assignments
            continue
        room_name, day, start, end = group.assignment
        room = state.classrooms[room_name]
        assert state.assignments[group.group_id] == group.assignment
        assert room.capacity >= group.size
        assert room.allows_course(group.course_code)
        assert end - start == group.duration_min
        assert tm.is_valid_interval(day, start, end)
        assert not tm.overlaps_lunch(start, end)
        assert (start, end) in room.occupancy[day]
        if group.parent_group_id:
            assert room_name == "A0"  # its suggested room has a hard reservation

    for room in rooms:
        for intervals in room.occupancy.values():
            ordered = sorted(intervals)
            assert all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:]))

    parts = [group.assignment for group in groups
             if group.parent_group_id and group.is_assigned()]
    assert len({part[1] for part in parts}) == len(parts)
    assert len({part[2] for part in parts}) <= 1
