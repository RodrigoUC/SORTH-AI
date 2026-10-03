from copy import deepcopy
import pytest
from src.application.placement_suggestions import enumerate_placements, validate_choice, revision
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.group import Group
from src.scheduling.time_model import TimeModel
from src.scheduling.validation import validate_schedule
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources


def inputs():
    groups = Course('A', 2, 60, 'REGULAR', size=20).generate_groups()
    groups[0].assignment = ('R', 1, 420, 480)
    return dict(groups=groups, assignments={'A-G1': groups[0].assignment},
                classrooms={'R': Classroom('R', 30, 'REGULAR')},
                time_model=TimeModel.default(), pinned={'A-G1'})


def test_candidates_equal_independent_validator_on_declared_grid_and_do_not_mutate():
    data = inputs()
    before = revision(**data)
    result = enumerate_placements('A-G2', **data, max_options=500)
    expected = []
    for day in range(1, 7):
        for start in data['time_model'].generate_start_candidates(60):
            candidate = ('R', day, start, start + 60)
            schedule = dict(data['assignments'], **{'A-G2': candidate})
            if not validate_schedule(schedule, data['groups'], data['classrooms'], data['time_model']):
                expected.append(candidate)
    assert result.placements == tuple(expected)
    assert not result.truncated
    assert before == revision(**data)
    assert all(not validate_choice(result, p, **data) for p in result.placements)


@pytest.mark.parametrize('change', ['assignment', 'pin', 'room', 'time', 'group', 'resource'])
def test_stale_inputs_require_recalculation(change):
    data = inputs()
    result = enumerate_placements('A-G2', **data)
    if change == 'assignment': data['assignments']['A-G1'] = ('R', 2, 420, 480)
    if change == 'pin': data['pinned'] = set()
    if change == 'room': data['classrooms']['R'].capacity = 25
    if change == 'time': data['time_model'] = TimeModel(['Lunes'])
    if change == 'group': data['groups'][1].size = 24
    if change == 'resource': data['resources'] = SchedulingResources((ResourceCatalog('teacher'),))
    assert validate_choice(result, result.placements[0], **data) == ('stale',)


def test_limits_no_options_lab_and_reserved_rooms():
    data = inputs()
    assert enumerate_placements('A-G2', **data, max_options=1).truncated
    assert enumerate_placements('A-G2', **data, max_candidates=1).examined == 1
    data['groups'][1].required_room_type = 'LAB'
    result = enumerate_placements('A-G2', **data)
    assert not result.placements and result.notices
    assert data['assignments'] == {'A-G1': ('R', 1, 420, 480)}
    data['groups'][1].required_room_type = 'REGULAR'
    data['classrooms']['R'].allowed_courses = {'OTHER'}
    assert not enumerate_placements('A-G2', **data).placements


def test_split_sessions_pins_and_no_automatic_lab_exception():
    groups = [Group('P-1', 60, 'LAB', parent_group_id='P'),
              Group('P-2', 60, 'LAB', parent_group_id='P')]
    data = dict(groups=groups, assignments={'P-1': ('LAB', 1, 480, 540)},
        classrooms={'LAB': Classroom('LAB', 30, 'LAB'), 'R': Classroom('R', 30, 'REGULAR')},
        time_model=TimeModel.default(), pinned={'P-1'})
    options = enumerate_placements('P-2', **data, max_options=500)
    assert options.placements
    assert all(room == 'LAB' and day != 1 and start == 480 for room, day, start, end in options.placements)
    with pytest.raises(ValueError): enumerate_placements('P-1', **data)


def test_resource_availability_and_conflicts_always_enforced():
    data = inputs()
    data['classrooms']['S'] = Classroom('S', 30, 'REGULAR')
    data['resources'] = SchedulingResources((ResourceCatalog('teacher', True,
        (Resource('t', 'Teacher', ((1, 420, 600),)),),
        (('A-G1', ('t',)), ('A-G2', ('t',)))),))
    result = enumerate_placements('A-G2', **data)
    assert result.placements
    assert all(day == 1 and 480 <= start < end <= 600 for _, day, start, end in result.placements)


def test_custom_time_model_respected():
    data = inputs()
    data['assignments'] = {}
    data['pinned'] = set()
    data['groups'][0].assignment = None
    data['time_model'] = TimeModel(['Miércoles'], 900, 1080)
    result = enumerate_placements('A-G2', **data)
    assert result.placements
    assert all(day == 1 and 900 <= start < end <= 1080 for _, day, start, end in result.placements)


def test_forged_choice_rejected():
    data = inputs(); result = enumerate_placements('A-G2', **data)
    assert validate_choice(result, ('R', 1, 420, 480), **data) == ('invalid_choice',)


def test_split_exact_off_grid_and_saved_preference_remain_available():
    groups = [Group('P-1', 60, 'REGULAR', parent_group_id='P'),
              Group('P-2', 60, 'REGULAR', parent_group_id='P')]
    data = dict(groups=groups, assignments={'P-1': ('R', 1, 482, 542)},
        classrooms={'R': Classroom('R', 30, 'REGULAR')}, time_model=TimeModel.default())
    options = enumerate_placements('P-2', **data)
    assert options.placements
    assert all(start == 482 and day != 1 for _, day, start, _ in options.placements)
    data = inputs()
    data['groups'][1].preferred_start_min = 487
    assert any(p[2] == 487 for p in enumerate_placements('A-G2', **data).placements)
