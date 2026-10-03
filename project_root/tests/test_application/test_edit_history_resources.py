"""Cross-feature contract, executed when the resource follow-on is integrated."""
from copy import deepcopy
from dataclasses import replace
import pytest
resources_module = pytest.importorskip('src.scheduling.teaching_resources',
    reason='Resource follow-on is not part of the standalone undo/bulk baseline')
from src.application.edit_history import EditHistory, EditError, course_change, fingerprint
from src.application.bulk_courses import preview_bulk, apply_bulk
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom


def resource_state(kind, enabled):
    Resource = resources_module.Resource
    ResourceCatalog = resources_module.ResourceCatalog
    SchedulingResources = resources_module.SchedulingResources
    return dict(excel_path=None, seed=42,
        classrooms={'R': Classroom('R', 30, 'REGULAR'), 'S': Classroom('S', 30, 'REGULAR')},
        courses=[Course('BIO', 1, 60, 'REGULAR', size=20), Course('CHEM', 1, 60, 'REGULAR', size=20)],
        restrictions={}, assignments={'BIO-G1': ('R', 1, 480, 540)}, pinned_group_ids=set(),
        lab_overrides=set(), schedule_present=True,
        resources=SchedulingResources((ResourceCatalog(kind, enabled,
            (Resource('r1', 'Synthetic resource', ((1, 480, 660),)),),
            (('BIO-G1', ('r1',)), ('CHEM-G1', ('r1',)))),)))


@pytest.mark.parametrize('kind', resources_module.RESOURCE_KINDS)
@pytest.mark.parametrize('enabled', [True, False])
def test_undo_bulk_preserves_every_resource_value(kind, enabled):
    before = resource_state(kind, enabled)
    expected = before['resources'].to_data()
    history = EditHistory()
    plan = preview_bulk(before, ('BIO',), {'size': 22})
    after = apply_bulk(history, before, plan, ('BIO',), lambda _: None, True)
    assert after['resources'].to_data() == expected
    for _ in range(3):
        restored = history.undo(after, lambda _: None)
        assert fingerprint(restored) == fingerprint(before)
        assert restored['resources'].to_data() == expected
        after = history.redo(restored, lambda _: None)
        assert after['resources'].to_data() == expected


@pytest.mark.parametrize('kind', resources_module.RESOURCE_KINDS)
def test_resource_orphans_and_active_constraints_rejected_atomically(kind):
    before = resource_state(kind, True)
    history = EditHistory()
    with pytest.raises(EditError):
        course_change(before, before['courses'][1:])
    split = deepcopy(before['courses'])
    split[0].force_split = True
    with pytest.raises(EditError):
        course_change(before, split)
    for placement in [('S', 1, 500, 560), ('S', 2, 480, 540)]:
        candidate = deepcopy(before)
        candidate['assignments']['CHEM-G1'] = placement
        with pytest.raises(EditError):
            history.execute(before, candidate, lambda _: pytest.fail('Must not save'), 'manual')
    assert not history.can_undo
