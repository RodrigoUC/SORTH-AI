"""Destructive scenarios run only against disposable test databases."""
import sqlite3
import zipfile

import pytest

from src.infrastructure.excel_reader import ExcelReader, ExcelImportError
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


def populate(path):
    repo = SessionRepository(str(path))
    repo.save_session('original.xlsx', 42, {'R': Classroom('R', 30, 'REGULAR', 'Room', 'Campus')},
                      [Course('BIO', 2, 60, 'LAB', size=20, force_split=False,
                              group_suggestions=[{'aula': 'R', 'preferred_day': 'Lunes', 'preferred_start_min': 480}])],
                      {'R': {'BIO'}}, {'BIO-G1': ('R', 1, 480, 540)}, {'BIO-G1'})
    return repo


def records(path):
    with sqlite3.connect(path) as con:
        return {name: con.execute(f'SELECT * FROM {name}').fetchall()
                for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def test_real_sqlite_full_rolls_back_every_table(tmp_path):
    path = tmp_path / 'session.db'
    repo = populate(path)
    original = records(path)
    with sqlite3.connect(path) as con:
        page_count = con.execute('PRAGMA page_count').fetchone()[0]
    original_connect = sqlite3.connect
    def limited(*args, **kwargs):
        con = original_connect(*args, **kwargs)
        con.execute(f'PRAGMA max_page_count={page_count}')
        return con
    from unittest.mock import patch
    with patch('src.infrastructure.session_repository.sqlite3.connect', limited):
        with pytest.raises(sqlite3.OperationalError, match='full'):
            repo.save_session('new.xlsx', 9, {}, [Course('NEW', 1, 60, 'REGULAR', name='X' * 1000000)], {}, None)
    assert records(path) == original


def test_late_assignment_failure_rolls_back_all_replaced_tables(tmp_path):
    path = tmp_path / 'session.db'
    repo = populate(path)
    original = records(path)
    with sqlite3.connect(path) as con:
        con.execute("CREATE TRIGGER deny_assignment BEFORE INSERT ON assignments BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match='injected'):
        repo.save_session('new.xlsx', None, {}, [], {}, {'NEW': ('R', 1, 480, 540)})
    assert records(path) == original


def test_clear_failure_does_not_partially_delete_session(tmp_path):
    path = tmp_path / 'session.db'
    repo = populate(path)
    original = records(path)
    with sqlite3.connect(path) as con:
        con.execute("CREATE TRIGGER deny_clear BEFORE DELETE ON courses BEGIN SELECT RAISE(ABORT, 'cannot delete'); END")
    with pytest.raises(sqlite3.IntegrityError):
        repo.clear_session()
    assert records(path) == original


def test_backup_roundtrip_preserves_every_field_and_override(tmp_path):
    path = tmp_path / 'session.db'
    repo = populate(path)
    before = records(path)
    backup = repo.backup_session()
    restored = SessionRepository(str(backup)).load_session()
    copy = SessionRepository(str(tmp_path / 'restored.db'))
    copy.save_session(**restored)
    for key, rows in before.items():
        if key != 'session':
            assert records(tmp_path / 'restored.db')[key] == rows
    assert records(backup) == before
    assert restored['lab_overrides'] == {'BIO-G1'}


def test_newer_schema_is_rejected_without_change_or_backup(tmp_path):
    path = tmp_path / 'future.db'
    populate(path)
    with sqlite3.connect(path) as con:
        con.execute('PRAGMA user_version=999')
    original = path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError, match='newer'):
        SessionRepository(str(path))
    assert path.read_bytes() == original
    assert not list(tmp_path.glob('schema-session-*'))


def test_legacy_migration_keeps_premigration_backup_and_is_idempotent(tmp_path):
    path = tmp_path / 'legacy.db'
    populate(path)
    with sqlite3.connect(path) as con:
        con.execute('PRAGMA user_version=0')
        con.execute('ALTER TABLE courses DROP COLUMN size')
        con.execute('ALTER TABLE assignments DROP COLUMN lab_override')
    original = records(path)
    repo = SessionRepository(str(path))
    assert records(repo.schema_backup) == original
    with sqlite3.connect(repo.schema_backup) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 0
    assert repo.load_session()['lab_overrides'] == set()
    assert SessionRepository(str(path)).schema_backup is None
    assert len(list(tmp_path.glob('schema-session-*'))) == 1


def test_schema_migration_failure_is_atomic(tmp_path):
    path = tmp_path / 'legacy.db'
    populate(path)
    with sqlite3.connect(path) as con:
        con.execute('PRAGMA user_version=0')
        con.execute('ALTER TABLE courses DROP COLUMN size')
        con.execute('DROP TABLE assignments')
        con.execute('CREATE VIEW assignments AS SELECT 1 AS group_id')
    original = records(path)
    with pytest.raises(sqlite3.OperationalError):
        SessionRepository(str(path))
    assert records(path) == original
    with sqlite3.connect(path) as con:
        assert con.execute('PRAGMA user_version').fetchone()[0] == 0
        assert 'size' not in {r[1] for r in con.execute('PRAGMA table_info(courses)')}


@pytest.mark.parametrize('limit', ['MAX_FILE_BYTES', 'MAX_EXPANDED_BYTES', 'MAX_ARCHIVE_MEMBERS'])
def test_oversized_archives_rejected_before_excel_parser(tmp_path, monkeypatch, limit):
    path = tmp_path / 'large.xlsx'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('payload', '0' * 100000)
    monkeypatch.setattr(ExcelReader, limit, 0)
    monkeypatch.setattr('pandas.ExcelFile', lambda *a, **k: pytest.fail('parser must not run'))
    with pytest.raises(ExcelImportError, match='límite'):
        ExcelReader(str(path)).load_validated()


def test_too_many_rows_are_rejected_not_truncated(tmp_path, monkeypatch):
    from openpyxl import Workbook
    path = tmp_path / 'rows.xlsx'
    book = Workbook()
    room = book.active
    room.title = 'Aulas'
    room.append(['# DE AULA', 'CAPACIDAD'])
    room.append(['R', 30])
    course = book.create_sheet('Cursos')
    course.append(['Curso'])
    course.append(['ONE'])
    course.append(['TWO'])
    book.save(path)
    monkeypatch.setattr(ExcelReader, 'MAX_DATA_ROWS', 1)
    with pytest.raises(ExcelImportError, match='límite'):
        ExcelReader(str(path)).load_validated()


def test_recovery_candidate_keeps_original_and_never_overwrites(tmp_path):
    from tools.recover_session import recover_candidate
    source = tmp_path / 'original.db'
    populate(source)
    before = source.read_bytes()
    output = tmp_path / 'candidate.db'
    assert recover_candidate(source, output) == output
    assert records(output) == records(source)
    assert source.read_bytes() == before
    candidate_before = output.read_bytes()
    with pytest.raises(FileExistsError):
        recover_candidate(source, output)
    assert output.read_bytes() == candidate_before
    with pytest.raises(FileExistsError):
        recover_candidate(source, source)


def test_recovery_rejects_corrupt_source_without_publishing(tmp_path):
    from tools.recover_session import recover_candidate
    source = tmp_path / 'broken.db'
    source.write_bytes(b'broken database')
    output = tmp_path / 'candidate.db'
    with pytest.raises(sqlite3.DatabaseError):
        recover_candidate(source, output)
    assert source.read_bytes() == b'broken database'
    assert not output.exists()
    assert not list(tmp_path.glob('.recovery-*'))


def test_interrupted_writer_recovers_previous_committed_session(tmp_path):
    """Kill an isolated process mid-transaction, then let SQLite recover it."""
    import subprocess
    import sys
    path = tmp_path / 'session.db'
    populate(path)
    before = records(path)
    script = '''import sqlite3, sys, time
con = sqlite3.connect(sys.argv[1])
con.execute("BEGIN IMMEDIATE")
con.execute("UPDATE session SET excel_path='uncommitted.xlsx'")
con.execute("DELETE FROM assignments")
con.execute("DELETE FROM courses")
print("uncommitted", flush=True)
time.sleep(60)
'''
    child = subprocess.Popen([sys.executable, '-c', script, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'uncommitted'
        child.kill()
        child.communicate(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)
    assert records(path) == before
    assert SessionRepository(str(path)).load_session()['lab_overrides'] == {'BIO-G1'}


def test_orphaned_rows_are_not_treated_as_empty_session(tmp_path):
    path = tmp_path / 'orphaned.db'
    repo = populate(path)
    with sqlite3.connect(path) as con:
        con.execute('DELETE FROM session')
    before = path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError, match='without session metadata'):
        repo.has_session()
    assert path.read_bytes() == before
