import pytest
from src.scheduling.project_calendar import ProjectCalendar
from src.scheduling.time_model import TimeModel
from src.application.calendar_transition import preview_calendar_change
from src.scheduling.teaching_resources import SchedulingResources, ResourceCatalog, Resource
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.application.scheduling_service import SchedulingService


@pytest.mark.parametrize('values', [dict(days=[]), dict(days=['Unknown']), dict(days=['Lunes','Lunes']),
    dict(day_start=True), dict(day_start=100, day_end=50), dict(day_end=1441),
    dict(breaks=[(700,800),(750,850)]), dict(breaks=[(100,200)]),
    dict(breaks=[(420,1320)]), dict(breaks=[(720,720)]), dict(breaks=[(720,False)])])
def test_strict_calendar(values):
    with pytest.raises(ValueError): ProjectCalendar(**values)


def test_roundtrip_normalization_and_boundaries():
    calendar = ProjectCalendar(('Viernes','Martes'), 480, 1020, ((900,930),(600,630)))
    assert calendar.days == ('Martes','Viernes')
    assert ProjectCalendar.from_dict(calendar.to_dict()) == calendar
    time = TimeModel.from_calendar(calendar)
    assert time.is_valid_interval(1, 480, 600)
    assert not time.overlaps_lunch(480,600)
    assert time.overlaps_lunch(599,601)
    assert not time.overlaps_lunch(630,900)
    assert time.generate_start_candidates(390) == []
    assert time.generate_start_candidates(60) == [480,510,540,630,660,690,720,750,780,810,840,930,960]


def test_default_and_unknown_version():
    assert TimeModel.default().calendar == ProjectCalendar()
    data = ProjectCalendar().to_dict(); data['version'] = 2
    with pytest.raises(ValueError): ProjectCalendar.from_dict(data)


def fixture():
    course = Course(code='C', name='Course', number_of_groups=2, duration_min=60, required_room_type='REGULAR')
    return course.generate_groups(), {'A':Classroom('A',50,'REGULAR')}


def test_preview_preserves_weekday_and_reports_removed():
    groups, rooms = fixture()
    a,b = [g.group_id for g in groups]
    assignments = {a:('A',2,480,540), b:('A',1,480,540)}
    preview = preview_calendar_change(ProjectCalendar(), ProjectCalendar(('Martes',)), assignments, groups, rooms)
    assert preview.assignments == {a:('A',1,480,540)}
    assert preview.affected == (b,)
    assert assignments[a][1] == 2


def test_resource_availability_remap_and_removed_day_rejection():
    groups, rooms = fixture()
    resources = SchedulingResources((ResourceCatalog('teacher',False,(Resource('t','T',((2,480,600),)),)),))
    preview = preview_calendar_change(ProjectCalendar(), ProjectCalendar(('Martes',)),{},groups,rooms,resources=resources)
    assert preview.resources.catalogs[0].resources[0].availability == ((1,480,600),)
    with pytest.raises(ValueError,match='removed'):
        preview_calendar_change(ProjectCalendar(),ProjectCalendar(('Lunes',)),{},groups,rooms,resources=resources)


def test_generator_uses_calendar():
    calendar=ProjectCalendar(('Viernes',), 900, 1020, ((930,960),))
    course=Course(code='C',name='Course',number_of_groups=1,duration_min=60,required_room_type='REGULAR')
    assignments, groups=SchedulingService(None).run([course],classrooms={'A':Classroom('A',50,'REGULAR')},calendar=calendar)
    assert list(assignments.values()) == [('A',1,960,1020)]


def test_mcp_fixed_contract_rejects_custom_calendar():
    from src.application.preview_contract import INPUT_SCHEMA, validate_shape, ContractError
    data={'courses':[], 'classrooms':[], 'seed':42, 'calendar':ProjectCalendar().to_dict()}
    with pytest.raises(ContractError) as error:
        validate_shape(data,INPUT_SCHEMA)
    assert error.value.code == 'UNSUPPORTED_FIELD'


def test_sunday_is_optional_and_does_not_change_default_indexes():
    from src.scheduling.project_calendar import DAYS, DEFAULT_DAYS
    assert ProjectCalendar().days==DEFAULT_DAYS
    assert TimeModel.default().index_to_day==dict(enumerate(DEFAULT_DAYS,1))
    time=TimeModel.from_calendar(ProjectCalendar(DAYS))
    assert time.to_day_index('Domingo')==7
    assert time.is_valid_interval(7,480,540)
    assert not time.is_valid_interval(8,480,540)
    assert not TimeModel.default().is_valid_interval(7,480,540)
    resources=SchedulingResources((ResourceCatalog('teacher',True,(Resource('t','T',((7,480,600),)),)),))
    assert not resources.structure_issues(set(),time)
    assert resources.structure_issues(set(),TimeModel.default())
    assert {day:time.to_day_index(day) for day in DEFAULT_DAYS}==TimeModel.default().day_to_index
    course=Course('SUN',1,60,'REGULAR',preferred_day='Domingo')
    calendar=ProjectCalendar(('Domingo',),480,600,())
    assignments,groups=SchedulingService(None).run([course],classrooms={'A':Classroom('A',30,'REGULAR')},calendar=calendar)
    assert list(assignments.values())==[('A',1,480,540)]
    assert TimeModel.from_calendar(calendar).to_day_name(1)=='Domingo'
