"""Group-local admission reuse must preserve the unindexed solver exactly."""
from copy import deepcopy
from functools import partial
import random

import pytest

from src.application.scheduling_service import SchedulingService
from src.scheduling.cancellation import SchedulingCancelled
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.group import Group
from src.scheduling.schedule_state import ScheduleState
from src.scheduling.scheduler import Scheduler
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from src.scheduling.time_model import TimeModel
from src.scheduling.validation import validate_schedule


class UncachedScheduler(Scheduler):
    """Keep the original per-candidate admission rule as the comparison oracle."""
    @staticmethod
    def _resource_checker(state, group):
        return partial(state.resources_allow, group)


class CountingState(ScheduleState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resource_checks = []

    def resources_allow(self, group, day, start_min):
        self.resource_checks.append((group.group_id, day, start_min))
        return super().resources_allow(group, day, start_min)


def test_domain_admission_is_checked_once_per_group_day_start_not_room():
    tm = TimeModel(['Lunes', 'Martes'], day_start=420, day_end=600, breaks=())
    state = CountingState(tm, [Classroom(f'R{i}', 50, 'REGULAR') for i in range(20)],
                          SchedulingResources())
    groups = [Group('short', 60, 'REGULAR'), Group('long', 90, 'REGULAR')]
    Scheduler()._build_domains(state, groups)
    assert len(state.resource_checks) == len(set(state.resource_checks)) == 18
    assert [len(group.domain) for group in groups] == [200, 160]


def test_greedy_checker_is_fresh_after_each_assignment_and_final_admission_runs():
    tm = TimeModel(['Lunes'], day_start=420, day_end=540, breaks=())
    groups = [Group(gid, 60, 'REGULAR') for gid in ('A', 'B')]
    resources = SchedulingResources((ResourceCatalog('teacher', True, (Resource('T', 'Teacher'),),
        tuple((g.group_id, ('T',)) for g in groups)),))
    state = CountingState(tm, [Classroom(f'R{i}', 50, 'REGULAR') for i in range(8)], resources)
    scheduler = Scheduler()
    scheduler._build_domains(state, groups)
    state.resource_checks.clear()
    scheduler._greedy_pass(state, groups)
    assert len(state.assignments) == 2
    assert groups[0].assignment[2] != groups[1].assignment[2]
    assert len(state.resource_checks) == 8
    assert not validate_schedule(state.assignments, groups, state.classrooms, tm, resources=resources)


def test_resource_checker_propagates_exceptions_without_caching_them():
    state = CountingState(TimeModel.default(), [], SchedulingResources())
    group = Group('A', 60, 'REGULAR')
    attempts = 0
    def fail_once(*_args):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ValueError('resource admission failed')
        return True
    state.resources_allow = fail_once
    checker = Scheduler._resource_checker(state, group)
    with pytest.raises(ValueError, match='resource admission failed'):
        checker(1, 420)
    assert checker(1, 420) and checker(1, 420)
    assert attempts == 2


def test_cache_does_not_keep_old_assignments_across_domain_calls():
    tm = TimeModel(['Lunes'], day_start=420, day_end=540, breaks=())
    groups = [Group(gid, 60, 'REGULAR') for gid in ('A', 'B')]
    resources = SchedulingResources((ResourceCatalog('teacher', True, (Resource('T', 'Teacher'),),
        tuple((g.group_id, ('T',)) for g in groups)),))
    state = ScheduleState(tm, [Classroom(f'R{i}', 50, 'REGULAR') for i in range(2)], resources)
    scheduler = Scheduler()
    scheduler._build_domains(state, [groups[1]])
    assert len(groups[1].domain) == 6
    assert state.assign(groups[0], 'R0', 1, 420)
    scheduler._build_domains(state, [groups[1]])
    assert {(day, start) for _, day, start in groups[1].domain} == {(1, 480)}
    state.unassign(groups[0])
    scheduler._build_domains(state, [groups[1]])
    assert len(groups[1].domain) == 6


def make_fixture(seed):
    rng = random.Random(seed)
    tm = TimeModel(['Lunes', 'Martes', 'Miércoles'], day_start=427, day_end=1027,
                   breaks=((667, 727),))
    rooms = [Classroom(f'R{i}', 30 + 10 * (i % 3), 'LAB' if i % 3 == 0 else 'REGULAR')
             for i in range(6)]
    courses = [Course(f'C{i}', 2, rng.choice((60, 90, 120, 240)),
                      'LAB' if i % 4 == 0 else 'REGULAR', size=rng.choice((10, 30, 40)),
                      force_split=i % 3 == 0,
                      preferred_day='Lunes' if i % 4 == 1 else None,
                      preferred_start_min=487 if i % 3 == 1 else None) for i in range(8)]
    courses[0] = Course('C0', 1, 240, 'LAB', size=20, force_split=True)
    groups = [g for course in courses for g in course.generate_groups()]
    rooms[-1].set_allowed_courses({'C0', 'C1'})
    catalogs = []
    for kind in ('teacher', 'student_group', 'student'):
        resources = tuple(Resource(f'{kind}{i}', f'Resource {i}',
            None if i < 2 else () if i == 2 else ((1, 427, 667), (1, 727, 1027),
              (2, 427, 667), (2, 727, 1027), (3, 427, 667), (3, 727, 1027)))
            for i in range(4))
        members = tuple((g.group_id, None if i % 7 == 0 else
            tuple(rng.sample([r.id for r in resources], rng.randrange(2 if kind == 'teacher' else 3))))
            for i, g in enumerate(groups))
        catalogs.append(ResourceCatalog(kind, bool(seed % 5), resources, members))
    state = ScheduleState(tm, rooms, SchedulingResources(tuple(catalogs)))
    pin = groups[0]
    assert state.assign(pin, 'R1', 2, 437, allow_lab_override=True)
    pin.pinned = True
    return state, groups, {pin.group_id: pin.assignment}


@pytest.mark.parametrize('fixture_seed', range(12))
@pytest.mark.parametrize('solver_seed', (0, 42, 999))
def test_cached_and_uncached_solver_are_exactly_equivalent(fixture_seed, solver_seed):
    source = make_fixture(fixture_seed)
    results = []
    for scheduler_type in (Scheduler, UncachedScheduler):
        state, groups, pins = deepcopy(source)
        scheduler = scheduler_type(solver_seed)
        complete = scheduler.schedule(state, groups)
        errors = validate_schedule(state.assignments, groups, state.classrooms, state.time_model,
            {g.group_id for g in groups if g.lab_override}, state.resources)
        assert not errors
        assert all(state.assignments[gid] == pin for gid, pin in pins.items())
        results.append((complete, list(state.assignments.items()),
                        [[(r.name, d, s) for r,d,s in g.domain] for g in groups],
                        [g.unassigned_reason for g in groups], scheduler._rng.getstate()))
    assert results[0] == results[1]


def test_cache_hits_keep_candidate_cancellation_and_do_not_publish_partial_results():
    courses = [Course('A', 2, 60, 'REGULAR')]
    rooms = {f'R{i}': Classroom(f'R{i}', 30, 'REGULAR') for i in range(30)}
    resources = SchedulingResources((ResourceCatalog('teacher', True, (Resource('T','Teacher'),),
        (('A-G1', ('T',)), ('A-G2', ('T',)))),))
    checks = 0
    def cancelled():
        nonlocal checks
        checks += 1
        return checks == 1000
    with pytest.raises(SchedulingCancelled):
        SchedulingService(None).run(courses, classrooms=rooms, resources=resources, cancelled=cancelled)
    assert checks == 1000
    assert all(not room.occupancy for room in rooms.values())
    assignments, groups = SchedulingService(None).run(courses, classrooms=rooms, resources=resources)
    assert len(assignments) == len(groups) == 2


def test_greedy_cache_hits_keep_per_candidate_cancellation():
    class CountingScheduler(Scheduler):
        scored = 0

        def _candidate_score(self, state, group, candidate):
            result = super()._candidate_score(state, group, candidate)
            self.scored += 1
            return result

    tm = TimeModel(['Lunes'], day_start=420, day_end=480, breaks=())
    state = CountingState(tm, [Classroom(f'R{i}', 50, 'REGULAR') for i in range(8)],
                          SchedulingResources())
    group = Group('A', 60, 'REGULAR')
    scheduler = CountingScheduler()
    scheduler._build_domains(state, [group])
    state.resource_checks.clear()
    scheduler._cancelled = lambda: scheduler.scored == 3

    with pytest.raises(SchedulingCancelled):
        scheduler._greedy_pass(state, [group])

    assert scheduler.scored == 3
    assert state.resource_checks == [('A', 1, 420)]
    assert not state.assignments and not group.is_assigned()
    assert all(not room.occupancy for room in state.classrooms.values())


def test_reused_scheduler_rechecks_resources_on_separate_runs():
    tm = TimeModel(['Lunes'], day_start=420, day_end=480, breaks=())
    state = CountingState(tm, [Classroom(f'R{i}', 50, 'REGULAR') for i in range(4)])
    group = Group('A', 60, 'REGULAR')
    scheduler = Scheduler()

    for availability, expected in ((None, True), ((), False), (None, True)):
        state.unassign(group)
        state.resources = SchedulingResources((ResourceCatalog('teacher', True,
            (Resource('T', 'Teacher', availability),), (('A', ('T',)),)),))
        state.resource_checks.clear()

        assert scheduler.schedule(state, [group]) is expected
        assert group.is_assigned() is expected
        assert len(group.domain) == (4 if expected else 0)
        assert len(state.resource_checks) == (3 if expected else 2)


def test_checker_memory_is_bounded_by_temporal_candidates_not_rooms():
    state = ScheduleState(TimeModel.default(), [], SchedulingResources())
    checker = Scheduler._resource_checker(state, Group('A', 60, 'REGULAR'))
    for _room in range(500):
        for day in range(1, 7):
            for start in range(420, 720, 30):
                assert checker(day, start)
    assert checker.cache_info().currsize == 60
    assert checker.cache_info().misses == 60
