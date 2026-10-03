"""Failed semantic validation must roll back migration, not just later loading."""
import json
import sqlite3

import pytest

from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources


@pytest.mark.parametrize('kind', ['unknown_session', 'invalid_assignment'])
def test_schema3_invalid_saved_constraints_roll_back_migration(tmp_path, kind):
    path = tmp_path / 'session.db'
    repo = SessionRepository(str(path))
    resources = SchedulingResources((ResourceCatalog('teacher', True,
        (Resource('T', 'Synthetic teacher'),), (('BIO-G1', ('T',)),)),))
    repo.save_session(None, 42, {'R': Classroom('R', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'REGULAR')], {},
                      {'BIO-G1': ('R', 1, 480, 540)}, resources=resources)
    with sqlite3.connect(path) as con:
        con.execute('DROP TABLE project_calendar')
        con.execute('PRAGMA user_version=3')
        if kind == 'unknown_session':
            payload = json.loads(con.execute('SELECT payload FROM scheduling_resources').fetchone()[0])
            payload['catalogs'][0]['memberships'][0]['group_id'] = 'UNKNOWN-G1'
            con.execute('UPDATE scheduling_resources SET payload=?', (json.dumps(payload),))
        else:
            con.execute('UPDATE assignments SET end_min=555')
    before = path.read_bytes()

    with pytest.raises(ValueError):
        SessionRepository(str(path))

    assert path.read_bytes() == before
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 3
        assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='project_calendar'").fetchone()
    backups = list(tmp_path.glob('schema-session-*.db'))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 3


def test_valid_schema3_resources_pins_and_lab_exception_survive_migration(tmp_path):
    path = tmp_path / 'session.db'
    repo = SessionRepository(str(path))
    resources = SchedulingResources((ResourceCatalog('teacher', True,
        (Resource('T', 'Synthetic teacher'),), (('BIO-G1', ('T',)),)),))
    repo.save_session(None, 42, {'R': Classroom('R', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'LAB')], {},
                      {'BIO-G1': ('R', 1, 480, 540)},
                      lab_overrides={'BIO-G1'}, pinned_group_ids={'BIO-G1'}, resources=resources)
    with sqlite3.connect(path) as con:
        con.execute('DROP TABLE project_calendar')
        con.execute('PRAGMA user_version=3')

    migrated = SessionRepository(str(path))
    loaded = migrated.load_session()

    assert loaded['resources'] == resources
    assert loaded['pinned_group_ids'] == loaded['lab_overrides'] == {'BIO-G1'}
    assert loaded['assignments'] == {'BIO-G1': ('R', 1, 480, 540)}
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == SessionRepository.SCHEMA_VERSION
    with sqlite3.connect(migrated.schema_backup) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 3
