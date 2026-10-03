from dataclasses import replace
import pytest
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources, RESOURCE_KINDS
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom
from src.scheduling.time_model import TimeModel
from src.scheduling.validation import validate_schedule
from src.application.scheduling_service import SchedulingService


def data(kind='teacher', availability=None, enabled=True):
    courses = [Course(code, 1, 60, 'REGULAR', size=10, name=code) for code in ['DEMO-A', 'DEMO-B']]
    groups = [g for c in courses for g in c.generate_groups()]
    rooms = {n: Classroom(n, 20, 'REGULAR') for n in ['R1', 'R2']}
    catalog = ResourceCatalog(kind, enabled, (Resource('resource-demo-1', 'Alias', availability),),
                              tuple((g.group_id, ('resource-demo-1',)) for g in groups))
    return courses, groups, rooms, SchedulingResources((catalog,))


@pytest.mark.parametrize('kind', RESOURCE_KINDS)
def test_overlap_identity_hard_and_adjacent_allowed(kind):
    _, groups, rooms, resources = data(kind)
    a,b = [g.group_id for g in groups]
    placements = {a: ('R1', 1, 480, 540), b: ('R2', 1, 500, 560)}
    errors = validate_schedule(placements, groups, rooms, TimeModel.default(), resources=resources)
    assert [e.code for e in errors] == [kind.upper() + '_OVERLAP']
    assert errors[0].entity_id == 'resource-demo-1'
    assert {errors[0].group_id, errors[0].other_group_id} == {a,b}
    placements[b] = ('R2', 1, 540, 600)
    assert not validate_schedule(placements, groups, rooms, TimeModel.default(), resources=resources)


@pytest.mark.parametrize('kind', RESOURCE_KINDS)
def test_optional_disabled_preserves_data_and_core_room_conflicts(kind):
    _, groups, rooms, resources = data(kind, enabled=False)
    a,b = [g.group_id for g in groups]
    placements = {a: ('R1', 1, 480, 540), b: ('R2', 1, 480, 540)}
    assert not validate_schedule(placements, groups, rooms, TimeModel.default(), resources=resources)
    placements[b] = ('R1', 1, 480, 540)
    assert any('conflicto de aula' in str(e) for e in validate_schedule(placements, groups, rooms, TimeModel.default(), resources=resources))
    assert SchedulingResources.from_data(resources.to_data()) == resources


@pytest.mark.parametrize('kind', RESOURCE_KINDS)
@pytest.mark.parametrize('availability,allowed', [(None, True), ((), False), (((1,480,510),(1,510,540)), True), (((1,480,509),(1,510,540)), False), (((1,480,539),), False)])
def test_availability_unknown_empty_union_and_gap(kind, availability, allowed):
    _, groups, rooms, resources = data(kind, availability)
    errors = validate_schedule({groups[0].group_id:('R1',1,480,540)}, groups, rooms, TimeModel.default(), resources=resources)
    assert bool(errors) is not allowed


@pytest.mark.parametrize('kind', RESOURCE_KINDS)
def test_generator_cannot_relax_resource_availability_or_overlap(kind):
    courses, groups, rooms, resources = data(kind, ((1,480,540),))
    assignments, result = SchedulingService(None).run(courses, classrooms=rooms, resources=resources)
    assert len(assignments) == 1 and len(result) == 2
    assert next(iter(assignments.values()))[1:] == (1,480,540)
    assert sum(bool(g.unassigned_reason) for g in result) == 1
    assert not validate_schedule(assignments, result, rooms, TimeModel.default(), resources=resources)
    assert all(not room.occupancy for room in rooms.values())


def test_absent_resources_exact_legacy_generation_and_empty_partial():
    courses, _, rooms, _ = data()
    assert SchedulingService(None).run(courses, classrooms=rooms)[0] == SchedulingService(None).run(courses, classrooms=rooms, resources=SchedulingResources())[0]
    assert SchedulingService(None).run(courses, classrooms=rooms, resources=data(availability=())[3])[0] == {}


def test_user_selects_teacher_each_split_session_no_inheritance():
    course = Course('DEMO', 1, 240, 'REGULAR', size=10, name='Demo', force_split=True)
    groups = course.generate_groups()
    resources = SchedulingResources((ResourceCatalog('teacher', True, (Resource('a','Same name'), Resource('b','Same name')),
                                ((groups[0].group_id, ('a',)), (groups[1].group_id, ('b',)))),))
    rooms = {'R1': Classroom('R1',20,'REGULAR')}
    assignments, result = SchedulingService(None).run([course], classrooms=rooms, resources=resources)
    assert len(assignments) == 2
    assert resources.catalog('teacher').ids_for(groups[0].group_id) == ('a',)
    assert resources.catalog('teacher').ids_for(groups[1].group_id) == ('b',)
    assert not validate_schedule(assignments,result,rooms,TimeModel.default(),resources=resources)


