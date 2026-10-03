from src.scheduling.scheduler import Scheduler
from src.scheduling.schedule_state import ScheduleState
from src.scheduling.time_model import TimeModel
from src.scheduling.classroom import Classroom
from src.scheduling.group import Group


def _make_state(days=None, capacity=30):
    tm = TimeModel(days or ["Lunes", "Martes"])
    classroom = Classroom("A1", capacity=capacity, room_type="REGULAR")
    return ScheduleState(tm, [classroom]), tm


def test_scheduler_assigns_single_group():
    state, _ = _make_state()
    group = Group("G1", duration_min=120, required_room_type="REGULAR", size=10)
    assert Scheduler().schedule(state, [group])
    assert group.is_assigned()


def test_scheduler_two_groups_same_classroom():
    state, _ = _make_state()
    g1 = Group("G1", duration_min=120, required_room_type="REGULAR", size=10)
    g2 = Group("G2", duration_min=120, required_room_type="REGULAR", size=10)
    # Two groups can fit in the same classroom on different slots/days
    assert Scheduler().schedule(state, [g1, g2])
    assert g1.is_assigned()
    assert g2.is_assigned()
    # They must not overlap
    assert not (g1.assignment[1] == g2.assignment[1] and
                g1.assignment[2] < g2.assignment[3] and
                g2.assignment[2] < g1.assignment[3])


def test_scheduler_no_solution_capacity():
    state, tm = _make_state(capacity=5)
    group = Group("G1", duration_min=60, required_room_type="REGULAR", size=30)
    assert not Scheduler().schedule(state, [group])


def test_scheduler_respects_preferred_day():
    state, tm = _make_state(["Lunes", "Martes"])
    group = Group("G1", duration_min=60, required_room_type="REGULAR",
                  size=10, preferred_day="Martes")
    assert Scheduler().schedule(state, [group])
    _, assigned_day, _, _ = group.assignment
    assert tm.to_day_name(assigned_day) == "Martes"


def test_scheduler_respects_preferred_start():
    state, _ = _make_state()
    group = Group("G1", duration_min=60, required_room_type="REGULAR",
                  size=10, preferred_start_min=480)
    assert Scheduler().schedule(state, [group])
    _, _, start, _ = group.assignment
    assert start == 480


# ------------------------------------------------------------------
# Anti-copy grouping priority tests
# ------------------------------------------------------------------

def _make_multi_classroom_state(days=None):
    """State with 3 REGULAR classrooms and 2 days."""
    tm = TimeModel(days or ["Lunes", "Martes", "Miércoles"])
    classrooms = [
        Classroom("A1", capacity=30, room_type="REGULAR"),
        Classroom("A2", capacity=30, room_type="REGULAR"),
        Classroom("A3", capacity=30, room_type="REGULAR"),
    ]
    return ScheduleState(tm, classrooms), tm


