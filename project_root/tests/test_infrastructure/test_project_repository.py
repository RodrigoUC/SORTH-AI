import sqlite3
from pathlib import Path
import pytest
from src.infrastructure.project_repository import ProjectRepository
from src.infrastructure.session_repository import SessionRepository
from src.application.scenario_comparison import scenario_metadata, compare_scenarios
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def repo(tmp_path):
    repo = SessionRepository(str(tmp_path/'session.db'))
    repo.save_session(None, 42, {'A': Classroom('A', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'REGULAR', preferred_day='Lunes')], {},
                      {'BIO-G1': ('A', 1, 480, 540)})
    return repo


def test_save_reopen_duplicate_rename_isolation(repo, tmp_path):
    catalog = ProjectRepository(tmp_path/'projects.db')
    project, first = catalog.create_project('../Semester', 'Original', repo, scenario_metadata('v1'))
    duplicate = catalog.duplicate(first, 'Alternative')
    catalog.rename(duplicate, 'Renamed')
    repo.clear_session()
    assert catalog.read(first)[0]['seed'] == 42
    reopened = ProjectRepository(tmp_path/'projects.db')
    assert [r['name'] for r in reopened.list_scenarios()] == ['Original', 'Renamed']
    assert reopened.read(duplicate)[0]['assignments'] == {'BIO-G1': ('A', 1, 480, 540)}
    assert not (tmp_path.parent/'Semester').exists()


def test_duplicate_names_and_invalid_names_never_overwrite(repo, tmp_path):
    catalog = ProjectRepository(tmp_path/'projects.db')
    project, first = catalog.create_project('Project', 'Initial', repo, scenario_metadata())
    before = catalog.read(first)[0]['assignments']
    for name in ('INITIAL', ' initial '):
        with pytest.raises(sqlite3.IntegrityError):
            catalog.save_as(project, name, repo, scenario_metadata())
    with pytest.raises(sqlite3.IntegrityError):
        catalog.create_project('PROJECT', 'New', repo, scenario_metadata())
    for name in ('', '  ', 'a\x00b', 'x'*121):
        with pytest.raises(ValueError):
            catalog.duplicate(first, name)
    assert len(catalog.list_scenarios()) == 1
    assert catalog.read(first)[0]['assignments'] == before


def test_composite_failure_rolls_back_project(repo, tmp_path, monkeypatch):
    catalog = ProjectRepository(tmp_path/'projects.db')
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(catalog, '_insert', fail)
    with pytest.raises(OSError):
        catalog.create_project('Fail', 'Initial', repo, scenario_metadata())
    with sqlite3.connect(catalog.path) as con:
        assert con.execute('SELECT count(*) FROM projects').fetchone()[0] == 0
    assert repo.load_session()['seed'] == 42


def test_preserve_legacy_is_idempotent_and_source_unchanged(repo, tmp_path):
    before = Path(repo._db_path).read_bytes()
    catalog = ProjectRepository(tmp_path/'projects.db')
    first = catalog.preserve_legacy(repo, scenario_metadata())
    assert catalog.preserve_legacy(repo, scenario_metadata()) == first
    assert len(catalog.list_scenarios()) == 1
    assert Path(repo._db_path).read_bytes() == before


def test_future_catalog_and_snapshot_preserved(repo, tmp_path):
    catalog = ProjectRepository(tmp_path/'projects.db')
    _, first = catalog.create_project('P', 'S', repo, scenario_metadata())
    with sqlite3.connect(repo._db_path) as con:
        con.execute('PRAGMA user_version=999')
    before = Path(repo._db_path).read_bytes()
    with pytest.raises(sqlite3.DatabaseError):
        catalog.save_as(catalog.list_scenarios()[0]['project_id'], 'Future', repo, scenario_metadata())
    assert Path(repo._db_path).read_bytes() == before
    assert catalog.read(first)[0]['seed'] == 42
    with sqlite3.connect(catalog.path) as con:
        con.execute('PRAGMA user_version=999')
    before = catalog.path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError):
        ProjectRepository(catalog.path)
    assert catalog.path.read_bytes() == before