def test_duplicate_labels_never_merge_and_multigroup_memberships_overlap():
    _, groups, rooms, original = data('student_group')
    a,b = [g.group_id for g in groups]
    catalog = replace(original.catalog('student_group'), resources=(Resource('one','Same'),Resource('two','Same')),
                      memberships=((a,('one',)),(b,('two',))))
    placements={a:('R1',1,480,540),b:('R2',1,480,540)}
    assert not validate_schedule(placements,groups,rooms,TimeModel.default(),resources=SchedulingResources((catalog,)))
    catalog=replace(catalog,memberships=((a,('one','two')),(b,('two',))))
    assert validate_schedule(placements,groups,rooms,TimeModel.default(),resources=SchedulingResources((catalog,)))[0].code=='STUDENT_GROUP_OVERLAP'


@pytest.mark.parametrize('mutation,code', [
    (lambda c: replace(c,resources=c.resources+c.resources),'DUPLICATE_RESOURCE_ID'),
    (lambda c: replace(c,memberships=c.memberships+c.memberships),'DUPLICATE_SESSION_MEMBERSHIP'),
    (lambda c: replace(c,memberships=(('missing',('resource-demo-1',)),)),'UNKNOWN_SESSION_REFERENCE'),
    (lambda c: replace(c,memberships=((c.memberships[0][0],('missing',)),)),'UNKNOWN_RESOURCE_REFERENCE'),
    (lambda c: replace(c,resources=(Resource('resource-demo-1','Alias',((True,480,540),)),)),'INVALID_AVAILABILITY'),
    (lambda c: replace(c,resources=(Resource('resource-demo-1','Alias',((7,480,540),)),)),'INVALID_AVAILABILITY'),
    (lambda c: replace(c,resources=(Resource('resource-demo-1','Alias',((1,540,480),)),)),'INVALID_AVAILABILITY'),
])
def test_structural_errors_even_disabled_and_unassigned(mutation,code):
    courses,groups,rooms,original=data(enabled=False)
    resources=SchedulingResources((mutation(original.catalog('teacher')),))
    assert code in {e.code for e in resources.validate({},groups,TimeModel.default())}
    with pytest.raises(ValueError):
        SchedulingService(None).run(courses,classrooms=rooms,resources=resources)


def test_strict_versioned_import_no_silent_future_or_unknown_fields():
    original=data()[3].to_data()
    for key,value in [('version',True),('version',2),('extra',1),('catalogs',{})]:
        malformed={**original,key:value}
        with pytest.raises(ValueError): SchedulingResources.from_data(malformed)
    catalog=original['catalogs'][0]
    for key,value in [('enabled','false'),('kind','inferred_roster'),('extra',1)]:
        with pytest.raises(ValueError): ResourceCatalog.from_data({**catalog,key:value})


def test_unknown_null_and_empty_memberships_survive_round_trip():
    _,groups,_,original=data()
    catalog=replace(original.catalog('teacher'),memberships=((groups[0].group_id,None),(groups[1].group_id,())))
    resources=SchedulingResources((catalog,))
    assert SchedulingResources.from_data(resources.to_data())==resources
    assert not resources.validate({},groups,TimeModel.default())


def test_invalid_resource_pins_rejected_before_reservation():
    courses,groups,rooms,resources=data()
    pins={groups[0].group_id:('R1',1,480,540),groups[1].group_id:('R2',1,480,540)}
    with pytest.raises(ValueError,match='TEACHER_OVERLAP'):
        SchedulingService(None).run(courses,classrooms=rooms,resources=resources,pinned_assignments=pins)
    assert all(not room.occupancy for room in rooms.values())


def test_multiple_simultaneous_teachers_not_inferred_from_course_choice():
    _,groups,_,resources=data()
    catalog=replace(resources.catalog('teacher'),resources=(Resource('a','A'),Resource('b','B')),
                    memberships=((groups[0].group_id,('a','b')),))
    assert 'INVALID_MEMBERSHIP' in {i.code for i in catalog.validate({},groups,TimeModel.default())}


@pytest.mark.parametrize('group_id', ['', None, 1, True, [], {}])
def test_deserialization_still_rejects_malformed_session_references(group_id):
    document = data()[3].to_data()
    document['catalogs'][0]['memberships'][0]['group_id'] = group_id
    with pytest.raises(ValueError, match='Malformed session membership'):
        SchedulingResources.from_data(document)


@pytest.mark.parametrize('field', ['id', 'label'])
def test_session_reference_compatibility_does_not_relax_resource_name_limits(field):
    document = data()[3].to_data()
    document['catalogs'][0]['resources'][0][field] = 'X' * 121
    with pytest.raises(ValueError, match='Malformed resource'):
        SchedulingResources.from_data(document)
