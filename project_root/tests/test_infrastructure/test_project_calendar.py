import json
import sqlite3
import pytest
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.project_calendar import ProjectCalendar
from src.application.scenario_comparison import scenario_metadata, validate_scenario_metadata, compare_scenarios


def test_calendar_roundtrip_and_schema(tmp_path):
    path=tmp_path/'session.db'; repo=SessionRepository(str(path))
    calendar=ProjectCalendar(('Martes','Jueves'),480,1000,((600,620),(800,840)))
    repo.save_session(None,42,{},[],{},None,calendar=calendar)
    assert SessionRepository(str(path)).load_session()['calendar'] == calendar
    with sqlite3.connect(path) as db: assert db.execute('pragma user_version').fetchone()[0] == 4


def test_schema3_migration_defaults_backup_and_unknown_calendar(tmp_path):
    path=tmp_path/'session.db'; repo=SessionRepository(str(path))
    repo.save_session(None,42,{},[],{},None)
    with sqlite3.connect(path) as db:
        db.execute('drop table project_calendar'); db.execute('pragma user_version=3')
    repo=SessionRepository(str(path))
    assert repo.schema_backup.exists()
    assert repo.load_session()['calendar'] == ProjectCalendar()
    with sqlite3.connect(path) as db:
        db.execute('update project_calendar set payload=? where id=1',(json.dumps({'version':999}),))
    with pytest.raises(ValueError): repo.load_session()


def test_scenario_validates_own_calendar(tmp_path):
    repo=SessionRepository(str(tmp_path/'session.db'))
    calendar=ProjectCalendar(('Martes',),480,600,())
    repo.save_session(None,42,{},[],{},None,calendar=calendar)
    data=repo.load_session(); metadata=scenario_metadata('version',calendar)
    validate_scenario_metadata(metadata,calendar)
    assert compare_scenarios((data,metadata),(data,metadata))['supported_calendar']
    with pytest.raises(ValueError): validate_scenario_metadata(metadata,ProjectCalendar())


def test_omitted_calendar_preserves_rules_and_explicit_default_resets(tmp_path):
    repo=SessionRepository(str(tmp_path/'calendar.db'))
    calendar=ProjectCalendar(('Martes',),480,600,())
    repo.save_session(None,42,{},[],{},None,calendar=calendar)
    repo.save_session(None,43,{},[],{},None)
    assert repo.load_session()['calendar']==calendar
    repo.save_session(None,44,{},[],{},None,calendar=ProjectCalendar())
    assert repo.load_session()['calendar']==ProjectCalendar()


def test_duplicate_calendar_json_rejected_without_mutation(tmp_path):
    path=tmp_path/'calendar.db';repo=SessionRepository(str(path))
    repo.save_session(None,42,{},[],{},None)
    payload=json.dumps(ProjectCalendar().to_dict()).replace('"version": 1','"version": 99, "version": 1')
    with sqlite3.connect(path) as db: db.execute('update project_calendar set payload=?',(payload,))
    with pytest.raises(ValueError,match='Duplicate'): repo.load_session()
    with pytest.raises(ValueError,match='Duplicate'): repo.save_session(None,43,{},[],{},None)
    with sqlite3.connect(path) as db: assert db.execute('select seed from session').fetchone()[0]==42


def test_calendar_changes_session_fingerprint(tmp_path):
    from src.application.scenario_comparison import session_fingerprint
    repo=SessionRepository(str(tmp_path/'fingerprint.db'))
    repo.save_session(None,42,{},[],{},None)
    data=repo.load_session(); original=session_fingerprint(data)
    data['calendar']=ProjectCalendar(('Martes',),480,600,())
    assert session_fingerprint(data)!=original


def test_missing_saved_calendar_never_silently_reverts_to_defaults(tmp_path):
    path=tmp_path/'calendar.db';repo=SessionRepository(str(path))
    repo.save_session(None,42,{},[],{},None,calendar=ProjectCalendar(('Martes',),480,600,()))
    with sqlite3.connect(path) as db:db.execute('delete from project_calendar')
    reopened=SessionRepository(str(path))
    with pytest.raises(ValueError,match='missing'): reopened.load_session()
    with pytest.raises(ValueError,match='missing'): reopened.save_session(None,43,{},[],{},None)