def test_comparison_shared_metrics_unknown_version_and_differences(repo, tmp_path):
    catalog = ProjectRepository(tmp_path/'projects.db')
    project, a = catalog.create_project('P', 'A', repo, scenario_metadata('v1'))
    b = catalog.duplicate(a, 'B')
    result = compare_scenarios(catalog.read(a), catalog.read(b))
    assert result['comparable']
    assert result['left'] == result['right']
    assert result['left']['coverage']['assigned_sessions'] == 1
    assert result['left']['occupancy']['occupied_minutes'] == 60
    changed = catalog.read(b)
    changed[0]['seed'] = 99
    changed[0]['restrictions'] = {'A': {'BIO'}}
    changed[1]['algorithm_version'] = None
    result = compare_scenarios(catalog.read(a), changed)
    assert not result['comparable'] and result['unknown_algorithm']
    assert set(result['differences']) == {'seed', 'restrictions', 'algorithm_version'}
    changed[1]['calendar']['end'] = 1000
    result = compare_scenarios(catalog.read(a), changed)
    assert result['left'] is None and not result['supported_calendar']


@pytest.mark.parametrize('placement', [
    ('B', 1, 480, 540), ('A', 2, 480, 540), ('A', 1, 540, 600),
])
def test_comparison_reports_changed_pinned_placement(repo, tmp_path, placement):
    values = repo.load_session()
    values['classrooms']['B'] = Classroom('B', 30, 'REGULAR')
    values['pinned_group_ids'] = {'BIO-G1'}
    repo.save_session(**values)
    catalog = ProjectRepository(tmp_path / 'pinned-projects.db')
    project, first = catalog.create_project('Synthetic', 'First pin', repo,
                                            scenario_metadata('sorth-scheduler-v2'))
    values['assignments']['BIO-G1'] = placement
    repo.save_session(**values)
    second = catalog.save_as(project, 'Changed pin', repo,
                             scenario_metadata('sorth-scheduler-v2'))
    result = compare_scenarios(catalog.read(first), catalog.read(second))
    assert not result['comparable']
    assert result['differences'] == ['pins']
    left, right = result['difference_values']['pins']
    assert left == {'BIO-G1': {'assignment': ('A', 1, 480, 540), 'lab_override': False}}
    assert right == {'BIO-G1': {'assignment': placement, 'lab_override': False}}


def test_comparison_does_not_treat_unpinned_results_as_fixed_inputs(repo):
    from copy import deepcopy

    original = repo.load_session()
    changed = deepcopy(original)
    changed['assignments']['BIO-G1'] = ('A', 2, 540, 600)
    metadata = scenario_metadata('sorth-scheduler-v2')
    result = compare_scenarios((original, metadata), (changed, metadata))
    assert result['comparable']
    assert result['differences'] == []
    assert result['left']['day_load'] != result['right']['day_load']


def test_comparison_preserves_confirmed_lab_exception_in_pin_details(repo):
    from copy import deepcopy

    original = repo.load_session()
    original['courses'][0].required_room_type = 'LAB'
    original['pinned_group_ids'] = {'BIO-G1'}
    original['lab_overrides'] = {'BIO-G1'}
    changed = deepcopy(original)
    changed['assignments']['BIO-G1'] = ('A', 2, 480, 540)
    metadata = scenario_metadata('sorth-scheduler-v2')
    identical = compare_scenarios((original, metadata), (deepcopy(original), metadata))
    assert identical['comparable']
    result = compare_scenarios((original, metadata), (changed, metadata))
    assert not result['comparable'] and result['differences'] == ['pins']
    assert all(side['BIO-G1']['lab_override']
               for side in result['difference_values']['pins'])


def test_snapshot_carries_extra_schema_fields_without_schema_ownership(repo, tmp_path):
    # An unknown future extension is preserved alongside the real pin column.
    with sqlite3.connect(repo._db_path) as con:
        con.execute('ALTER TABLE assignments ADD COLUMN future_marker INTEGER NOT NULL DEFAULT 0')
        con.execute('UPDATE assignments SET future_marker=1')
    catalog = ProjectRepository(tmp_path/'projects.db')
    _, scenario = catalog.create_project('P', 'Pinned', repo, scenario_metadata())
    with sqlite3.connect(catalog.path) as con:
        blob = con.execute('SELECT snapshot FROM scenarios WHERE id=?', (scenario,)).fetchone()[0]
    snapshot = tmp_path/'snapshot.db'
    snapshot.write_bytes(blob)
    with sqlite3.connect(snapshot) as con:
        assert con.execute('SELECT future_marker FROM assignments').fetchone()[0] == 1


def test_failed_rename_preserves_both_snapshots(repo, tmp_path):
    catalog = ProjectRepository(tmp_path/'projects.db')
    _, a = catalog.create_project('P', 'A', repo, scenario_metadata())
    b = catalog.duplicate(a, 'B')
    with pytest.raises(sqlite3.IntegrityError):
        catalog.rename(b, 'a')
    assert [r['name'] for r in catalog.list_scenarios()] == ['A', 'B']
