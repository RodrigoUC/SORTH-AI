import sqlite3
import pytest
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom


def save(repo, pins=()):
    repo.save_session(None, 42, {'R': Classroom('R', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'LAB')], {},
                      {'BIO-G1': ('R', 1, 480, 540)}, {'BIO-G1'}, pins)


def test_schema_v1_migration_retains_assignment_and_lab_exception(tmp_path):
    path = tmp_path / 'session.db'
    repo = SessionRepository(str(path))
    save(repo)
    with sqlite3.connect(path) as con:
        con.execute('ALTER TABLE assignments DROP COLUMN pinned')
        con.execute('PRAGMA user_version = 1')
    upgraded = SessionRepository(str(path))
    assert upgraded.schema_backup.exists()
    data = upgraded.load_session()
    assert data['assignments'] == {'BIO-G1': ('R', 1, 480, 540)}
    assert data['lab_overrides'] == {'BIO-G1'}
    assert not data['pinned_group_ids']
    with sqlite3.connect(upgraded.schema_backup) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 1
    save(upgraded, {'BIO-G1'})
    assert SessionRepository(str(path)).load_session()['pinned_group_ids'] == {'BIO-G1'}


def test_bad_pin_or_late_save_failure_does_not_erase_previous_state(tmp_path):
    repo = SessionRepository(str(tmp_path / 'session.db'))
    save(repo, {'BIO-G1'})
    with pytest.raises(ValueError):
        save(repo, {'MISSING'})
    with sqlite3.connect(repo._db_path) as con:
        con.execute("CREATE TRIGGER fail_assignment BEFORE INSERT ON assignments BEGIN SELECT RAISE(ABORT, 'failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        save(repo)
    data = repo.load_session()
    assert data['pinned_group_ids'] == {'BIO-G1'}
    assert data['lab_overrides'] == {'BIO-G1'}
    assert data['assignments']['BIO-G1'] == ('R', 1, 480, 540)


def test_migration_failure_rolls_back_added_column_and_version(tmp_path, monkeypatch):
    from contextlib import contextmanager
    path = tmp_path / 'old.db'
    repo = SessionRepository(str(path))
    save(repo)
    with sqlite3.connect(path) as con:
        con.execute('ALTER TABLE assignments DROP COLUMN pinned')
        con.execute('PRAGMA user_version = 1')
    original = SessionRepository._connect
    class FailVersion:
        def __init__(self, con):
            self.con = con
        def execute(self, query, *args):
            if query.startswith('PRAGMA user_version ='):
                raise sqlite3.OperationalError('synthetic migration failure')
            return self.con.execute(query, *args)
        def executescript(self, script):
            return self.con.executescript(script)
    @contextmanager
    def fail_connect(self):
        with original(self) as con:
            yield FailVersion(con)
    monkeypatch.setattr(SessionRepository, '_connect', fail_connect)
    with pytest.raises(sqlite3.OperationalError):
        SessionRepository(str(path))
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 1
        assert 'pinned' not in {r[1] for r in con.execute('PRAGMA table_info(assignments)')}
        assert con.execute('SELECT group_id, lab_override FROM assignments').fetchall() == [('BIO-G1', 1)]
