"""Independent arithmetic oracles; no scheduler scoring helpers used."""
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import pytest
from benchmark import run_once
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.group import Group
from src.scheduling.quality import QualitySnapshot, analyze_quality
from src.scheduling.time_model import TimeModel


@pytest.fixture
def example():
    data = json.loads((Path(__file__).parents[1] / 'fixtures/quality/partial_schedule.json').read_text())
    courses = [Course(**row) for row in data['courses']]
    groups = [g for c in courses for g in c.generate_groups()]
    for g in groups:
        g.lab_override = g.group_id in data['lab_overrides']
    rooms = {name: Classroom(name, 30, kind) for name, kind in data['rooms'].items()}
    tm = TimeModel(data['days'], data['day_start'], data['day_end'])
    return data['assignments'], groups, tm, rooms, courses


def measure(example):
    return analyze_quality(QualitySnapshot.capture(*example[:4]))


def test_partial_fixture_independent_denominators(example):
    r = measure(example)
    assert r['coverage'] == dict(sessions=5, assigned_sessions=4, pending_sessions=1,
        assigned_ratio=.8, original_groups=dict(total=4, fully_assigned=3, partially_assigned=1,
                                               unassigned=0, unknown=0), unknown_assignment_ids=[])
    for kind, satisfied in [('day', 1), ('time', 2), ('room', 1)]:
        assert r['preferences'][kind] == dict(requested=3, absent=2, pending=1, unknown=0,
            evaluated=2, satisfied=satisfied, unsatisfied=2-satisfied, ratio=satisfied/2)
    assert [row['teaching_minutes'] for row in r['day_load']] == [180, 120]
    assert [row['assigned_sessions'] for row in r['day_load']] == [2, 2]
    assert [row['teaching_minutes_ratio'] for row in r['day_load']] == [.6, .4]
    assert r['occupancy']['available_minutes'] == 2 * 2 * (420 - 60)
    assert r['occupancy']['occupied_minutes'] == 300
    assert r['occupancy']['ratio'] == 300 / 1440
    assert [row['occupied_minutes'] for row in r['occupancy']['rooms']] == [240, 60]
    assert r['manual_exceptions']['active_ids'] == ['LAB-G1']
    assert r['manual_exceptions']['active_ratio'] == .25
    assert r['data_issues'] == []
    assert r['validity'] == 'not_evaluated'
    json.dumps(r, allow_nan=False)


def test_same_coverage_can_hide_quality_regression(example):
    old = measure(example)
    example[0]['C-G1'] = ['B', 2, 485, 545]
    edited = measure(example)
    assert old['coverage'] == edited['coverage']
    assert edited['preferences']['day']['ratio'] == 0
    assert edited['preferences']['room']['ratio'] == 0
    assert edited['preferences']['time']['ratio'] == .5


def test_analysis_pure_and_snapshot_detached(example):
    assignments, groups, tm, rooms, _ = example
    before = copy.deepcopy((assignments, [g.__dict__ for g in groups], tm.__dict__,
                            {k: v.__dict__ for k, v in rooms.items()}))
    snap = QualitySnapshot.capture(assignments, groups, tm, rooms)
    first = analyze_quality(snap)
    assert before == (assignments, [g.__dict__ for g in groups], tm.__dict__, {k:v.__dict__ for k,v in rooms.items()})
    assignments['C-G1'][2] = 600
    groups[0].preferred_day = 'Martes'
    groups[0].assignment = ('B', 2, 600, 660)
    rooms['A'].room_type = 'LAB'
    rooms['A'].occupy(1, 420, 1320)
    tm.index_to_day[1] = 'Changed'
    assert analyze_quality(snap) == first
    with pytest.raises(FrozenInstanceError):
        snap.day_start = 0
    first['preferences']['day']['ratio'] = 999
    assert analyze_quality(snap)['preferences']['day']['ratio'] == .5


def test_empty_known_inventory():
    r = analyze_quality(QualitySnapshot.capture({}, [], TimeModel.default(), {'A': Classroom('A', 30, 'REGULAR')}))
    assert r['coverage']['assigned_ratio'] is None
    assert r['preferences']['day']['ratio'] is None
    assert r['occupancy']['ratio'] == 0
    assert r['occupancy']['available_minutes'] == 6 * 840
    assert len(r['day_load']) == 6
    assert all(row['assigned_sessions'] == 0 and row['teaching_minutes_ratio'] is None for row in r['day_load'])


@pytest.mark.parametrize('rooms', [None, {}])
def test_unknown_or_empty_inventory(rooms):
    r = analyze_quality(QualitySnapshot.capture({}, [], TimeModel.default(), rooms))
    assert r['occupancy']['ratio'] is None
    assert r['occupancy']['inventory_known'] is (rooms is not None)


def test_union_minutes_exclude_lunch_and_overlapping_blocks():
    tm = TimeModel(['Lunes'], 600, 900)
    rooms = {'A': Classroom('A', 30, 'REGULAR')}
    slots = {'a': ('A', 1, 630, 810), 'b': ('A', 1, 650, 850)}
    groups = [Group('a', 180, 'REGULAR'), Group('b', 200, 'REGULAR')]
    snap = QualitySnapshot.capture(slots, groups, tm, rooms,
        room_exclusions={('A', 1): [(650, 700), (680, 730), (800, 820)]})
    r = analyze_quality(snap)
    # Available: 600-650,780-800,820-900 = 150; occupied:630-650,780-800,820-850 = 70.
    assert r['occupancy']['available_minutes'] == 150
    assert r['occupancy']['occupied_minutes'] == 70
    assert r['day_load'][0]['teaching_minutes'] == 380
    assert r['occupancy']['ratio'] == 70 / 150


