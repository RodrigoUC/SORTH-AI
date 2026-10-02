from src.application.scheduling_service import SchedulingService
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


def test_supplied_classrooms_are_not_mutated():
    room = Classroom('A1', 30, 'REGULAR')
    room.occupy(1, 420, 480)
    room.set_allowed_courses({'OLD'})
    course = Course('BIO', 1, 60, 'REGULAR', size=20)
    result, groups = SchedulingService(None).run(
        courses=[course], classrooms={'A1': room},
        classroom_restrictions={'A1': {'BIO'}},
    )
    assert result and groups
    assert room.occupancy == {1: [(420, 480)]}
    assert room.allowed_courses == {'OLD'}


def test_generation_from_saved_data_does_not_require_excel():
    course = Course('BIO', 1, 60, 'REGULAR')
    rooms = {'A1': Classroom('A1', 30, 'REGULAR')}
    first = SchedulingService(None, seed=42).run(courses=[course], classrooms=rooms)[0]
    second = SchedulingService(None, seed=42).run(courses=[course], classrooms=rooms)[0]
    assert first == second
