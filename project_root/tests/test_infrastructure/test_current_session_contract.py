"""Current sessions retain result presence and reject unsupported formats intact."""
import sqlite3

import pytest

from src.application.scenario_comparison import session_fingerprint
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.mark.parametrize('assignments', [None, {}, {'BIO-G1': ('R', 1, 480, 540)}])
def test_result_presence_roundtrip_and_independent_snapshot(tmp_path, assignments):
    repo = SessionRepository(str(tmp_path / 'session.db'))
    repo.save_session(None, 42, {'R': Classroom('R', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'REGULAR')], {}, assignments)
    assert SessionRepository(repo._db_path).load_session()['assignments'] == assignments
    assert SessionRepository(str(repo.backup_session())).load_session()['assignments'] == assignments


@pytest.mark.parametrize('version', [0, 1, 2, 3, 4, 6, 999])
def test_unsupported_schema_is_rejected_without_mutation_or_migration(tmp_path, version):
    path = tmp_path / 'session.db'
    SessionRepository(str(path)).save_session(None, 42, {}, [], {}, None)
    with sqlite3.connect(path) as con:
        con.execute(f'PRAGMA user_version={version}')
    before = path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError, match='Unsupported session schema'):
        SessionRepository(str(path))
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_empty_result_changes_scenario_fingerprint(tmp_path):
    repo = SessionRepository(str(tmp_path / 'session.db'))
    repo.save_session(None, 42, {}, [Course('BIO', 1, 60, 'REGULAR')], {}, None)
    before = repo.load_session()
    repo.save_session(None, 42, {}, before['courses'], {}, {})
    assert session_fingerprint(before) != session_fingerprint(repo.load_session())


@pytest.mark.parametrize('value', [2, -1, 'false', b'1'])
def test_invalid_result_presence_is_not_coerced(tmp_path, value):
    path = tmp_path / 'session.db'
    repo = SessionRepository(str(path))
    repo.save_session(None, 42, {}, [], {}, None)
    with sqlite3.connect(path) as con:
        con.execute('PRAGMA ignore_check_constraints=ON')
        con.execute('UPDATE session SET schedule_present=?', (value,))
    before = path.read_bytes()
    with pytest.raises((ValueError, sqlite3.DatabaseError), match='schedule_present|integrity'):
        SessionRepository(str(path))
    assert path.read_bytes() == before


def test_assignments_without_result_are_rejected(tmp_path):
    path = tmp_path / 'session.db'
    repo = SessionRepository(str(path))
    repo.save_session(None, 42, {'R': Classroom('R', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'REGULAR')], {}, {'BIO-G1': ('R', 1, 480, 540)})
    with sqlite3.connect(path) as con:
        con.execute('UPDATE session SET schedule_present=0')
    with pytest.raises(ValueError, match='without a generated schedule'):
        repo.load_session()
