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
