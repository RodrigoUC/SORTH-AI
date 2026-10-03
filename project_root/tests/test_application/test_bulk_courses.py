from copy import deepcopy
import pytest
from src.application.bulk_courses import preview_bulk, apply_bulk
from src.application.edit_history import EditHistory, EditError, fingerprint
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


def state():
    return dict(excel_path=None, seed=42, classrooms={'R': Classroom('R', 50, 'REGULAR')},
                courses=[Course('BIO', 1, 60, 'REGULAR', size=20, preferred_day='Lunes',
                                group_suggestions=[{'preferred_day': 'Martes'}]),
                         Course('CHEM', 1, 60, 'REGULAR', size=30), Course('OTHER', 1, 60, 'REGULAR')],
                restrictions={'R': {'BIO', 'CHEM', 'OTHER'}}, assignments={'BIO-G1': ('R', 1, 480, 540)},
                pinned_group_ids=set(), lab_overrides=set(), schedule_present=True)


def test_only_selected_fields_identity_one_command_and_preview():
    before = state()
    plan = preview_bulk(before, ('BIO', 'CHEM'), {'size': 40, 'preferred_day': None})
    assert plan.removed_assignments == ('BIO-G1',)
    assert len(plan.changes) == 3
    history = EditHistory()
    saves = []
    after = apply_bulk(history, before, plan, ('BIO', 'CHEM'), saves.append, True)
    assert len(saves) == 1 and len(history._undo) == 1
    assert vars(after['courses'][2]) == vars(before['courses'][2])
    assert after['courses'][0].group_suggestions == before['courses'][0].group_suggestions
    assert [c.code for c in after['courses']] == [c.code for c in before['courses']]
    assert after['restrictions'] == before['restrictions']
    for _ in range(3):
        restored = history.undo(after, saves.append)
        assert fingerprint(restored) == fingerprint(before)
        after = history.redo(restored, saves.append)
    assert after['courses'][0].size == 40


@pytest.mark.parametrize('selected,fields', [
    ((), {'size': 20}), (('MISSING',), {'size': 20}), (('BIO', 'BIO'), {'size': 20}),
    (('BIO',), {}), (('BIO',), {'code': 'new'}), (('BIO',), {'size': -1}),
    (('BIO',), {'size': True}), (('BIO',), {'preferred_day': 'Sunday'}),
    (('BIO',), {'required_room_type': 'ANY'}), (('BIO',), {'size': 20})])
def test_invalid_and_noop_never_mutate(selected, fields):
    current = state()
    original = fingerprint(current)
    with pytest.raises(EditError):
        preview_bulk(current, selected, fields)
    assert fingerprint(current) == original


def test_stale_selection_state_disabled_failure_and_tampered_candidate():
    current = state()
    plan = preview_bulk(current, ('BIO',), {'size': 25})
    h = EditHistory()
    for selected, enabled in [(('CHEM',), True), (('BIO',), False)]:
        with pytest.raises(EditError):
            apply_bulk(h, current, plan, selected, lambda _: pytest.fail('No save'), enabled)
    changed = deepcopy(current)
    changed['seed'] = 1
    with pytest.raises(EditError):
        apply_bulk(h, changed, plan, ('BIO',), lambda _: pytest.fail('No save'), True)
    def fail(_):
        raise OSError('disk full')
    with pytest.raises(OSError):
        apply_bulk(h, current, plan, ('BIO',), fail, True)
    assert not h.can_undo
    # A detached UI preview cannot inject unchecked changes into the command.
    plan.candidate['courses'][0].code = 'TAMPERED'
    after = apply_bulk(h, current, plan, ('BIO',), lambda _: None, True)
    assert after['courses'][0].code == 'BIO'


def test_pin_capacity_lab_and_split_safety():
    current = state()
    current['pinned_group_ids'] = {'BIO-G1'}
    good = preview_bulk(current, ('BIO',), {'preferred_day': None})
    assert good.preserved_pins == ('BIO-G1',)
    assert good.candidate['assignments'] == current['assignments']
    for fields in ({'size': 51}, {'required_room_type': 'LAB'}):
        with pytest.raises(EditError):
            preview_bulk(current, ('BIO',), fields)
    current['courses'][0].duration_min = 300
    current['assignments'] = {'BIO-G1-P1': ('R', 1, 480, 600), 'BIO-G1-P2': ('R', 2, 480, 600)}
    current['pinned_group_ids'] = {'BIO-G1-P1', 'BIO-G1-P2'}
    plan = preview_bulk(current, ('BIO',), {'size': 25})
    assert plan.candidate['assignments'] == current['assignments']
