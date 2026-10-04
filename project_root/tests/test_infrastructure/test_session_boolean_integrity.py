"""Damaged SQLite values must never invent consent or scheduling decisions."""
import sqlite3

import pytest

from src.application.recovery_command import recover_candidate
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources


INVALID_BOOLEANS = [2, -1, 0.5, 'false', 'true', '', b'\x00']


def saved(path, *, resources=False):
    repo = SessionRepository(str(path))
    catalog = SchedulingResources((ResourceCatalog('teacher', True,
        (Resource('T', 'Synthetic teacher'),), (('LAB-G1', ('T',)),)),)) if resources else SchedulingResources()
    repo.save_session(None, 42, {'L': Classroom('L', 40, 'LAB')},
        [Course('LAB', 1, 60, 'LAB', size=20, force_split=False),
         Course('LONG', 1, 300, 'REGULAR', force_split=False)], {},
        {'LAB-G1': ('L', 1, 480, 540)}, lab_overrides={'LAB-G1'},
        pinned_group_ids={'LAB-G1'}, resources=catalog)
    return repo


def corrupt(path, field, value):
    table = 'courses' if field == 'force_split' else 'assignments'
    with sqlite3.connect(path) as con:
        # Pinned already has a CHECK on new databases; exercise the reader too,
        # as a caller can retain its repository while another writer changes it.
        con.execute('PRAGMA ignore_check_constraints=ON')
        where = " WHERE code='LONG'" if field == 'force_split' else ''
        con.execute(f'UPDATE {table} SET {field}=?{where}', (value,))


def downgrade(path, version):
    with sqlite3.connect(path) as con:
        con.execute('DROP TABLE project_calendar')
        if version < 3:
            con.execute('DROP TABLE scheduling_resources')
        if version < 2:
            con.execute('ALTER TABLE assignments DROP COLUMN pinned')
        con.execute(f'PRAGMA user_version={version}')


@pytest.mark.parametrize('field', ['force_split', 'lab_override'])
@pytest.mark.parametrize('value', INVALID_BOOLEANS)
def test_malformed_boolean_blocks_open_load_save_and_recovery_without_rewriting(tmp_path, field, value):
    path = tmp_path / 'session.db'
    repo = saved(path)
    corrupt(path, field, value)
    before = path.read_bytes()

    with pytest.raises(ValueError, match=field):
        SessionRepository(str(path))
    with pytest.raises(ValueError, match=field):
        repo.load_session()
    with pytest.raises(ValueError, match=field):
        repo.save_session(None, 43, {}, [], {}, None)
    candidate = tmp_path / 'candidate.db'
    with pytest.raises(ValueError, match=field):
        recover_candidate(path, candidate)

    assert path.read_bytes() == before
    assert not candidate.exists()
    assert not list(tmp_path.glob('.recovery-*'))
    assert not list(tmp_path.glob('*session-*.db'))


@pytest.mark.parametrize('value', INVALID_BOOLEANS)
def test_malformed_pinned_boolean_is_rejected_on_existing_repository(tmp_path, value):
    path = tmp_path / 'session.db'
    repo = saved(path)
    corrupt(path, 'pinned', value)
    before = path.read_bytes()
    with pytest.raises(ValueError, match='pinned'):
        repo.load_session()
    with pytest.raises(ValueError, match='pinned'):
        repo.save_session(None, 43, {}, [], {}, None)
    assert path.read_bytes() == before


@pytest.mark.parametrize('version', [1, 2, 3])
@pytest.mark.parametrize('field', ['force_split', 'lab_override'])
def test_bad_legacy_boolean_rolls_back_schema_and_preserves_original_backup(tmp_path, version, field):
    path = tmp_path / 'legacy.db'
    saved(path, resources=version >= 3)
    downgrade(path, version)
    corrupt(path, field, 'false')
    before = path.read_bytes()
    with pytest.raises(ValueError, match=field):
        SessionRepository(str(path))
    assert path.read_bytes() == before
    backups = list(tmp_path.glob('schema-session-*.db'))
    assert len(backups) == 1
    for source in [path, backups[0]]:
        with sqlite3.connect(source) as con:
            assert con.execute('PRAGMA user_version').fetchone()[0] == version
            assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='project_calendar'").fetchone()
            table = 'courses' if field == 'force_split' else 'assignments'
            where = " WHERE code='LONG'" if field == 'force_split' else ''
            assert con.execute(f'SELECT {field}, typeof({field}) FROM {table}{where}').fetchone() == ('false', 'text')


@pytest.mark.parametrize('value', [0, 1, '0', '1', 0.0, 1.0])
@pytest.mark.parametrize('version', [1, 2, 3, 4])
def test_valid_sqlite_boolean_storage_survives_versions_and_recovery(tmp_path, value, version):
    path = tmp_path / 'session.db'
    saved(path, resources=version >= 3)
    # SQLite INTEGER affinity normalizes numeric strings/integral floats to
    # integers; these have always been valid and do not need truthiness.
    corrupt(path, 'force_split', value)
    corrupt(path, 'lab_override', value)
    if version < 4:
        downgrade(path, version)
    original = path.read_bytes()
    candidate = tmp_path / 'candidate.db'
    recover_candidate(path, candidate)
    assert path.read_bytes() == original
    loaded = SessionRepository(str(candidate)).load_session()
    expected = bool(int(value))
    assert next(c for c in loaded['courses'] if c.code == 'LONG').force_split is expected
    assert next(c for c in loaded['courses'] if c.code == 'LAB').force_split is False
    assert loaded['lab_overrides'] == ({'LAB-G1'} if expected else set())
    assert loaded['pinned_group_ids'] == ({'LAB-G1'} if version >= 2 else set())
    assert loaded['assignments'] == {'LAB-G1': ('L', 1, 480, 540)}
    if version >= 3:
        assert loaded['resources'].catalog('teacher').ids_for('LAB-G1') == ('T',)
        assert loaded['resources'].catalog('teacher').enabled
    else:
        assert loaded['resources'] == SchedulingResources()


def test_nullable_force_split_remains_automatic(tmp_path):
    path = tmp_path / 'session.db'
    saved(path)
    corrupt(path, 'force_split', None)
    loaded = SessionRepository(str(path)).load_session()
    assert next(c for c in loaded['courses'] if c.code == 'LONG').force_split is None
    assert [g.duration_min for c in loaded['courses'] if c.code == 'LONG'
            for g in c.generate_groups()] == [120, 120, 60]


@pytest.mark.parametrize('field', ['lab_override', 'pinned'])
def test_nonnullable_saved_flags_reject_null_even_without_schema_constraint(field):
    # Normal schemas reject NULL on insert; the boundary still has an explicit
    # contract if a legacy or repaired schema lacks that SQL constraint.
    with pytest.raises(ValueError, match=field):
        SessionRepository._decode_boolean(None, field)