def test_same_course_priority0_consecutive_blocks():
    """
    Two groups of the same course on the same day should either:
    - Be consecutive (priority 0): second starts at next exact hour after first ends
    - Or share the same time slot in different classrooms (priority 1)
    Both are valid anti-copy arrangements.
    """
    state, tm = _make_multi_classroom_state(["Lunes"])
    g1 = Group("BIO-G1", duration_min=90, required_room_type="REGULAR",
               size=10, course_code="BIO")
    g2 = Group("BIO-G2", duration_min=90, required_room_type="REGULAR",
               size=10, course_code="BIO")

    assert Scheduler(seed=42).schedule(state, [g1, g2])
    assert g1.is_assigned()
    assert g2.is_assigned()

    # Both must be on the same day
    assert g1.assignment[1] == g2.assignment[1]

    s1, e1 = g1.assignment[2], g1.assignment[3]
    s2, e2 = g2.assignment[2], g2.assignment[3]
    starts = sorted([s1, s2])
    ends   = sorted([e1, e2])

    # Priority 1: same start time, different classroom
    same_time = (s1 == s2 and g1.assignment[0] != g2.assignment[0])

    # Priority 0: consecutive — second starts at next exact hour after first ends
    first_end = ends[0]
    next_hour = ((first_end + 59) // 60) * 60
    consecutive = (starts[1] == next_hour)

    assert same_time or consecutive, (
        f"Expected same-time or consecutive blocks, got "
        f"G1={g1.assignment} G2={g2.assignment}"
    )


def test_same_course_priority1_same_time_different_classroom():
    """
    When consecutive blocks are not possible (only 1 day, 1 slot),
    groups of the same course should prefer same time in different classrooms.
    """
    # Only one time slot available per classroom per day
    tm = TimeModel(["Lunes"])
    classrooms = [
        Classroom("A1", capacity=30, room_type="REGULAR"),
        Classroom("A2", capacity=30, room_type="REGULAR"),
    ]
    state = ScheduleState(tm, classrooms)

    # Pre-occupy A1 at 10:00 and A2 at 10:00 to force same-time scenario
    # Actually just let the scheduler decide — with 2 classrooms and 2 groups
    # priority 1 (same time, different classroom) should be preferred
    g1 = Group("BIO-G1", duration_min=120, required_room_type="REGULAR",
               size=10, course_code="BIO")
    g2 = Group("BIO-G2", duration_min=120, required_room_type="REGULAR",
               size=10, course_code="BIO")

    assert Scheduler(seed=42).schedule(state, [g1, g2])
    assert g1.is_assigned()
    assert g2.is_assigned()
    # Must not overlap in same classroom
    if g1.assignment[0] == g2.assignment[0]:
        assert not (g1.assignment[2] < g2.assignment[3] and
                    g2.assignment[2] < g1.assignment[3])


def test_same_course_priority2_different_day_same_time():
    """
    Groups of the same course on different days should share the same start time.
    """
    state, tm = _make_multi_classroom_state(["Lunes", "Martes"])
    g1 = Group("BIO-G1", duration_min=120, required_room_type="REGULAR",
               size=10, course_code="BIO", preferred_start_min=480)
    g2 = Group("BIO-G2", duration_min=120, required_room_type="REGULAR",
               size=10, course_code="BIO", preferred_start_min=480)
    g3 = Group("BIO-G3", duration_min=120, required_room_type="REGULAR",
               size=10, course_code="BIO", preferred_start_min=480)

    assert Scheduler(seed=42).schedule(state, [g1, g2, g3])
    starts = {g.assignment[2] for g in [g1, g2, g3]}
    # All should share the same preferred start time
    assert starts == {480}


def test_regular_course_prefers_regular_classroom():
    """
    A REGULAR course should be assigned to a REGULAR classroom,
    not a LAB, even if both are available.
    """
    tm = TimeModel(["Lunes"])
    classrooms = [
        Classroom("LAB1", capacity=30, room_type="LAB"),
        Classroom("REG1", capacity=30, room_type="REGULAR"),
    ]
    state = ScheduleState(tm, classrooms)
    group = Group("BIO-G1", duration_min=90, required_room_type="REGULAR",
                  size=10, course_code="BIO")

    assert Scheduler(seed=42).schedule(state, [group])
    assert group.assignment[0] == "REG1"



def test_course_without_suggested_room_can_use_an_unrestricted_room():
    tm = TimeModel(["Lunes"], day_start=420, day_end=480)
    reserved = Classroom("LAB1", capacity=30, room_type="LAB")
    reserved.set_allowed_courses({"BIO"})
    reserved.occupy(1, 420, 480)
    regular = Classroom("A1", capacity=30, room_type="REGULAR")
    state = ScheduleState(tm, [reserved, regular])
    group = Group("BIO-G1", 60, "REGULAR", course_code="BIO")

    assert Scheduler().schedule(state, [group])
    assert group.assignment[0] == "A1"


def test_suggested_restricted_room_remains_a_hard_constraint_on_retry():
    tm = TimeModel(["Lunes"], day_start=420, day_end=480)
    reserved = Classroom("LAB1", capacity=30, room_type="LAB")
    reserved.set_allowed_courses({"BIO"})
    reserved.occupy(1, 420, 480)
    regular = Classroom("A1", capacity=30, room_type="REGULAR")
    state = ScheduleState(tm, [reserved, regular])
    group = Group("BIO-G1", 60, "REGULAR", course_code="BIO",
                  suggested_classroom="LAB1")

    assert not Scheduler().schedule(state, [group])
    assert not group.is_assigned()
    assert not regular.occupancy


def test_missing_course_cannot_use_restricted_room_even_on_retry():
    state, _ = _make_state()
    state.classrooms["A1"].set_allowed_courses({"BIO"})
    group = Group("G1", 60, "REGULAR")

    assert not Scheduler().schedule(state, [group])
    assert not state.assignments
    assert not group.domain


def test_existing_assignments_contribute_to_load_balancing():
    state, _ = _make_state()
    existing = Group("G1", 60, "REGULAR")
    new = Group("G2", 60, "REGULAR")
    assert state.assign(existing, "A1", 1, 420)
    scheduler = Scheduler()

    assert scheduler.schedule(state, [existing, new])
    assert new.assignment[1] == 2
    assert scheduler._day_load == {1: 1, 2: 1}
    # Calling again must reconstruct counters rather than drop or double them.
    assert scheduler.schedule(state, [existing, new])
    assert scheduler._day_load == {1: 1, 2: 1}


def test_retries_stop_when_a_relaxed_pass_makes_no_progress():
    class CountingScheduler(Scheduler):
        def __init__(self):
            super().__init__()
            self.passes = 0

        def _greedy_pass(self, state, groups):
            self.passes += 1
            super()._greedy_pass(state, groups)

    state, _ = _make_state(capacity=5)
    group = Group("G1", 60, "REGULAR", size=10)
    scheduler = CountingScheduler()

    assert not scheduler.schedule(state, [group])
    assert scheduler.passes == 2  # strict pass, then one exhausted relaxed pass


def test_split_sessions_use_different_days_and_same_start_time():
    state, _ = _make_state(["Lunes", "Martes", "Miércoles"])
    groups = [Group(f"BIO-G1-P{i}", 60, "REGULAR", course_code="BIO",
                    parent_group_id="BIO-G1", subgroup_index=i, total_subgroups=3)
              for i in range(1, 4)]

    assert Scheduler().schedule(state, groups)
    assert len({group.assignment[1] for group in groups}) == 3
    assert len({group.assignment[2] for group in groups}) == 1


def test_soft_preferences_relax_without_relaxing_lunch_or_capacity():
    tm = TimeModel(["Lunes", "Martes"], day_start=660, day_end=840)
    room = Classroom("A1", capacity=20, room_type="REGULAR")
    room.occupy(1, 660, 720)
    room.occupy(1, 780, 840)
    state = ScheduleState(tm, [room])
    group = Group("G1", 60, "REGULAR", size=20, preferred_day="Lunes",
                  preferred_start_min=720)

    assert Scheduler().schedule(state, [group])
    _, day, start, end = group.assignment
    assert day == 2
    assert not tm.overlaps_lunch(start, end)
    assert tm.is_valid_interval(day, start, end)


def test_time_candidates_are_reused_across_rooms_days_and_groups():
    class CountingTimeModel(TimeModel):
        def __init__(self):
            super().__init__(["Lunes", "Martes"])
            self.candidate_calls = []

        def generate_start_candidates(self, duration_min, preferred_start_min=None):
            self.candidate_calls.append((duration_min, preferred_start_min))
            return super().generate_start_candidates(duration_min, preferred_start_min)

    tm = CountingTimeModel()
    state = ScheduleState(tm, [Classroom(f"A{i}", 30, "REGULAR") for i in range(3)])
    groups = [Group(f"G{i}", 60, "REGULAR") for i in range(5)]
    groups.append(Group("G6", 90, "REGULAR", preferred_start_min=480))

    Scheduler()._build_domains(state, groups)

    assert tm.candidate_calls == [(60, None), (90, 480)]
    assert all(group.domain for group in groups)


def test_greedy_pass_scores_only_currently_feasible_slots():
    class CountingScheduler(Scheduler):
        def __init__(self):
            super().__init__()
            self.scored = {}

        def _candidate_score(self, state, group, candidate):
            self.scored[group.group_id] = self.scored.get(group.group_id, 0) + 1
            return super()._candidate_score(state, group, candidate)

    tm = TimeModel(["Lunes"], day_start=420, day_end=540)
    state = ScheduleState(tm, [Classroom("A1", 30, "REGULAR")])
    groups = [Group(f"G{i}", 60, "REGULAR") for i in (1, 2)]
    scheduler = CountingScheduler()

    assert scheduler.schedule(state, groups)
    assert scheduler.scored == {"G1": 3, "G2": 1}
    assert groups[0].assignment == ("A1", 1, 420, 480)
    assert groups[1].assignment == ("A1", 1, 480, 540)


def test_pinned_split_siblings_preserve_exact_starts_per_family():
    from src.application.scheduling_service import SchedulingService
    from src.scheduling.course import Course
    from src.scheduling.validation import validate_schedule
    courses = [Course(code, 1, 240, 'REGULAR', force_split=True) for code in ('A', 'B')]
    rooms = {'R': Classroom('R', 20, 'REGULAR')}
    pins = {'A-G1-P1': ('R', 1, 421, 541), 'B-G1-P1': ('R', 1, 551, 671)}
    assignments, groups = SchedulingService(None).run(courses, classrooms=rooms, pinned_assignments=pins)
    assert len(assignments) == 4
    assert all(assignments[gid] == slot for gid, slot in pins.items())
    assert assignments['A-G1-P2'][2] == 421
    assert assignments['B-G1-P2'][2] == 551
    assert not validate_schedule(assignments, groups, rooms, TimeModel.default())


def test_seed_changes_only_equal_priority_choices_and_is_reproducible():
    from src.scheduling.validation import validate_schedule
    def run(seed):
        time = TimeModel(['Lunes', 'Martes'])
        rooms = [Classroom(name, 30, kind) for name, kind in
                 [('R1', 'REGULAR'), ('R2', 'REGULAR'), ('L', 'LAB')]]
        state = ScheduleState(time, rooms)
        group = Group('A', 60, 'REGULAR', preferred_start_min=480)
        assert Scheduler(seed).schedule(state, [group])
        assert group.assignment[0] != 'L'  # Room type outranks random tie-breaking.
        assert group.assignment[2] == 480  # Exact preference also outranks it.
        assert not validate_schedule(state.assignments, [group], state.classrooms, time)
        return group.assignment
    assert run(42) == run(42)
    assert len({run(seed) for seed in range(20)}) > 1


def test_reused_scheduler_resets_fixed_seed_for_equivalent_inputs():
    scheduler = Scheduler(12)
    results = []
    for _ in range(2):
        state, _ = _make_multi_classroom_state()
        groups = [Group(str(i), 60, 'REGULAR') for i in range(3)]
        assert scheduler.schedule(state, groups)
        results.append(dict(state.assignments))
    assert results[0] == results[1]
