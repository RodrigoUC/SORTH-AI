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
    assignments = {course.generate_groups()[0].group_id: ("L101", 2, 420, 420 + course.generate_groups()[0].duration_min)}
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
    with pytest.raises(ValueError, match="duplicado"):
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
    assignments = {"LAB-G1": ("LAB1", 1, 480, 540), "LAB-G2": ("R1", 2, 480, 540)}
    rooms = {"LAB1": Classroom("LAB1", 30, "LAB"), "R1": Classroom("R1", 30, "REGULAR")}
    repository.save_session(None, 9, rooms, [Course("LAB", 2, 60, "LAB")], {}, assignments, {"LAB-G2"})
    restored = SessionRepository(str(path)).load_session()
    assert restored["assignments"] == assignments
    assert restored["lab_overrides"] == {"LAB-G2"}
    with sqlite3.connect(path) as con:
        columns = {row[1]: row for row in con.execute("PRAGMA table_info(assignments)")}
        assert columns["lab_override"][2:5] == ("INTEGER", 1, "0")
