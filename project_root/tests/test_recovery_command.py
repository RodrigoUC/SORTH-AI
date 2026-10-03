import json
from pathlib import Path
import pytest
from src.application.recovery_command import run
from src.infrastructure.session_repository import SessionRepository


def arguments(tmp_path, source):
    return ['--recover-session', '--source', str(source), '--output', str(tmp_path / 'candidate.db'),
            '--report', str(tmp_path / 'report.json')]


def test_missing_source_reports_error_without_default_session(tmp_path, monkeypatch):
    monkeypatch.setattr(SessionRepository, 'default_path', lambda: pytest.fail('default session accessed'))
    assert run(arguments(tmp_path, tmp_path / 'missing.db')) == 1
    assert not (tmp_path / 'candidate.db').exists()
    assert not json.loads((tmp_path / 'report.json').read_text())['ok']


def test_report_must_not_overwrite_source(tmp_path):
    source = tmp_path / 'report.json'
    source.write_bytes(b'original')
    with pytest.raises(FileExistsError):
        run(arguments(tmp_path, source))
    assert source.read_bytes() == b'original'


def test_output_must_not_overwrite_file(tmp_path):
    candidate = tmp_path / 'candidate.db'
    candidate.write_bytes(b'original')
    assert run(arguments(tmp_path, tmp_path / 'missing.db')) == 1
    assert candidate.read_bytes() == b'original'


def test_successful_recovery_is_independent_and_not_activated(tmp_path):
    source = tmp_path / 'original.db'
    repo = SessionRepository(str(source))
    repo.save_session('Café.xlsx', 17, {}, [], {}, {})
    original = source.read_bytes()
    assert run(arguments(tmp_path, source)) == 0
    result = json.loads((tmp_path / 'report.json').read_text())
    assert result['ok'] and result['activated'] is False
    assert source.read_bytes() == original
    recovered = SessionRepository(str(tmp_path / 'candidate.db')).load_session()
    assert recovered['seed'] == 17 and recovered['excel_path'] == 'Café.xlsx'


def test_future_schema_is_preserved_and_not_published(tmp_path):
    import sqlite3
    source = tmp_path / 'future.db'
    with sqlite3.connect(source) as db:
        db.execute('PRAGMA user_version=999')
    original = source.read_bytes()
    assert run(arguments(tmp_path, source)) == 1
    assert source.read_bytes() == original
    assert not (tmp_path / 'candidate.db').exists()


def test_real_schema1_fixture_recovers_with_schedule_and_lab_exception(tmp_path):
    import sqlite3
    from src.scheduling.validation import validate_schedule
    from src.scheduling.time_model import TimeModel
    source = tmp_path / 'schema1.db'
    sql = Path(__file__).parent / 'fixtures/session-schema1.sql'
    with sqlite3.connect(source) as db:
        db.executescript(sql.read_text(encoding='utf-8'))
    original = source.read_bytes()
    assert run(arguments(tmp_path, source)) == 0
    assert source.read_bytes() == original
    data = SessionRepository(str(tmp_path / 'candidate.db')).load_session()
    assert data['assignments'] == {'MAT-G1': ('Aula Á', 1, 420, 480)}
    assert data['lab_overrides'] == {'MAT-G1'}
    course = data['courses'][0]
    assert course.preferred_day == 'Lunes' and course.preferred_start_min == 420
    assert course.group_suggestions == [{'aula': 'Aula Á', 'preferred_day': 'Lunes', 'preferred_start_min': 420}]
    assert validate_schedule(data['assignments'], course.generate_groups(), data['classrooms'],
                             TimeModel.default(), data['lab_overrides']) == []
