from copy import deepcopy
import sqlite3
import pytest
from src.application.edit_history import EditHistory, EditError, course_change, fingerprint
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


def state():
    return dict(excel_path=None, seed=42, classrooms={'R': Classroom('R', 30, 'REGULAR')},
                courses=[Course('BIO', 1, 60, 'REGULAR', size=20)], restrictions={},
                assignments={'BIO-G1': ('R', 1, 480, 540)}, pinned_group_ids=set(),
                lab_overrides=set(), schedule_present=True, classroom_course_map={})


def test_long_sequence_exact_undo_redo_and_new_branch():
    h = EditHistory(max_commands=60)
    current = state()
    states = [deepcopy(current)]
    saved = []
    for size in range(21, 51):
        candidate = deepcopy(current)
        candidate['courses'][0].size = size
        candidate['assignments'] = None
        candidate['schedule_present'] = False
        current = h.execute(current, candidate, saved.append, 'edit')
        states.append(deepcopy(current))
    for expected in reversed(states[:-1]):
        current = h.undo(current, saved.append)
        assert fingerprint(current) == fingerprint(expected)
    for expected in states[1:]:
        current = h.redo(current, saved.append)
        assert fingerprint(current) == fingerprint(expected)
    current = h.undo(current, saved.append)
    candidate = deepcopy(current)
    candidate['courses'][0].name = 'New branch'
    current = h.execute(current, candidate, saved.append, 'edit')
    assert not h.can_redo


def test_failure_keeps_command_and_exact_state(tmp_path):
    h = EditHistory()
    repo = SessionRepository(str(tmp_path/'session.db'))
    def save(data):
        repo.save_session(**{k: v for k, v in data.items() if k not in ('schedule_present', 'classroom_course_map')})
    original = state()
    save(original)
    candidate = course_change(original, [])
    current = h.execute(original, candidate, save, 'delete')
    def fail(_):
        raise sqlite3.OperationalError('disk full')
    with pytest.raises(sqlite3.OperationalError):
        h.undo(current, fail)
    assert h.can_undo and not h.can_redo
    assert fingerprint(current) == fingerprint(candidate)
    restored = h.undo(current, save)
    assert fingerprint(restored) == fingerprint(original)
    assert repo.load_session()['assignments'] == original['assignments']
    with pytest.raises(sqlite3.OperationalError):
        h.execute(restored, candidate, fail, 'delete')
    assert h.can_redo


def test_invalid_change_and_stale_history():
    h = EditHistory()
    current = state()
    changed = course_change(current, [])
    current = h.execute(current, changed, lambda _: None, 'delete')
    invalid = deepcopy(current)
    invalid['pinned_group_ids'] = {'missing'}
    with pytest.raises(EditError):
        h.execute(current, invalid, lambda _: pytest.fail('must not save'), 'invalid')
    assert h.can_undo
    external = deepcopy(current)
    external['seed'] = 11
    with pytest.raises(EditError, match='reinició'):
        h.undo(external, lambda _: pytest.fail('must not save'))
    assert not h.can_undo and not h.can_redo


def test_limits_off_on_and_reset():
    h = EditHistory(max_commands=2)
    current = state()
    for size in range(1, 5):
        target = deepcopy(current)
        target['courses'][0].size = size
        current = h.execute(current, target, lambda _: None, 'edit')
    assert len(h._undo) == 2
    assert not h.observe(current)  # hiding/showing unchanged data preserves history
    h.reset(current, 'import')
    assert not h.can_undo and h.reset_reason == 'import'
    target = course_change(current, [])
    current = h.execute(current, target, lambda _: None, 'delete', enabled=False)
    assert not h.can_undo and h.reset_reason == 'feature_disabled_change'
    small = EditHistory(max_bytes=1)
    with pytest.raises(EditError, match='memoria'):
        small.execute(state(), target, lambda _: pytest.fail('must not save'), 'delete')


def test_pin_lab_split_and_metadata_preserved():
    original = state()
    original['courses'][0].required_room_type = 'LAB'
    original['lab_overrides'] = {'BIO-G1'}
    original['pinned_group_ids'] = {'BIO-G1'}
    original['future_constraints'] = {'resource': 'preserve me'}
    modified = deepcopy(original['courses'])
    modified[0].name = 'Title'
    candidate = course_change(original, modified)
    assert candidate['assignments'] == original['assignments']
    assert candidate['lab_overrides'] == original['lab_overrides']
    assert candidate['future_constraints'] == original['future_constraints']
    modified[0].force_split = True
    with pytest.raises(EditError):
        course_change(original, modified)
    with pytest.raises(EditError):
        course_change(original, [])


def test_redo_validation_failure_does_not_consume_command():
    h = EditHistory()
    original = state()
    after = h.execute(original, course_change(original, []), lambda _: None, 'delete')
    restored = h.undo(after, lambda _: None)
    def reject(_):
        raise EditError('El cambio no es válido. Revise las asignaciones y las restricciones.')
    h.validator = reject
    with pytest.raises(EditError):
        h.redo(restored, lambda _: pytest.fail('Must not save invalid target'))
    assert h.can_redo and not h.can_undo


def test_byte_limit_evicts_oldest_commands_without_exceeding_bound():
    from src.application.edit_history import encoded
    original = state()
    target = deepcopy(original)
    target['courses'][0].name = 'First'
    cost = len(encoded(original)) + len(encoded(target))
    h = EditHistory(max_bytes=cost + 100)
    current = h.execute(original, target, lambda _: None, 'one')
    target = deepcopy(current)
    target['courses'][0].name = 'Second'
    current = h.execute(current, target, lambda _: None, 'two')
    assert len(h._undo) == 1 and h.bytes_used <= h.max_bytes
    current = h.undo(current, lambda _: None)
    assert current['courses'][0].name == 'First'
    assert not h.can_undo and h.can_redo


def test_group_feedback_normalization_is_detached_idempotent_and_preserves_sources():
    from src.application.edit_history import normalized_group_feedback
    from src.scheduling.validation import ValidationNotice

    candidate = state()
    candidate['courses'][0].number_of_groups = 4
    saved_reason = ValidationNotice('Synthetic reason for {gid}', gid='BIO-G2')
    candidate['group_feedback'] = {'BIO-G1': 'stale assigned reason', 'BIO-G2': saved_reason,
                                   'BIO-G3': '', 'removed-session': 'stale'}
    before = fingerprint(candidate)
    feedback = normalized_group_feedback(candidate)
    assert feedback['BIO-G1'] == ''
    assert feedback['BIO-G2'] is saved_reason
    assert feedback['BIO-G3'] == ''
    assert feedback['BIO-G4']
    assert 'removed-session' not in feedback
    assert fingerprint(candidate) == before
    assert normalized_group_feedback({**candidate, 'group_feedback': feedback}) == feedback
    assert normalized_group_feedback({**candidate, 'schedule_present': False}) == {}
