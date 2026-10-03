"""Persistence regressions use isolated databases, never user data."""
import sqlite3

import pytest

from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.mark.parametrize("size,force_split", [(0, None), (37, False), (120, True)])
def test_session_roundtrip_preserves_all_fields(tmp_path, size, force_split):
    db_path = tmp_path / "session.db"
    repository = SessionRepository(str(db_path))
    room = Classroom("L101", 150, "LAB", "Laboratorio", "HO")
    course = Course(
        code="BIO101", name="Biología", number_of_groups=2, duration_min=300,
        required_room_type="LAB", size=size, suggested_classroom="L101",
        preferred_day="Lunes", preferred_start_min=480, force_split=force_split,
        group_suggestions=[
            {"aula": "L101", "preferred_day": "Martes", "preferred_start_min": 540},
            {"aula": None, "preferred_day": None, "preferred_start_min": None},
        ],
    )
    restrictions = {"L101": {"BIO101", "BIO102"}}
    assignments = {course.generate_groups()[0].group_id: ("L101", 2, 540, 660)}
    repository.save_session("input/Cursos.xlsx", 42, {room.name: room},
                            [course], restrictions, assignments)

    # Reopening also exercises initialization on an already-current schema.
    reopened = SessionRepository(str(db_path))
    restored = reopened.load_session()
    assert reopened.has_session()
    assert restored["excel_path"] == "input/Cursos.xlsx"
    assert restored["seed"] == 42
    assert vars(restored["classrooms"]["L101"]) == vars(room)
    assert len(restored["courses"]) == 1
    assert vars(restored["courses"][0]) == vars(course)
    assert all(group.size == size for group in restored["courses"][0].generate_groups())
    assert restored["restrictions"] == restrictions
    assert restored["assignments"] == assignments
    assert reopened.get_course_completions() == [("BIO101", "Biología")]


def test_legacy_migration_preserves_existing_data_and_is_idempotent(tmp_path):
    db_path = tmp_path / "legacy.db"
    # Define the original schema independently of the repository initializer.
    with sqlite3.connect(db_path) as con:
        con.executescript("""
            CREATE TABLE session (
                id INTEGER PRIMARY KEY CHECK (id = 1), excel_path TEXT,
                seed INTEGER, saved_at TEXT DEFAULT (datetime('now')));
            CREATE TABLE classrooms (
                name TEXT PRIMARY KEY, capacity INTEGER NOT NULL,
                room_type TEXT NOT NULL, description TEXT DEFAULT '', campus TEXT DEFAULT '');
            CREATE TABLE courses (
                code TEXT PRIMARY KEY, name TEXT, number_of_groups INTEGER NOT NULL,
                duration_min INTEGER NOT NULL, required_room_type TEXT NOT NULL,
                suggested_classroom TEXT, preferred_day TEXT,
                preferred_start_min INTEGER, force_split INTEGER);
            CREATE TABLE course_group_suggestions (
                course_code TEXT NOT NULL, group_index INTEGER NOT NULL,
                aula TEXT, preferred_day TEXT, preferred_start_min INTEGER,
                PRIMARY KEY (course_code, group_index));
            CREATE TABLE restrictions (
                classroom_name TEXT NOT NULL, course_code TEXT NOT NULL,
                PRIMARY KEY (classroom_name, course_code));
            CREATE TABLE assignments (
                group_id TEXT PRIMARY KEY, classroom_name TEXT NOT NULL,
                day INTEGER NOT NULL, start_min INTEGER NOT NULL, end_min INTEGER NOT NULL);
            INSERT INTO session VALUES (1, 'legacy.xlsx', 17, '2025-01-01 12:00:00');
            INSERT INTO classrooms VALUES ('601', 60, 'REGULAR', 'Aula', 'HO');
            INSERT INTO courses VALUES
                ('BIO101', 'Biología', 1, 120, 'REGULAR', '601', 'Lunes', 480, 0);
            INSERT INTO course_group_suggestions VALUES ('BIO101', 0, '601', 'Martes', 540);
            INSERT INTO restrictions VALUES ('601', 'BIO101');
            INSERT INTO assignments VALUES ('BIO101-G1', '601', 2, 540, 660);
        """)
        original_columns = [row[1] for row in con.execute("PRAGMA table_info(courses)")]
        original_course = con.execute("SELECT * FROM courses").fetchall()
        tables = ["session", "classrooms", "course_group_suggestions", "restrictions", "assignments"]
        original_rows = {table: con.execute(f"SELECT * FROM {table}").fetchall() for table in tables}

    repository = SessionRepository(str(db_path))
    restored = repository.load_session()
    assert repository.has_session()
    assert restored["courses"][0].size == 0
    assert restored["courses"][0].group_suggestions == [
        {"aula": "601", "preferred_day": "Martes", "preferred_start_min": 540}
    ]
    assert restored["assignments"] == {"BIO101-G1": ("601", 2, 540, 660)}
    with sqlite3.connect(db_path) as con:
        for table in tables:
            columns = "group_id, classroom_name, day, start_min, end_min" if table == "assignments" else "*"
            assert con.execute(f"SELECT {columns} FROM {table}").fetchall() == original_rows[table]
        assert con.execute(f"SELECT {', '.join(original_columns)} FROM courses").fetchall() == original_course
        columns = {row[1]: row for row in con.execute("PRAGMA table_info(courses)")}
        assert columns["size"][2:5] == ("INTEGER", 1, "0")

    restored["courses"][0].size = 32
    repository.save_session(**restored)
    reopened = SessionRepository(str(db_path))
    assert reopened.load_session()["courses"][0].size == 32
    with sqlite3.connect(db_path) as con:
        assert [row[1] for row in con.execute("PRAGMA table_info(courses)")].count("size") == 1


