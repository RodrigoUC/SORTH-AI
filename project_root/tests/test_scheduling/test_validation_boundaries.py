"""Validation oracle tests do not call scheduler feasibility/scoring helpers."""
from itertools import product
import pytest
from src.scheduling.classroom import Classroom
from src.scheduling.group import Group
from src.scheduling.time_model import TimeModel
from src.scheduling.validation import validate_schedule
from src.application.scheduling_service import SchedulingService
from src.scheduling.course import Course
from src.scheduling.scheduler import Scheduler


def check(assignments, groups=None, rooms=None, overrides=()):
    return validate_schedule(assignments, groups or [Group('G', 60, 'REGULAR', size=20)],
                             rooms or {'A': Classroom('A', 20, 'REGULAR')},
                             TimeModel.default(), overrides)


@pytest.mark.parametrize('placement', [None, (), ('A', 1), ('A', 1, 420, 480, 0),
    ([], 1, 420, 480), ('A', True, 420, 480), ('A', 1.5, 420, 480),
    ('A', 1, '420', 480), ('A', 1, 420.5, 480.5), ('A', 1, float('nan'), 480)])
def test_malformed_placements_return_notices(placement):
    assert 'mal formada' in check({'G': placement})[0]


def test_duplicate_identifiers_are_rejected_even_without_assignments():
    assert 'duplicado' in check({}, [Group('G', 60, 'LAB'), Group('G', 60, 'REGULAR')])[0]


def test_interval_oracle_exhaustively_checks_boundaries():
    # Closed operating bounds, half-open lunch, exact duration and 1..6 days.
    for day, start, duration in product(range(0, 8), [419, 420, 659, 660, 661, 719, 720, 779, 780, 1259, 1260, 1261], [59, 60, 61]):
        end = start + duration
        expected = 1 <= day <= 6 and 420 <= start < end <= 1320 and duration == 60 and (end <= 720 or start >= 780)
        assert (not check({'G': ('A', day, start, end)})) == expected


@pytest.mark.parametrize('other_start,valid', [(420, False), (479, False), (480, True), (481, True)])
def test_room_collision_oracle(other_start, valid):
    groups = [Group(gid, 60, 'REGULAR') for gid in ['G', 'H']]
    assert (not check({'G': ('A', 1, 420, 480), 'H': ('A', 1, other_start, other_start+60)}, groups)) == valid


def test_both_directions_of_room_restrictions_and_capacity():
    rooms = {'A': Classroom('A', 20, 'REGULAR'), 'B': Classroom('B', 20, 'REGULAR')}
    rooms['A'].set_allowed_courses({'C'})
    assert check({'G': ('A', 1, 420, 480)}, [Group('G', 60, 'REGULAR', course_code='OTHER')], rooms)
    group = Group('G', 60, 'REGULAR', course_code='C', suggested_classroom='A')
    assert check({'G': ('B', 1, 420, 480)}, [group], rooms)
    group.suggested_classroom = None  # soft suggestion alone is not a hard rule
    assert not check({'G': ('B', 1, 420, 480)}, [group], rooms)
    group.size = 21
    assert check({'G': ('B', 1, 420, 480)}, [group], rooms)


@pytest.mark.parametrize('day,start,valid', [(1,480,False),(2,480,False),(2,420,True)])
def test_split_sessions_require_distinct_days_and_equal_starts(day,start,valid):
    groups = [Group(gid,60,'REGULAR',parent_group_id='P') for gid in ['G','H']]
    assert (not check({'G':('A',1,420,480),'H':('A',day,start,start+60)},groups)) == valid


def test_service_rejects_invalid_scheduler_result(monkeypatch):
    def corrupt(self, state, groups):
        state.assignments[groups[0].group_id] = ('A', 1, 700, 760)
    monkeypatch.setattr(Scheduler, 'schedule', corrupt)
    with pytest.raises(ValueError, match='horario'):
        SchedulingService(None).run([Course('C',1,60,'REGULAR')],classrooms={'A':Classroom('A',20,'REGULAR')})


@pytest.mark.parametrize('gid,room',[('UNKNOWN','A'),('G','UNKNOWN')])
def test_unknown_identity_rejected(gid,room):
    assert 'desconocido' in check({gid:(room,1,420,480)})[0]
