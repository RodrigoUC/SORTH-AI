"""Compare final validation against the unchanged, unindexed admission rule."""
import random
import pytest

from src.scheduling.course import Course
from src.scheduling.teaching_resources import Resource, ResourceCatalog, RESOURCE_KINDS
from src.scheduling.time_model import TimeModel


def reference(catalog, assignments, groups, time_model):
    issues = catalog.structure_issues({g.group_id for g in groups}, time_model)
    if issues:
        return issues
    seen = {}
    for gid, placement in assignments.items():
        if (isinstance(placement, (tuple, list)) and len(placement) == 4
                and all(type(v) is int for v in placement[1:])):
            _, day, start, end = placement
            issues.extend(catalog.placement_issues(gid, day, start, end, seen))
            seen[gid] = placement
    return issues


@pytest.mark.parametrize('kind', RESOURCE_KINDS)
@pytest.mark.parametrize('enabled', (True, False))
def test_index_preserves_exact_notice_order_across_seeded_fixtures(kind, enabled):
    groups = [Course(f'C{i}', 1, 60, 'REGULAR').generate_groups()[0] for i in range(60)]
    tm = TimeModel.default()
    for seed in range(30):
        rng = random.Random(seed)
        resources = tuple(Resource(f'R{i}', f'Resource {i}',
                          (None, (), ((1, 420, 510), (1, 510, 600)), ((2, 480, 540),))[i % 4])
                          for i in range(8))
        memberships = tuple((g.group_id,
            None if i % 11 == 0 else tuple(rng.sample([r.id for r in resources],
                rng.randrange(2 if kind == 'teacher' else 4)))) for i, g in enumerate(groups))
        catalog = ResourceCatalog(kind, enabled, resources, memberships)
        shuffled = list(groups)
        rng.shuffle(shuffled)
        assignments = {}
        for i, group in enumerate(shuffled):
            start = 420 + 30 * rng.randrange(7)
            assignments[group.group_id] = ('Room', rng.randrange(1, 4), start, start + 60)
            if i % 13 == 0:
                assignments[group.group_id] = ('Room', True, start, start + 60)
            elif i % 17 == 0:
                assignments[group.group_id] = ('malformed',)
        assert catalog.validate(assignments, groups, tm) == reference(catalog, assignments, groups, tm)
        # Validation must not retain buckets across edits/removals or new calls.
        assignments.pop(shuffled[1].group_id)
        assignments[shuffled[2].group_id] = ('Other', 1, 420, 480)
        assert catalog.validate(assignments, groups, tm) == reference(catalog, assignments, groups, tm)


def test_index_avoids_unrelated_resource_membership_scans(monkeypatch):
    groups = [Course(f'C{i}', 1, 60, 'REGULAR').generate_groups()[0] for i in range(200)]
    catalog = ResourceCatalog('teacher', True,
        tuple(Resource(f'T{i}', f'Teacher {i}') for i in range(len(groups))),
        tuple((g.group_id, (f'T{i}',)) for i, g in enumerate(groups)))
    calls = 0
    original = ResourceCatalog.ids_for
    def counted(self, group_id):
        nonlocal calls
        calls += 1
        return original(self, group_id)
    monkeypatch.setattr(ResourceCatalog, 'ids_for', counted)
    assignments = {g.group_id: ('Room', 1, 420, 480) for g in groups}
    assert catalog.validate(assignments, groups, TimeModel.default()) == []
    assert calls <= 3 * len(groups)


def test_index_does_not_hide_structure_errors_for_disabled_catalogs():
    group = Course('C', 1, 60, 'REGULAR').generate_groups()[0]
    catalog = ResourceCatalog('teacher', False, (Resource('T', 'Teacher'),),
                              ((group.group_id, ('missing',)),))
    assert catalog.validate({}, [group], TimeModel.default()) == reference(
        catalog, {}, [group], TimeModel.default())
    assert catalog.validate({}, [group], TimeModel.default())[0].code == 'UNKNOWN_RESOURCE_REFERENCE'
