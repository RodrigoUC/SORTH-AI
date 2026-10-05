"""Changed repeated-course review detects ambiguity without inferring a remap."""
from copy import deepcopy

import pytest

from src.application.reimport_identity import affected_identity_groups
from src.scheduling.course import Course
from src.scheduling.teaching_resources import (
    RESOURCE_KINDS, Resource, ResourceCatalog, SchedulingResources,
)


ALPHA = {'aula': 'R1', 'preferred_day': 'Lunes', 'preferred_start_min': 480}
BETA = {'aula': 'R2', 'preferred_day': 'Martes', 'preferred_start_min': 600}
GAMMA = {'aula': 'R3', 'preferred_day': 'Miércoles', 'preferred_start_min': 720}


def course(code='BIO', suggestions=None, **changes):
    suggestions = [ALPHA, BETA] if suggestions is None else suggestions
    values = dict(code=code, number_of_groups=len(suggestions), duration_min=60,
                  required_room_type='REGULAR', group_suggestions=deepcopy(suggestions))
    values.update(changes)
    return Course(**values)


def resources(*group_ids, kind='teacher', enabled=True):
    return SchedulingResources((ResourceCatalog(
        kind, enabled, (Resource('r1', 'Synthetic resource'),),
        tuple((group_id, ('r1',)) for group_id in group_ids)),))


def affected(old, new, linked=('BIO-G1', 'BIO-G2'), pins=()):
    return affected_identity_groups([old], [new], resources(*linked), pins)


@pytest.mark.parametrize('suggestions', [
    [BETA, ALPHA],                    # Row reorder.
    [GAMMA, ALPHA, BETA],             # Insertion before existing ordinals.
    [BETA],                          # Deletion keeps an ambiguous G1.
    [ALPHA, GAMMA],                   # Replacement may look like a preference edit.
])
def test_reorder_insertion_deletion_and_edit_review_all_linked_old_ordinals(suggestions):
    assert affected(course(), course(suggestions=suggestions)) == ('BIO-G1', 'BIO-G2')


def test_changed_course_includes_unchanged_linked_group():
    # G1 has equal generated properties, but another row changed. Equal values
    # do not establish that a resource's source-row identity was preserved.
    assert affected(course(), course(suggestions=[ALPHA, GAMMA]),
                    linked=('BIO-G1',)) == ('BIO-G1',)


def test_ordered_explicit_suggestions_matter_even_when_effective_groups_are_equal():
    old = course(suggestions=[{}, {'aula': 'R1'}], suggested_classroom='R1')
    new = course(suggestions=[{'aula': 'R1'}, {}], suggested_classroom='R1')
    assert [vars(g) for g in old.generate_groups()] == [vars(g) for g in new.generate_groups()]
    assert affected(old, new) == ('BIO-G1', 'BIO-G2')


@pytest.mark.parametrize('changes', [
    {'duration_min': 90},
    {'required_room_type': 'LAB'},
    {'size': 20},
    {'suggested_classroom': 'R2'},
    {'preferred_day': 'Martes'},
    {'preferred_start_min': 600},
    {'force_split': True},
])
def test_effective_generated_properties_require_review_with_equal_row_suggestions(changes):
    old = course(suggestions=[{}, {}])
    new = course(suggestions=[{}, {}], **changes)
    assert old.group_suggestions == new.group_suggestions
    assert affected(old, new) == ('BIO-G1', 'BIO-G2')


@pytest.mark.parametrize('old_count,new_count', [(1, 2), (2, 1), (2, 3), (3, 2)])
def test_count_change_uses_repeated_status_from_either_version(old_count, new_count):
    old = course(suggestions=[ALPHA] * old_count)
    new = course(suggestions=[ALPHA] * new_count)
    old_ids = tuple(f'BIO-G{i}' for i in range(1, old_count + 1))
    assert affected(old, new, linked=old_ids) == old_ids


def test_split_change_returns_exact_old_part_ids_including_disappearing_parts():
    old = course(duration_min=360)
    new = course(duration_min=300)
    assert affected(old, new, linked=('BIO-G1-P2',),
                    pins={'BIO-G2-P3'}) == ('BIO-G1-P2', 'BIO-G2-P3')
    unsplit = course(duration_min=360, force_split=False)
    assert affected(old, unsplit, linked=('BIO-G1-P2',),
                    pins={'BIO-G2-P3'}) == ('BIO-G1-P2', 'BIO-G2-P3')


@pytest.mark.parametrize('kind', RESOURCE_KINDS)
@pytest.mark.parametrize('enabled', [False, True])
def test_every_resource_catalog_counts_even_when_inactive(kind, enabled):
    result = affected_identity_groups(
        [course()], [course(suggestions=[BETA, ALPHA])],
        resources('BIO-G2', kind=kind, enabled=enabled), ())
    assert result == ('BIO-G2',)