def test_all_time_excluded_not_applicable():
    tm = TimeModel(['Lunes'], 720, 780)
    r = analyze_quality(QualitySnapshot.capture({}, [], tm, {'A': Classroom('A', 1, 'REGULAR')}))
    assert r['occupancy']['available_minutes'] == 0 and r['occupancy']['ratio'] is None


def test_unknown_targets_not_failures_or_successes():
    g = Group('G', 60, 'LAB', suggested_classroom='missing', preferred_day='Sunday', preferred_start_min=1400)
    r = analyze_quality(QualitySnapshot.capture({'G': ('A', 1, 480, 540)}, [g], TimeModel.default(),
                                               {'A': Classroom('A', 30, 'REGULAR')}))
    assert all(v['unknown'] == 1 and v['ratio'] is None for v in r['preferences'].values())
    assert r['manual_exceptions']['unconfirmed_ids'] == ['G']
    assert r['manual_exceptions']['active_ids'] == []


def test_pending_preferences_and_inactive_overrides(example):
    _, groups, tm, rooms, _ = example
    r = analyze_quality(QualitySnapshot.capture({}, groups, tm, rooms))
    assert r['preferences']['day']['pending'] == 3 and r['preferences']['day']['ratio'] is None
    assert r['manual_exceptions']['inactive_ids'] == ['LAB-G1']
    assert r['manual_exceptions']['active_ids'] == []
    assert r['coverage']['original_groups']['unassigned'] == 4


def test_missing_metadata_explicit():
    g = Group('G-P1', 60, 'LAB', parent_group_id='G', total_subgroups=2)
    r = analyze_quality(QualitySnapshot.capture({'G-P1': ('X', 1, 480, 540),
                 'unknown': ('X', 9, 600, 600)}, [g], TimeModel.default(), {}))
    assert r['coverage']['original_groups']['unknown'] == 1
    assert r['coverage']['unknown_assignment_ids'] == ['unknown']
    assert r['occupancy']['unknown_assignment_rooms'] == ['X']
    assert r['manual_exceptions']['unknown_ids'] == ['G-P1']
    assert 'unmeasurable_assignment_intervals' in r['data_issues']


def test_invalid_exclusions_and_duplicate_sessions_rejected():
    tm = TimeModel.default(); rooms = {'A': Classroom('A', 30, 'REGULAR')}; g = Group('g', 60, 'REGULAR')
    with pytest.raises(ValueError, match='Duplicate'):
        QualitySnapshot.capture({}, [g, g], tm, rooms)
    for exclusions in [{('A', 1): [(600, 500)]}, {('X', 1): [(500, 600)]}, {('A', 9): [(500, 600)]}]:
        with pytest.raises(ValueError):
            QualitySnapshot.capture({}, [g], tm, rooms, room_exclusions=exclusions)


def test_deterministic_scheduler_quality_fixture():
    rooms = {'A': Classroom('A', 30, 'REGULAR'), 'B': Classroom('B', 30, 'LAB')}
    courses = [Course('A', 1, 60, 'REGULAR', preferred_day='Lunes', preferred_start_min=480, suggested_classroom='A'),
               Course('B', 1, 60, 'LAB', preferred_day='Martes', preferred_start_min=540, suggested_classroom='B')]
    reports = []
    for _ in range(2):
        _, state, groups = run_once(rooms, courses, seed=42)
        reports.append(analyze_quality(QualitySnapshot.capture(state.assignments, groups, state.time_model, state.classrooms)))
    assert reports[0] == reports[1]
    assert reports[0]['coverage']['assigned_ratio'] == 1
    assert all(row['ratio'] == 1 for row in reports[0]['preferences'].values())
    assert reports[0]['occupancy']['occupied_minutes'] == 120


def test_restored_result_identical_quality(example, tmp_path):
    from src.infrastructure.session_repository import SessionRepository
    assignments, groups, tm, rooms, courses = example
    repo = SessionRepository(str(tmp_path / 'session.db'))
    repo.save_session(None, 42, rooms, courses, {}, assignments, lab_overrides={'LAB-G1'})
    loaded = repo.load_session()
    restored = [g for c in loaded['courses'] for g in c.generate_groups()]
    for g in restored:
        g.lab_override = g.group_id in loaded['lab_overrides']
    actual = analyze_quality(QualitySnapshot.capture(loaded['assignments'], restored, tm, loaded['classrooms']))
    assert actual == measure(example)


def test_benchmark_json_exposes_quality_without_replacing_validity():
    from benchmark import benchmark_excel
    report = benchmark_excel(repeats=2, seed=42)
    assert report['deterministic'] is True
    assert report['hard_constraints_verified'] is True
    assert report['quality']['validity'] == 'not_evaluated'
    assert report['quality']['coverage']['assigned_sessions'] == report['assigned']
    assert report['quality']['coverage']['pending_sessions'] == report['unassigned']
    json.dumps(report, allow_nan=False)


def test_complete_split_family_counts_one_original_group(example):
    example[0]['D-G1-P2'] = ['A', 2, 540, 660]
    report = measure(example)
    assert report['coverage']['sessions'] == 5
    assert report['coverage']['original_groups'] == dict(total=4, fully_assigned=4,
        partially_assigned=0, unassigned=0, unknown=0)
    assert report['preferences']['day']['satisfied'] == 2
    assert report['preferences']['day']['evaluated'] == 3
    assert report['preferences']['time']['satisfied'] == 3
    assert report['preferences']['time']['pending'] == 0


def test_positive_time_tolerance_is_not_invented(example):
    example[0]['C-G1'][2:4] = [485, 545]
    report = measure(example)
    assert report['preferences']['time']['satisfied'] == 1
    assert report['preferences']['time']['unsatisfied'] == 1
