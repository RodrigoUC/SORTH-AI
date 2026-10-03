from copy import deepcopy
import pytest

from src.application import edit_history as history
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.project_calendar import ProjectCalendar
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources


def states():
    before = dict(excel_path=None, seed=42, classrooms={'R': Classroom('R', 30, 'REGULAR')},
        courses=[Course('C', 1, 60, 'REGULAR', size=20)], restrictions={},
        assignments={'C-G1': ('R', 1, 480, 540)}, pinned_group_ids={'C-G1'},
        lab_overrides=set(), calendar=ProjectCalendar(),
        resources=SchedulingResources((ResourceCatalog('teacher', True,
            (Resource('T', 'Teacher'),), (('C-G1', ('T',)),)),)),
        future_constraints={'unordered': {'Z', 'A'}})
    after = deepcopy(before)
    after['courses'][0].name = 'Changed'
    return before, after


@pytest.mark.parametrize('enabled', (True, False))
def test_execute_encodes_each_snapshot_once_and_preserves_expected_digest(monkeypatch, enabled):
    before, after = states()
    expected_digest = history.fingerprint(after)
    expected_bytes = len(history.encoded(before)) + len(history.encoded(after))
    original = history.encoded
    calls = []
    def counted(state):
        calls.append(state)
        return original(state)
    monkeypatch.setattr(history, 'encoded', counted)
    h = history.EditHistory()
    accepted = h.execute(before, after, lambda _: None, 'rename', enabled=enabled)
    assert len(calls) == 2
    assert h._expected == expected_digest
    assert h.bytes_used == (expected_bytes if enabled else 0)
    assert h.reset_reason == (None if enabled else 'feature_disabled_change')
    assert history.fingerprint(accepted) == expected_digest


def test_transaction_reuse_never_shares_mutable_snapshots():
    before, after = states()
    expected_before, expected_after = history.fingerprint(before), history.fingerprint(after)
    h = history.EditHistory()
    def persist(data):
        data['courses'][0].name = 'Mutated persistence argument'
        data['assignments'].clear()
    accepted = h.execute(before, after, persist, 'rename')
    before['courses'][0].name = 'Changed caller before'
    after['courses'][0].name = 'Changed caller after'
    accepted['assignments'].clear()
    assert history.fingerprint(h._undo[0].before) == expected_before
    assert history.fingerprint(h._undo[0].after) == expected_after
    assert h._expected == expected_after


def test_out_of_band_observe_encodes_once_and_invalidates_both_stacks(monkeypatch):
    before, after = states()
    h = history.EditHistory()
    accepted = h.execute(before, after, lambda _: None, 'rename')
    h.undo(accepted, lambda _: None)
    assert h.can_redo
    external = deepcopy(before)
    external['seed'] = 7
    expected = history.fingerprint(external)
    original = history.encoded
    calls = 0
    def counted(state):
        nonlocal calls
        calls += 1
        return original(state)
    monkeypatch.setattr(history, 'encoded', counted)
    assert h.observe(external)
    assert calls == 1
    assert h._expected == expected
    assert not h.can_undo and not h.can_redo
    assert h.reset_reason == 'external_change'


def test_failed_persist_does_not_publish_precomputed_fingerprints():
    before, after = states()
    h = history.EditHistory()
    h.reset(before)
    expected = h._expected
    def fail(_):
        raise OSError('Disk full')
    with pytest.raises(OSError, match='Disk full'):
        h.execute(before, after, fail, 'rename')
    assert h._expected == expected
    assert not h.can_undo and not h.can_redo


def test_noop_still_validates_returns_detached_state_and_does_not_save():
    before, _ = states()
    validations = []
    h = history.EditHistory(validator=validations.append)
    result = h.execute(before, before, lambda _: pytest.fail('No-op saved'), 'noop')
    assert len(validations) == 1
    result['courses'][0].name = 'Detached'
    assert before['courses'][0].name is None
    assert not h.can_undo and not h.can_redo