def test_pins_alone_require_review_and_output_is_deduplicated_and_sorted():
    old = [course(code='ZZZ'), course(code='AAA')]
    new = [course(code='AAA', duration_min=90), course(code='ZZZ', duration_min=90)]
    catalogs = resources('ZZZ-G2').with_catalog(
        ResourceCatalog('student', False, (Resource('s1', 'Synthetic student'),),
                        (('ZZZ-G2', ('s1',)),)))
    pins = ['ZZZ-G2', 'AAA-G2', 'ZZZ-G1', 'AAA-G2']
    assert affected_identity_groups(old, new, catalogs, pins) == ('AAA-G2', 'ZZZ-G1', 'ZZZ-G2')
    assert affected_identity_groups(old, new, SchedulingResources(), {'AAA-G1'}) == ('AAA-G1',)


@pytest.mark.parametrize('code', ['BIO-G1', 'BIO-G1-P2', 'BIO-Gx-Pz', 'A-B / C', '生物-G1'])
def test_course_codes_are_not_parsed_from_group_ids(code):
    old = [course(code), course('BIO')]
    new = [course(code, duration_min=90), course('BIO')]
    linked = resources(f'{code}-G1', f'{code}-G2', 'BIO-G1', 'BIO-G2')
    expected = tuple(sorted((f'{code}-G1', f'{code}-G2')))
    assert affected_identity_groups(old, new, linked, ()) == expected


def test_unrelated_changes_do_not_trigger_review_of_unchanged_linked_course():
    old = [course(), course('CHEM')]
    new = [course('CHEM', duration_min=90), course()]
    assert affected_identity_groups(old, new, resources('BIO-G1'), {'BIO-G2'}) == ()


@pytest.mark.parametrize('changes', [{}, {'name': 'New display name'}])
def test_unchanged_input_and_display_only_name_changes_do_not_warn(changes):
    assert affected(course(), course(**changes), pins={'BIO-G1'}) == ()


def test_indistinguishable_normalized_row_permutations_cannot_be_detected():
    old = course(suggestions=[ALPHA, ALPHA])
    new = course(suggestions=list(reversed(old.group_suggestions)))
    assert affected(old, new, pins={'BIO-G1'}) == ()


@pytest.mark.parametrize('old_duration,new_duration', [(60, 90), (360, 300)])
def test_unique_course_does_not_warn_even_if_split_into_multiple_parts(old_duration, new_duration):
    old = course(suggestions=[ALPHA], duration_min=old_duration)
    new = course(suggestions=[BETA], duration_min=new_duration)
    linked = tuple(g.group_id for g in old.generate_groups())
    assert affected(old, new, linked=linked, pins=linked) == ()


def test_courses_added_or_entirely_removed_are_left_to_existing_orphan_review():
    assert affected_identity_groups([course()], [course('NEW')],
                                    resources('BIO-G1', 'NEW-G1'), {'BIO-G2'}) == ()


def test_empty_memberships_and_unknown_ids_do_not_count_as_saved_associations():
    catalogs = SchedulingResources((ResourceCatalog(memberships=(
        ('BIO-G1', None), ('BIO-G2', ()), ('BIO-G3', ('r1',)),
    )),))
    assert affected_identity_groups([course()], [course(duration_min=90)],
                                    catalogs, {'BIO-G99'}) == ()
    assert affected_identity_groups([course()], [course(duration_min=90)],
                                    SchedulingResources(), ()) == ()


def test_unused_suggestion_tail_and_non_preference_keys_do_not_warn():
    old = course()
    new = course(suggestions=[{**ALPHA, 'source_row': 12}, BETA, GAMMA], number_of_groups=2)
    assert affected(old, new) == ()


def test_missing_and_empty_suggestions_normalize_equally():
    old = course(suggestions=[], number_of_groups=2)
    new = course(suggestions=[{}, {'aula': None, 'preferred_day': None,
                                  'preferred_start_min': None}])
    assert affected(old, new) == ()


def test_zero_start_minute_is_a_real_preference():
    old = course(suggestions=[{}, {}], preferred_start_min=0)
    new = course(suggestions=[{'preferred_start_min': 0}, {}], preferred_start_min=0)
    assert affected(old, new) == ('BIO-G1', 'BIO-G2')


def test_ineffective_fallback_and_split_override_changes_do_not_warn():
    old = course(suggested_classroom='R1', preferred_day='Lunes', preferred_start_min=480)
    new = course(suggested_classroom='R9', preferred_day='Viernes', preferred_start_min=900,
                 force_split=False)
    assert affected(old, new) == ()


def test_detector_does_not_mutate_courses_catalogs_or_pins():
    old, new = [course(duration_min=360)], [course(duration_min=300)]
    catalogs = resources('BIO-G1-P1', enabled=False)
    pins = {'BIO-G2-P3'}
    before = deepcopy(([vars(c) for c in old], [vars(c) for c in new],
                       [vars(c) for c in catalogs.catalogs], pins))
    assert affected_identity_groups(iter(old), iter(new), catalogs, pins) == ('BIO-G1-P1', 'BIO-G2-P3')
    after = ([vars(c) for c in old], [vars(c) for c in new],
             [vars(c) for c in catalogs.catalogs], pins)
    assert after == before
