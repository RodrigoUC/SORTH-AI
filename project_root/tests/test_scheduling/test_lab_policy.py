import pytest
from src.application.scheduling_service import SchedulingService
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.group import Group
from src.scheduling.schedule_state import ScheduleState
from src.scheduling.scheduler import Scheduler
from src.scheduling.time_model import TimeModel
from src.scheduling.validation import validate_schedule, unassigned_reason
from src.infrastructure.session_repository import SessionRepository
from src.infrastructure.schedule_exporter import ScheduleExporter


def test_no_laboratory_returns_visible_pending_group_not_failure():
    result, groups = SchedulingService(None).run(courses=[Course('BIO', 1, 60, 'LAB')],
                                               classrooms={'A': Classroom('A', 30, 'REGULAR')})
    assert result == {} and len(groups) == 1
    assert 'No hay laboratorios' in groups[0].unassigned_reason
    assert not groups[0].lab_override


@pytest.mark.parametrize('count,expected', [(1, 1), (2, 2), (3, 2)])
def test_small_known_capacity_instance(count, expected):
    # Exactly two non-overlapping 60-minute slots; regular room cannot add LAB capacity.
    tm = TimeModel(['Lunes'], 420, 540)
    rooms = {'L': Classroom('L', 30, 'LAB'), 'A': Classroom('A', 30, 'REGULAR')}
    groups = [Group(str(i), 60, 'LAB') for i in range(count)]
    state = ScheduleState(tm, list(rooms.values()))
    Scheduler().schedule(state, groups)
    assert len(state.assignments) == expected
    assert not validate_schedule(state.assignments, groups, rooms, tm)
    if count == 3:
        assert 'no demuestra que sea imposible' in groups[-1].unassigned_reason


@pytest.mark.parametrize('capacity,restriction,duration,fragment', [
    (1, None, 60, 'capacidad'), (30, {'OTHER'}, 60, 'restricciones'),
    (30, None, 600, 'duración'),
])
def test_specific_static_failure_reasons(capacity, restriction, duration, fragment):
    room = Classroom('L', capacity, 'LAB')
    room.allowed_courses = restriction
    reason = unassigned_reason(Group('B', duration, 'LAB', size=20, course_code='B'),
                               {'L': room}, TimeModel.default())
    assert fragment.lower() in reason.lower()


def test_regular_courses_preserve_fallback_to_laboratory():
    assignments, groups = SchedulingService(None).run(courses=[Course('B', 1, 60, 'REGULAR')],
                                                     classrooms={'L': Classroom('L', 20, 'LAB')})
    assert assignments and not groups[0].lab_override


@pytest.mark.parametrize('placement,fragment', [
    (('A', 1, 420, 480), 'excepción'),
    (('A', 0, 420, 480), 'horario'),
    (('A', 1, 700, 760), 'horario'),
    (('A', 1, 420, 490), 'duración'),
])
def test_independent_validator_rejects_invalid_result(placement, fragment):
    errors = validate_schedule({'B': placement}, [Group('B', 60, 'LAB')],
                               {'A': Classroom('A', 30, 'REGULAR')}, TimeModel.default())
    assert any(fragment in e for e in errors)


def test_manual_override_roundtrip_and_export(tmp_path):
    rooms = {'A': Classroom('A', 30, 'REGULAR')}
    courses = [Course('B', 1, 60, 'LAB', size=20)]
    groups = courses[0].generate_groups()
    state = ScheduleState(TimeModel.default(), list(rooms.values()))
    assert not state.assign(groups[0], 'A', 1, 420)
    assert state.assign(groups[0], 'A', 1, 420, allow_lab_override=True)
    gid = groups[0].group_id
    repo = SessionRepository(str(tmp_path / 'session.db'))
    repo.save_session(None, 42, rooms, courses, {}, state.assignments, lab_overrides={gid})
    restored = repo.load_session()
    assert restored['lab_overrides'] == {gid}
    assert not validate_schedule(restored['assignments'], groups, rooms, TimeModel.default(), restored['lab_overrides'])
    for extension in ('csv', 'xlsx'):
        getattr(ScheduleExporter(TimeModel.default()), 'to_csv' if extension == 'csv' else 'to_excel')(
            state.assignments, str(tmp_path / f'result.{extension}'), groups)
        assert (tmp_path / f'result.{extension}').stat().st_size > 0
    state.unassign(groups[0])
    assert not groups[0].lab_override
    repo.save_session(None, 42, rooms, courses, {}, {}, lab_overrides={gid})
    assert not repo.load_session()['lab_overrides']


@pytest.mark.parametrize('size,start', [(31, 420), (10, 700), (10, 400)])
def test_override_never_relaxes_capacity_or_time(size, start):
    state = ScheduleState(TimeModel.default(), [Classroom('A', 30, 'REGULAR')])
    assert not state.assign(Group('B', 60, 'LAB', size=size), 'A', 1, start, allow_lab_override=True)


def test_override_never_relaxes_overlap():
    state = ScheduleState(TimeModel.default(), [Classroom('A', 30, 'REGULAR')])
    assert state.assign(Group('A', 60, 'REGULAR'), 'A', 1, 420)
    assert not state.assign(Group('B', 60, 'LAB'), 'A', 1, 420, allow_lab_override=True)


def test_validation_notices_retain_structured_translation_parameters():
    from src.scheduling.validation import ValidationNotice
    notice = ValidationNotice("{gid}: requiere laboratorio", gid="BIO-G1")
    assert str(notice) == "BIO-G1: requiere laboratorio"
    calls = []
    def translate(source, **parameters):
        calls.append((source, parameters))
        return "Laboratory required: " + parameters["gid"]
    assert notice.render(translate) == "Laboratory required: BIO-G1"
    assert calls == [("{gid}: requiere laboratorio", {"gid": "BIO-G1"})]
