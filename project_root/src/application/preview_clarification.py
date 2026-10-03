"""Bounded draft intake for an AI host; never infer missing academic inputs."""
from copy import deepcopy

from .preview_contract import (INPUT_SCHEMA, OUTPUT_SCHEMA, ERROR_SCHEMA, CAPABILITIES,
                               ContractError, array, obj, validate_shape)
from .schedule_preview import validate_configuration
from ..scheduling.course import SPLIT_THRESHOLD_MIN


def _draft(schema):
    result = deepcopy(schema)
    if result['type'] == 'object':
        result['required'] = []
        result['properties'] = {key: _draft(value) for key, value in result['properties'].items()}
    elif result['type'] == 'array':
        result['minItems'] = 0
        result['items'] = _draft(result['items'])
    return result


DRAFT_SCHEMA = _draft(INPUT_SCHEMA)
PREPARATION_SCHEMA = deepcopy(DRAFT_SCHEMA)
PREPARATION_SCHEMA['properties']['scope_confirmed'] = {'type': 'boolean'}
QUESTION_SCHEMA = obj({
    'path': {'type': 'string', 'maxLength': 256},
    'question': {'type': 'string', 'maxLength': 512},
})
NEEDS_INPUT_SCHEMA = obj({
    'status': {'type': 'string', 'enum': ['needs_input']},
    'questions': array(QUESTION_SCHEMA, 256, 1),
    'next_action': {'type': 'string', 'enum': ['ask_user_then_resubmit']},
    'message': {'type': 'string', 'maxLength': 512},
    'capabilities': array({'type': 'string', 'enum': CAPABILITIES}, len(CAPABILITIES)),
})
CLARIFICATION_OUTPUT_SCHEMA = {'type': 'object', 'oneOf': [OUTPUT_SCHEMA, NEEDS_INPUT_SCHEMA, ERROR_SCHEMA]}

_QUESTIONS = {
    'courses': 'Which courses and groups should be scheduled? Provide the known course codes and details.',
    'classrooms': 'Which rooms may be used? Provide their identifiers, capacities and LAB or REGULAR types.',
    'seed': 'Which reproducible scheduling seed should be used? The host may propose 42 for your confirmation; this is an algorithm setting, not an academic requirement.',
    'code': 'What is the course code?',
    'number_of_groups': 'How many groups does this course have? Each group receives the specified weekly duration.',
    'duration_min': f'How many total teaching minutes per week does each group need? By default, durations over {SPLIT_THRESHOLD_MIN} minutes are split by SORTH; force_split can override this. Confirm the intended session pattern before submitting.',
    'required_room_type': 'Does this course require a LAB or a REGULAR classroom?',
    'size': 'How many students must fit in each group?',
    'name': 'What is the classroom identifier?',
    'capacity': 'What is the capacity of this classroom?',
    'room_type': 'Is this classroom a LAB or REGULAR room?',
    'classroom': 'Which provided classroom does this restriction apply to?',
    'allowed_courses': 'Which provided courses may use this classroom? An empty list blocks all courses.',
    'classroom_restrictions': 'Are any rooms restricted to particular courses? Provide those rules, or an explicit empty list if none apply.',
    'scope_confirmed': 'Confirm the supported timetable: Monday–Saturday, 07:00–22:00, lunch 12:00–13:00; day/time preferences are soft. Are there required days, times, session patterns, teacher/cohort conflicts or availability rules beyond this? Unsupported mandatory rules must not be ignored.',
}


def _missing(value, schema, path='request'):
    questions = []
    if schema['type'] == 'object':
        for key in schema['required']:
            if key not in value:
                questions.append({'path': f'{path}.{key}', 'question': _QUESTIONS[key]})
        for key, child in value.items():
            questions.extend(_missing(child, schema['properties'][key], f'{path}.{key}'))
    elif schema['type'] == 'array':
        if len(value) < schema['minItems']:
            questions.append({'path': path, 'question': _QUESTIONS[path.split('.')[-1]]})
        for index, child in enumerate(value):
            questions.extend(_missing(child, schema['items'], f'{path}[{index}]'))
    return questions


def prepare_configuration(request, *, confirm_scope=False):
    """Validate every supplied value before collecting all absent required fields.

    The host owns the conversation and resubmission. No elicitation capability,
    model, persistence, or session state is required or silently introduced.
    """
    schema = PREPARATION_SCHEMA if confirm_scope else DRAFT_SCHEMA
    validate_shape(request, schema)
    data = {key: deepcopy(value) for key, value in request.items() if key != 'scope_confirmed'}
    required = deepcopy(INPUT_SCHEMA)
    if confirm_scope:
        required['required'].append('classroom_restrictions')
    questions = _missing(data, required)
    if confirm_scope:
        if request.get('scope_confirmed') is False:
            raise ContractError('UNSUPPORTED_CONSTRAINTS', 'request.scope_confirmed',
                                'The supported timetable was not confirmed. Clarify required days, availability, session patterns and other hard rules; do not generate or claim to satisfy unsupported rules.')
        if 'scope_confirmed' not in request:
            questions.append({'path': 'request.scope_confirmed', 'question': _QUESTIONS['scope_confirmed']})
    if questions:
        result = {'status': 'needs_input', 'questions': questions,
                  'next_action': 'ask_user_then_resubmit',
                  'message': 'Ask only the necessary clarifications in the user\'s language. Group shared questions and batch course details; do not paste a long field list into chat. Shared defaults or session patterns require explicit user confirmation. Preserve supplied facts and resubmit completed data. No timetable or file was generated.',
                  'capabilities': list(CAPABILITIES)}
        validate_shape(result, NEEDS_INPUT_SCHEMA, 'result')
        return result
    return validate_configuration(data)
