import json
import sqlite3
from dataclasses import replace
import pytest
from src.infrastructure.session_repository import SessionRepository
from src.infrastructure.project_repository import ProjectRepository
from src.application.scenario_comparison import scenario_metadata, compare_scenarios, session_fingerprint
from src.scheduling.teaching_resources import SchedulingResources
from tests.test_scheduling.test_teaching_resources import data


def payload(kind='teacher', enabled=True):
    courses, groups, rooms, resources=data(kind,enabled=enabled)
    return dict(excel_path=None,seed=42,classrooms=rooms,courses=courses,restrictions={},
                assignments={groups[0].group_id:('R1',1,480,540)},resources=resources)


@pytest.mark.parametrize('kind',['teacher','student_group','student'])
def test_partial_save_restore_scenario_and_disabled_roundtrip(tmp_path,kind):
    repo=SessionRepository(str(tmp_path/'session.db'))
    values=payload(kind)
    repo.save_session(**values)
    restored=repo.load_session()
    assert restored['resources']==values['resources']
    assert len(restored['assignments'])==1
    catalog=ProjectRepository(tmp_path/'projects.db')
    _project,scenario=catalog.create_project('Synthetic','Partial',repo,scenario_metadata('test'))
    snapshot,meta=catalog.read(scenario)
    assert snapshot['resources']==values['resources']
    assert compare_scenarios((restored,meta),(snapshot,meta))['comparable']
    values['resources']=SchedulingResources(tuple(replace(c,enabled=False) for c in values['resources'].catalogs))
    repo.save_session(**values)
    disabled=repo.load_session()
    assert not disabled['resources'].catalog(kind).enabled
    assert disabled['resources'].catalog(kind).memberships==restored['resources'].catalog(kind).memberships
    assert session_fingerprint(disabled)!=session_fingerprint(restored)
    assert 'resources' in compare_scenarios((disabled,meta),(snapshot,meta))['differences']
    assert catalog.read(scenario)[0]['resources']==snapshot['resources']


def test_migration_from_schema2_backup_is_readable_and_preserves_pins(tmp_path):
    path=tmp_path/'session.db';repo=SessionRepository(str(path))
    values=payload(); values.pop('resources')
    repo.save_session(**values,pinned_group_ids=set(values['assignments']))
    with sqlite3.connect(path) as con:
        con.execute('DROP TABLE scheduling_resources');con.execute('PRAGMA user_version=2')
    migrated=SessionRepository(str(path))
    assert migrated.schema_backup is not None
    with sqlite3.connect(migrated.schema_backup) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0]==2
        assert con.execute('SELECT COUNT(*) FROM assignments WHERE pinned=1').fetchone()[0]==1
    loaded=migrated.load_session()
    assert loaded['resources']==SchedulingResources()
    assert loaded['pinned_group_ids']==set(values['assignments'])
    with sqlite3.connect(path) as con: assert con.execute('PRAGMA user_version').fetchone()[0]==SessionRepository.SCHEMA_VERSION


def test_invalid_resource_save_preserves_last_transaction(tmp_path):
    repo=SessionRepository(str(tmp_path/'session.db'));values=payload()
    repo.save_session(**values)
    before=session_fingerprint(repo.load_session())
    groups=[g for c in values['courses'] for g in c.generate_groups()]
    values['assignments'][groups[1].group_id]=('R2',1,480,540)
    with pytest.raises(ValueError,match='TEACHER_OVERLAP'):repo.save_session(**values)
    assert session_fingerprint(repo.load_session())==before
    values['resources']=SchedulingResources(tuple(replace(c,enabled=False) for c in values['resources'].catalogs))
    repo.save_session(**values)
    assert len(repo.load_session()['assignments'])==2


@pytest.mark.parametrize('mutate',[
    lambda doc: doc.update(version=99),
    lambda doc: doc['catalogs'][0]['resources'].append(doc['catalogs'][0]['resources'][0]),
    lambda doc: doc['catalogs'][0]['memberships'][0].update(resource_ids=['missing']),
    lambda doc: doc['catalogs'][0].update(enabled='false'),
])
def test_corrupt_import_fails_closed_without_rewriting(tmp_path,mutate):
    path=tmp_path/'session.db';repo=SessionRepository(str(path));repo.save_session(**payload())
    with sqlite3.connect(path) as con:
        doc=json.loads(con.execute('SELECT payload FROM scheduling_resources').fetchone()[0]);mutate(doc)
        con.execute('UPDATE scheduling_resources SET payload=?',(json.dumps(doc),))
    before=path.read_bytes()
    with pytest.raises(ValueError):repo.load_session()
    assert path.read_bytes()==before


