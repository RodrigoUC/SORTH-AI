import sqlite3
from src.infrastructure.session_repository import SessionRepository
from src.infrastructure.project_repository import ProjectRepository
from src.application.scenario_comparison import scenario_metadata
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom

def test_pins_and_exceptions_survive_immutable_duplicate(tmp_path):
    repo=SessionRepository(str(tmp_path/'working.db'))
    data=dict(excel_path=None,seed=42,classrooms={'R':Classroom('R',30,'REGULAR')},courses=[Course('A',1,60,'LAB')],restrictions={},assignments={'A-G1':('R',1,480,540)},lab_overrides={'A-G1'},pinned_group_ids={'A-G1'})
    repo.save_session(**data)
    catalog=ProjectRepository(tmp_path/'projects.db')
    _,a=catalog.create_project('Project','One',repo,scenario_metadata())
    b=catalog.duplicate(a,'Two')
    data.update(seed=99,pinned_group_ids=set(),lab_overrides=set(),assignments={})
    repo.save_session(**data)
    for sid in [a,b]:
        saved,_=catalog.read(sid)
        assert saved['seed']==42
        assert saved['pinned_group_ids']==saved['lab_overrides']=={'A-G1'}
        assert saved['assignments']=={'A-G1':('R',1,480,540)}

def test_old_snapshot_read_migrates_expendable_copy_only(tmp_path):
    repo=SessionRepository(str(tmp_path/'legacy.db'))
    repo.save_session(None,42,{},[],{}, {})
    with sqlite3.connect(repo._db_path) as db:
        db.execute('ALTER TABLE assignments DROP COLUMN pinned')
        db.execute('PRAGMA user_version=1')
    legacy=(tmp_path/'legacy.db').read_bytes()
    catalog=ProjectRepository(tmp_path/'projects.db')
    _,sid=catalog.create_project('Project','Old',repo,scenario_metadata())
    assert (tmp_path/'legacy.db').read_bytes()==legacy
    before=(tmp_path/'projects.db').read_bytes()
    saved,_=catalog.read(sid)
    assert saved['pinned_group_ids']==set()
    assert (tmp_path/'projects.db').read_bytes()==before


def test_future_snapshot_read_preserves_catalog_and_source(tmp_path):
    repo=SessionRepository(str(tmp_path/'future.db'))
    repo.save_session(None,42,{},[],{}, {})
    catalog=ProjectRepository(tmp_path/'projects.db')
    _,sid=catalog.create_project('Project','One',repo,scenario_metadata())
    with sqlite3.connect(repo._db_path) as db: db.execute('PRAGMA user_version=999')
    blob=(tmp_path/'future.db').read_bytes()
    with sqlite3.connect(catalog.path) as db: db.execute('UPDATE scenarios SET snapshot=? WHERE id=?',(blob,sid))
    before=catalog.path.read_bytes()
    import pytest
    with pytest.raises(sqlite3.DatabaseError): catalog.read(sid)
    assert catalog.path.read_bytes()==before
    assert (tmp_path/'future.db').read_bytes()==blob
