import sqlite3
import sys
from pathlib import Path

import pytest

from src.infrastructure.session_repository import SessionRepository
from src.scheduling.course import Course


def saved(path, code="OLD"):
    repo = SessionRepository(str(path))
    repo.save_session("source.xlsx", 7, {}, [Course(code, 1, 60, "REGULAR")], {}, None)
    return repo


def route(monkeypatch, target, legacy):
    monkeypatch.setattr(SessionRepository, "default_path", staticmethod(lambda: target))
    monkeypatch.setattr(SessionRepository, "legacy_path", staticmethod(lambda: legacy))


def test_default_path_is_per_user_and_independent_of_executable(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/read-only/version-1/SORTH.exe")
    expected = tmp_path / "SORTH" / "sorth_session.db"
    assert SessionRepository.default_path() == expected
    monkeypatch.setattr(sys, "executable", "/read-only/version-2/SORTH.exe")
    assert SessionRepository.default_path() == expected


def test_linux_ignores_relative_xdg_path(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "relative-data")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert SessionRepository.default_path() == tmp_path / ".local/share/SORTH/sorth_session.db"


def test_migration_retains_original_and_independent_backup(monkeypatch, tmp_path):
    legacy = tmp_path / "legacy.db"
    saved(legacy)
    original = legacy.read_bytes()
    target = tmp_path / "userdata/session.db"
    route(monkeypatch, target, legacy)
    repo = SessionRepository()
    assert repo.load_session()["courses"][0].code == "OLD"
    assert legacy.read_bytes() == original
    assert repo.migration_backup.exists()
    assert repo.migration_backup.stat().st_ino != target.stat().st_ino
    saved(target, "NEW")
    assert SessionRepository(str(repo.migration_backup)).load_session()["courses"][0].code == "OLD"
    assert legacy.read_bytes() == original
    assert SessionRepository().load_session()["courses"][0].code == "NEW"


def test_destination_always_wins_over_legacy(monkeypatch, tmp_path):
    legacy, target = tmp_path / "legacy.db", tmp_path / "current.db"
    saved(legacy, "OLD")
    saved(target, "CURRENT")
    route(monkeypatch, target, legacy)
    repo = SessionRepository()
    assert repo.migration_backup is None
    assert repo.load_session()["courses"][0].code == "CURRENT"


@pytest.mark.parametrize("corrupt_target", [False, True])
def test_corrupt_database_is_never_deleted_or_replaced(monkeypatch, tmp_path, corrupt_target):
    legacy, target = tmp_path / "legacy.db", tmp_path / "current.db"
    saved(legacy)
    corrupt = target if corrupt_target else legacy
    corrupt.write_bytes(b"unreadable session content")
    route(monkeypatch, target, legacy)
    before = corrupt.read_bytes()
    with pytest.raises(sqlite3.DatabaseError):
        SessionRepository()
    assert corrupt.read_bytes() == before
    if not corrupt_target:
        assert not target.exists()


def test_migration_includes_committed_wal_data(monkeypatch, tmp_path):
    legacy, target = tmp_path / "legacy.db", tmp_path / "new.db"
    saved(legacy)
    con = sqlite3.connect(legacy)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("UPDATE courses SET code='WAL'")
        con.commit()
        route(monkeypatch, target, legacy)
        assert SessionRepository().load_session()["courses"][0].code == "WAL"
    finally:
        con.close()


@pytest.mark.parametrize("error", [OSError(28, "No space left on device"), PermissionError("read-only folder")])
def test_migration_failure_does_not_create_empty_destination(monkeypatch, tmp_path, error):
    legacy, target = tmp_path / "legacy.db", tmp_path / "new.db"
    saved(legacy)
    before = legacy.read_bytes()
    route(monkeypatch, target, legacy)
    def fail(*args):
        raise error
    monkeypatch.setattr(SessionRepository, "_snapshot", staticmethod(fail))
    with pytest.raises(OSError):
        SessionRepository()
    assert not target.exists()
    assert legacy.read_bytes() == before


def test_connections_close_after_use(tmp_path):
    repo = saved(tmp_path / "session.db")
    with repo._connect() as con:
        con.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        con.execute("SELECT 1")


def test_real_read_only_database_save_preserves_previous_state(monkeypatch, tmp_path):
    from contextlib import contextmanager
    path = tmp_path / "session.db"
    repo = saved(path)
    @contextmanager
    def readonly():
        con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()
    monkeypatch.setattr(repo, "_connect", readonly)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        repo.save_session(None, 0, {}, [], {}, None)
    assert repo.load_session()["courses"][0].code == "OLD"


def test_competing_destination_is_not_clobbered(monkeypatch, tmp_path):
    import os
    legacy, target = tmp_path / "legacy.db", tmp_path / "current.db"
    saved(legacy)
    route(monkeypatch, target, legacy)
    def competing_instance(*args):
        saved(target, "WINNER")
        raise FileExistsError()
    monkeypatch.setattr(os, "link", competing_instance)
    repo = SessionRepository()
    assert repo.load_session()["courses"][0].code == "WINNER"
    assert SessionRepository(str(repo.migration_backup)).load_session()["courses"][0].code == "OLD"