def test_resources_only_session_retained_and_clear_is_atomic(tmp_path):
    repo=SessionRepository(str(tmp_path/'session.db'));values=payload()
    values['assignments']=None
    repo.save_session(**values)
    assert repo.has_session()
    assert repo.load_session()['assignments'] is None
    repo.clear_session()
    assert not repo.has_session()


def test_legacy_save_omission_preserves_resource_extension(tmp_path):
    repo=SessionRepository(str(tmp_path/'session.db'));values=payload()
    repo.save_session(**values)
    original=values.pop('resources')
    repo.save_session(**values)
    assert repo.load_session()['resources']==original


def test_duplicate_json_fields_rejected(tmp_path):
    repo=SessionRepository(str(tmp_path/'session.db'));repo.save_session(**payload())
    with sqlite3.connect(repo._db_path) as con:
        con.execute('UPDATE scheduling_resources SET payload=?',('{"version":99,"version":1,"catalogs":[]}',))
    with pytest.raises(ValueError,match='Duplicate resource JSON field'):repo.load_session()


def test_failed_resource_transaction_keeps_prior_valid_snapshot(tmp_path):
    repo=SessionRepository(str(tmp_path/'session.db'));values=payload();repo.save_session(**values)
    before=session_fingerprint(repo.load_session())
    with sqlite3.connect(repo._db_path) as con:
        con.execute("CREATE TRIGGER block_resources BEFORE UPDATE ON scheduling_resources BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    values['resources']=SchedulingResources(tuple(replace(c,enabled=False) for c in values['resources'].catalogs))
    with pytest.raises(sqlite3.IntegrityError):repo.save_session(**values)
    assert session_fingerprint(repo.load_session())==before


@pytest.mark.parametrize('explicit_resources',[False,True])
def test_missing_resource_row_fails_load_save_and_reopen_without_mutation(tmp_path,explicit_resources):
    path=tmp_path/'session.db';repo=SessionRepository(str(path));values=payload();repo.save_session(**values)
    with sqlite3.connect(path) as con:con.execute('DELETE FROM scheduling_resources')
    before=path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError,match='resource contract'):
        repo.load_session()
    assert path.read_bytes()==before
    if not explicit_resources:values.pop('resources')
    with pytest.raises(sqlite3.DatabaseError,match='resource contract'):
        repo.save_session(**values)
    assert path.read_bytes()==before
    with pytest.raises(sqlite3.DatabaseError,match='resource contract'):
        repo.has_session()
    assert path.read_bytes()==before
    with pytest.raises(sqlite3.DatabaseError,match='resource contract'):
        SessionRepository(str(path))
    assert path.read_bytes()==before


def test_missing_resource_table_is_not_recreated_in_saved_schema3(tmp_path):
    path=tmp_path/'session.db';repo=SessionRepository(str(path));repo.save_session(**payload())
    with sqlite3.connect(path) as con:con.execute('DROP TABLE scheduling_resources')
    before=path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError):SessionRepository(str(path))
    assert path.read_bytes()==before


@pytest.mark.parametrize('legacy_version',[0,1,2])
def test_only_legacy_migration_initializes_explicit_empty_contract(tmp_path,legacy_version):
    path=tmp_path/'session.db';repo=SessionRepository(str(path));values=payload();values.pop('resources');repo.save_session(**values)
    with sqlite3.connect(path) as con:
        con.execute('DROP TABLE scheduling_resources');con.execute(f'PRAGMA user_version={legacy_version}')
    migrated=SessionRepository(str(path))
    assert migrated.schema_backup is not None
    with sqlite3.connect(migrated.schema_backup) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0]==legacy_version
        assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='scheduling_resources'").fetchone()
    with sqlite3.connect(path) as con:
        rows=con.execute('SELECT id,payload FROM scheduling_resources').fetchall()
        assert rows==[(1,json.dumps(SchedulingResources().to_data()))]
    assert migrated.load_session()['resources']==SchedulingResources()