def test_replacing_session_removes_stale_records(tmp_path):
    repository = SessionRepository(str(tmp_path / "session.db"))
    room = Classroom("101", 40, "REGULAR")
    old = Course("OLD", 1, 60, "REGULAR", size=12, group_suggestions=[{"aula": "101"}])
    repository.save_session("old.xlsx", 1, {"101": room}, [old], {"101": {"OLD"}},
                            {"OLD-G1": ("101", 1, 480, 540)})
    new = Course("NEW", 1, 90, "REGULAR", size=25)
    repository.save_session(None, None, {"101": room}, [new], {}, None)
    restored = repository.load_session()
    assert restored["excel_path"] is None
    assert restored["seed"] is None
    assert [course.code for course in restored["courses"]] == ["NEW"]
    assert restored["courses"][0].size == 25
    assert restored["courses"][0].group_suggestions == []
    assert restored["restrictions"] == {}
    assert restored["assignments"] is None
    assert repository.get_course_completions() == [("NEW", "")]
    with sqlite3.connect(repository._db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM course_group_suggestions").fetchone()[0] == 0


def test_failed_save_rolls_back_session(tmp_path):
    repository = SessionRepository(str(tmp_path / "session.db"))
    original = Course("BIO101", 1, 60, "REGULAR", size=30)
    repository.save_session("original.xlsx", 7, {}, [original], {}, None)
    duplicate = Course("DUP", 1, 60, "REGULAR", size=15)
    with pytest.raises(sqlite3.IntegrityError):
        repository.save_session("replacement.xlsx", 8, {}, [duplicate, duplicate], {}, None)
    restored = repository.load_session()
    assert restored["excel_path"] == "original.xlsx"
    assert restored["seed"] == 7
    assert vars(restored["courses"][0]) == vars(original)


def test_empty_and_cleared_sessions(tmp_path):
    repository = SessionRepository(str(tmp_path / "session.db"))
    assert repository.load_session() is None
    assert not repository.has_session()
    assert repository.get_course_completions() == []
    repository.save_session(None, None, {}, [], {}, None)
    assert repository.has_session()
    repository.save_session(None, 0, {}, [Course("BIO101", 1, 60, "REGULAR")], {}, None)
    assert repository.has_session()
    repository.clear_session()
    assert repository.load_session() is None
    assert not repository.has_session()
    assert repository.get_course_completions() == []


def test_lab_override_roundtrip_on_fresh_and_reopened_database(tmp_path):
    """Fresh schema must accept every field written by assignment persistence."""
    path = tmp_path / "fresh.db"
    repository = SessionRepository(str(path))
    assignments = {"REG-G1": ("LAB1", 1, 480, 540), "REG-G2": ("R1", 2, 480, 540)}
    repository.save_session(None, 9, {}, [], {}, assignments, {"REG-G1"})
    restored = SessionRepository(str(path)).load_session()
    assert restored["assignments"] == assignments
    assert restored["lab_overrides"] == {"REG-G1"}
    with sqlite3.connect(path) as con:
        columns = {row[1]: row for row in con.execute("PRAGMA table_info(assignments)")}
        assert columns["lab_override"][2:5] == ("INTEGER", 1, "0")


def test_legacy_assignment_migration_preserves_rows_and_defaults_override_false(tmp_path):
    path = tmp_path / "legacy-assignment.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE assignments (group_id TEXT PRIMARY KEY, classroom_name TEXT NOT NULL, day INTEGER NOT NULL, start_min INTEGER NOT NULL, end_min INTEGER NOT NULL)")
        con.execute("INSERT INTO assignments VALUES ('OLD-G1', 'R1', 1, 480, 540)")
    SessionRepository(str(path))
    SessionRepository(str(path))
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT * FROM assignments").fetchall() == [("OLD-G1", "R1", 1, 480, 540, 0, 0)]
        assert [row[1] for row in con.execute("PRAGMA table_info(assignments)")].count("lab_override") == 1
