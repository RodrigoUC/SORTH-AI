from copy import deepcopy
import pytest
from src.application.scheduling_service import SchedulingService
from src.scheduling.cancellation import SchedulingCancelled
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.mark.parametrize('stop', [1, 2, 4, 10, 50, 100, 200, 500])
def test_cancellation_checkpoints_preserve_inputs_and_next_run(stop):
    courses = [Course('BIO', 4, 60, 'REGULAR', size=20)]
    rooms = {'A': Classroom('A', 30, 'REGULAR'), 'B': Classroom('B', 30, 'REGULAR')}
    rooms['A'].occupy(1, 420, 480)
    before = deepcopy(rooms['A'].__dict__)
    calls = 0
    def cancelled():
        nonlocal calls
        calls += 1
        return calls >= stop
    with pytest.raises(SchedulingCancelled):
        SchedulingService(None).run(courses=courses, classrooms=rooms, cancelled=cancelled)
    assert calls == stop
    assert rooms['A'].__dict__ == before
    assignments, groups = SchedulingService(None).run(courses=courses, classrooms=rooms)
    assert len(assignments) == len(groups) == 4


def test_cancellation_after_engine_before_publication(monkeypatch):
    from src.scheduling.scheduler import Scheduler
    original = Scheduler.schedule
    finished = False
    def schedule(*args, **kwargs):
        nonlocal finished
        result = original(*args, **kwargs)
        finished = True
        return result
    monkeypatch.setattr(Scheduler, 'schedule', schedule)
    with pytest.raises(SchedulingCancelled):
        SchedulingService(None).run(courses=[Course('A', 1, 60, 'REGULAR')],
                                   classrooms={'R': Classroom('R', 30, 'REGULAR')},
                                   cancelled=lambda: finished)
