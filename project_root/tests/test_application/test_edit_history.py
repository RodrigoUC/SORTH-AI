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
