from src.scheduling.time_model import TimeModel
from src.scheduling.classroom import Classroom
from src.scheduling.schedule_state import ScheduleState
from src.scheduling.group import Group


def _make_state():
    tm = TimeModel(["Lunes", "Martes"])
    classroom = Classroom("A1", capacity=30, room_type="REGULAR")
    return ScheduleState(tm, [classroom]), tm


def test_assign_and_unassign():
    state, tm = _make_state()
    group = Group("G1", duration_min=120, required_room_type="REGULAR", size=20)

    day = tm.to_day_index("Lunes")
    assert state.assign(group, "A1", day, 480)   # 08:00-10:00
    assert group.is_assigned()
    assert group.assignment == ("A1", day, 480, 600)

    state.unassign(group)
    assert not group.is_assigned()
    assert "G1" not in state.assignments


def test_assign_fails_on_overlap():
    state, tm = _make_state()
    g1 = Group("G1", duration_min=120, required_room_type="REGULAR", size=20)
    g2 = Group("G2", duration_min=120, required_room_type="REGULAR", size=20)

    day = tm.to_day_index("Lunes")
    assert state.assign(g1, "A1", day, 480)
    assert not state.assign(g2, "A1", day, 480)   # same slot → conflict


def test_lab_requires_explicit_manual_override():
    state, tm = _make_state()
    group = Group("G1", duration_min=60, required_room_type="LAB", size=10)
    day = tm.to_day_index("Lunes")
    assert not state.assign(group, "A1", day, 480)
    assert state.assign(group, "A1", day, 480, allow_lab_override=True)
    assert group.lab_override


def test_assign_fails_capacity():
    state, tm = _make_state()
    group = Group("G1", duration_min=60, required_room_type="REGULAR", size=50)
    day = tm.to_day_index("Lunes")
    assert not state.assign(group, "A1", day, 480)


def test_assign_fails_overlaps_lunch():
    state, tm = _make_state()
    group = Group("G1", duration_min=120, required_room_type="REGULAR", size=10)
    day = tm.to_day_index("Lunes")
    # 11:30-13:30 overlaps lunch (12:00-13:00)
    assert not state.assign(group, "A1", day, 690)



def test_reassign_rejected_without_leaking_room_occupancy():
    state, _ = _make_state()
    group = Group("G1", duration_min=60, required_room_type="REGULAR", size=10)
    assert state.assign(group, "A1", 1, 480)

    assert not state.assign(group, "A1", 2, 600)
    assert state.assignments == {"G1": ("A1", 1, 480, 540)}
    assert group.assignment == state.assignments["G1"]
    assert state.classrooms["A1"].is_available(2, 600, 660)

    state.unassign(group)
    assert state.classrooms["A1"].is_available(1, 480, 540)
    assert not state.assignments


def test_duplicate_group_id_cannot_overwrite_an_assignment():
    state, _ = _make_state()
    original = Group("G1", duration_min=60, required_room_type="REGULAR", size=10)
    duplicate = Group("G1", duration_min=60, required_room_type="REGULAR", size=10)
    assert state.assign(original, "A1", 1, 480)

    assert not state.assign(duplicate, "A1", 2, 480)
    assert not duplicate.is_assigned()
    assert state.assignments["G1"] == original.assignment
    assert state.classrooms["A1"].is_available(2, 480, 540)


def test_group_assigned_in_another_state_cannot_be_assigned_again():
    first, _ = _make_state()
    second, _ = _make_state()
    group = Group("G1", duration_min=60, required_room_type="REGULAR", size=10)
    assert first.assign(group, "A1", 1, 480)

    assert not second.assign(group, "A1", 2, 480)
    assert not second.assignments
    assert group.assignment == first.assignments["G1"]


def test_restricted_room_rejects_missing_course_code():
    state, _ = _make_state()
    state.classrooms["A1"].set_allowed_courses({"BIO"})
    group = Group("G1", duration_min=60, required_room_type="REGULAR", size=10)

    assert not state.assign(group, "A1", 1, 480)
    assert not group.is_assigned()
    assert not state.classrooms["A1"].occupancy


def test_restricted_room_allows_only_listed_courses():
    state, _ = _make_state()
    state.classrooms["A1"].set_allowed_courses({"BIO"})
    allowed = Group("G1", 60, "REGULAR", course_code="BIO")
    rejected = Group("G2", 60, "REGULAR", course_code="CHEM")

    assert state.assign(allowed, "A1", 1, 480)
    assert not state.assign(rejected, "A1", 2, 480)
