import sqlite3
import pytest
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course
from src.scheduling.classroom import Classroom


def save(repo, pins=()):
    repo.save_session(None, 42, {'R': Classroom('R', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'LAB')], {},
                      {'BIO-G1': ('R', 1, 480, 540)}, {'BIO-G1'}, pins)




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
