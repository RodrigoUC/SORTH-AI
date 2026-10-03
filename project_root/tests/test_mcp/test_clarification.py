"""Draft schemas guide the host without weakening completed input validation."""
import copy

import pytest

from src.application.preview_clarification import (DRAFT_SCHEMA, PREPARATION_SCHEMA,
                                                   NEEDS_INPUT_SCHEMA, prepare_configuration)
from src.application.preview_contract import ContractError, validate_shape
from .test_preview import request


def test_partial_example_returns_all_questions_without_inventing():
    data = {'courses': [{'code': 'BIF401', 'name': 'Biología'}, {'code': 'QIM500', 'name': 'Química'}],
            'classrooms': [{'name': '201'}, {'name': '202'}]}
    before = copy.deepcopy(data)
    validate_shape(data, PREPARATION_SCHEMA)
    result = prepare_configuration(data, confirm_scope=True)
    validate_shape(result, NEEDS_INPUT_SCHEMA)
    paths = {row['path'] for row in result['questions']}
    assert paths == {
        *(f'request.courses[{index}].{field}' for index in range(2)
          for field in ('number_of_groups', 'duration_min', 'required_room_type', 'size')),
        *(f'request.classrooms[{index}].{field}' for index in range(2) for field in ('capacity', 'room_type')),
        'request.seed', 'request.classroom_restrictions', 'request.scope_confirmed'}
    assert result['next_action'] == 'ask_user_then_resubmit'
    assert 'normalized' not in result and 'assignments' not in result
    assert data == before


def test_draft_accepts_absent_and_empty_but_rejects_invalid_supplied_values():
    for data in ({}, {'courses': [], 'classrooms': []}):
        validate_shape(data, DRAFT_SCHEMA)
        assert prepare_configuration(data)['status'] == 'needs_input'
    for data in ({'seed': True}, {'courses': [{'duration_min': 0}]}, {'file_path': 'SECRET'},
                 {'courses': [{'code': '../SECRET'}]}, {'classrooms': [{'capacity': None}]}):
        with pytest.raises(ContractError) as caught:
            prepare_configuration(data)
        assert 'SECRET' not in str(caught.value)


def test_scope_confirmation_is_explicit_and_does_not_enter_domain():
    data = request()
    result = prepare_configuration(data, confirm_scope=True)
    assert {q['path'] for q in result['questions']} == {'request.scope_confirmed', 'request.classroom_restrictions'}
    data.update(scope_confirmed=True, classroom_restrictions=[])
    result = prepare_configuration(data, confirm_scope=True)
    assert result['status'] == 'validated'
    assert 'scope_confirmed' not in result['normalized']
    data['scope_confirmed'] = False
    with pytest.raises(ContractError) as caught:
        prepare_configuration(data, confirm_scope=True)
    assert caught.value.code == 'UNSUPPORTED_CONSTRAINTS'


def test_complete_legacy_input_remains_compatible_and_limits_still_apply():
    assert prepare_configuration(request())['status'] == 'validated'
    data = request()
    data['courses'] *= 2
    with pytest.raises(ContractError) as caught:
        prepare_configuration(data)
    assert caught.value.code == 'DUPLICATE_ID'
    worst = {'courses': [{} for _ in range(32)], 'classrooms': [{} for _ in range(16)]}
    result = prepare_configuration(worst, confirm_scope=True)
    assert len(result['questions']) == 211
    validate_shape(result, NEEDS_INPUT_SCHEMA)


@pytest.mark.parametrize('duration,sessions', [(180, 1), (270, 1), (271, 2), (300, 3)])
def test_duration_question_matches_domain_split_boundary(duration, sessions):
    from src.scheduling.course import SPLIT_THRESHOLD_MIN
    partial = request()
    del partial['courses'][0]['duration_min']
    questions = prepare_configuration(partial)['questions']
    assert str(SPLIT_THRESHOLD_MIN) in next(q['question'] for q in questions if q['path'].endswith('duration_min'))
    completed = request()
    completed['courses'][0].update(duration_min=duration, number_of_groups=1)
    assert prepare_configuration(completed)['session_count'] == sessions
