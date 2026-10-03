# src/infrastructure/session_repository.py

import json
import sqlite3
import os
import sys
import tempfile
from contextlib import contextmanager, closing
from pathlib import Path

from ..scheduling.classroom import Classroom
from ..scheduling.course import Course
from ..scheduling.project_calendar import ProjectCalendar
from ..scheduling.teaching_resources import SchedulingResources
from ..scheduling.validation import validate_schedule
from ..scheduling.time_model import TimeModel


class SessionRepository:
    """
    Persists and restores a SORTH working session using SQLite.

    Stores: classrooms, courses (with per-group suggestions), classroom
    restrictions, the last generated schedule (assignments), and session
    metadata (excel path, seed).

    The database lives in the current user's SORTH application-data directory.
    """

    SCHEMA_VERSION = 4

    @staticmethod
    def default_path() -> Path:
        """Stable writable user data, independent of installation/update folders."""
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            candidate = Path(os.environ.get("XDG_DATA_HOME", ""))
            base = candidate if candidate.is_absolute() else Path.home() / ".local" / "share"
        return base / "SORTH" / "sorth_session.db"

    @staticmethod
    def legacy_path() -> Path:
        base = (Path(sys.executable).parent if getattr(sys, "frozen", False)
                else Path(__file__).resolve().parents[2])
        return base / "data" / "sorth_session.db"

    def __init__(self, db_path: str | None = None):
        self.migration_backup: Path | None = None
        self.schema_backup: Path | None = None
        target = Path(db_path) if db_path is not None else self.default_path()
        self._db_path = str(target)
        if db_path is None:
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            legacy = self.legacy_path()
            # Any existing destination wins, even when corrupt or empty. Never
            # replace user data with an older copy or silently fall back.
            if not target.exists() and legacy.exists() and legacy != target:
                backup = self._snapshot(legacy, target.parent, "legacy-session-")
                self.migration_backup = backup
                staged = self._snapshot(backup, target.parent, ".migration-")
                try:
                    # Atomic, no-clobber installation. A competing instance wins.
                    os.link(staged, target)
                except FileExistsError:
                    pass
                finally:
                    staged.unlink(missing_ok=True)
        self._init_db()

    @staticmethod
    def _snapshot(source: Path, directory: Path, prefix: str) -> Path:
        """Create an independent consistent SQLite backup; preserve source/WAL."""
        fd, name = tempfile.mkstemp(prefix=prefix, suffix=".db", dir=directory)
        os.close(fd)
        snapshot = Path(name)
        try:
            with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as src:
                if src.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise sqlite3.DatabaseError("SQLite integrity check failed")
                with closing(sqlite3.connect(snapshot)) as dst:
                    src.backup(dst)
            with snapshot.open("rb+") as stream:
                os.fsync(stream.fileno())
            return snapshot
        except Exception:
            # Only our new temporary file is removed; the source is untouched.
            snapshot.unlink(missing_ok=True)
            raise

    def backup_session(self) -> Path:
        path = Path(self._db_path)
        return self._snapshot(path, path.parent, "previous-session-")

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_db(self):
        with self._connect() as con:
            if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("SQLite integrity check failed")
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version > self.SCHEMA_VERSION:
                raise sqlite3.DatabaseError(
                    f"Session schema {version} is newer than supported {self.SCHEMA_VERSION}. "
                    "Open it with the newer SORTH version; do not overwrite it."
                )
            # Schema3 introduced a mandatory resource contract for saved
            # sessions. Missing/corrupt new-format rows are not legacy defaults.
            # Check before CREATE TABLE or migration writes can repair evidence.
            if version >= 3:
                self._read_resource_contract(con)
            if version >= 4:
                self._read_calendar_contract(con)
            if version == self.SCHEMA_VERSION:
                # Current-format opening is read-only. Never rewrite schema/header
                # bytes before complete semantic validation of saved constraints.
                self.load_session()
                return
            if version < self.SCHEMA_VERSION and con.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1").fetchone():
                path = Path(self._db_path)
                self.schema_backup = self._snapshot(path, path.parent, "schema-session-")
            con.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS project_calendar (
                    id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scheduling_resources (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS session (
                    id          INTEGER PRIMARY KEY CHECK (id = 1),
                    excel_path  TEXT,
                    seed        INTEGER,
                    saved_at    TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS classrooms (
                    name        TEXT PRIMARY KEY,
                    capacity    INTEGER NOT NULL,
                    room_type   TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    campus      TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS courses (
                    code                TEXT PRIMARY KEY,
                    name                TEXT,
                    number_of_groups    INTEGER NOT NULL,
                    duration_min        INTEGER NOT NULL,
                    required_room_type  TEXT NOT NULL,
                    size                INTEGER NOT NULL DEFAULT 0,
                    suggested_classroom TEXT,
                    preferred_day       TEXT,
                    preferred_start_min INTEGER,
                    force_split         INTEGER  -- NULL=auto, 1=force, 0=never
                );

                CREATE TABLE IF NOT EXISTS course_group_suggestions (
                    course_code         TEXT NOT NULL,
                    group_index         INTEGER NOT NULL,
                    aula                TEXT,
                    preferred_day       TEXT,
                    preferred_start_min INTEGER,
                    PRIMARY KEY (course_code, group_index)
                );

                CREATE TABLE IF NOT EXISTS restrictions (
                    classroom_name  TEXT NOT NULL,
                    course_code     TEXT NOT NULL,
                    PRIMARY KEY (classroom_name, course_code)
                );

                CREATE TABLE IF NOT EXISTS assignments (
                    group_id        TEXT PRIMARY KEY,
                    classroom_name  TEXT NOT NULL,
                    day             INTEGER NOT NULL,
                    start_min       INTEGER NOT NULL,
                    end_min         INTEGER NOT NULL,
                    lab_override    INTEGER NOT NULL DEFAULT 0
                );
            """)
            # Older sessions did not persist enrollment. Add the missing column
            # in place so existing courses, suggestions and schedules survive.
            # Zero preserves the Course default when the original size is unknown.
            course_columns = {
                row["name"] for row in con.execute("PRAGMA table_info(courses)")
            }
            if "size" not in course_columns:
                con.execute(
                    "ALTER TABLE courses ADD COLUMN size INTEGER NOT NULL DEFAULT 0"
                )

            assignment_columns = {
                row["name"] for row in con.execute("PRAGMA table_info(assignments)")
            }
            if "lab_override" not in assignment_columns:
                con.execute(
                    "ALTER TABLE assignments ADD COLUMN lab_override INTEGER NOT NULL DEFAULT 0"
                )
            if "pinned" not in assignment_columns:
                con.execute("ALTER TABLE assignments ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1))")
            if version < 4:
                con.execute("INSERT OR IGNORE INTO project_calendar SELECT 1, ? WHERE EXISTS (SELECT 1 FROM session WHERE id=1)",
                            (json.dumps(ProjectCalendar().to_dict(), ensure_ascii=False),))
            if version < 3 and con.execute("SELECT 1 FROM session WHERE id=1").fetchone():
                # Only a genuine legacy migration initializes absence, in the
                # same transaction as the schema change and after the backup.
                con.execute("INSERT OR IGNORE INTO scheduling_resources VALUES (1, ?)",
                            (json.dumps(SchedulingResources().to_data()),))
            self._read_resource_contract(con)
            con.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self._db_path)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_session(self, excel_path: str | None, seed: int | None,
                     classrooms: dict[str, Classroom],
                     courses: list[Course],
                     restrictions: dict[str, set[str]],
                     assignments: dict | None, lab_overrides=(), pinned_group_ids=(), resources=None, calendar=None,
                     *, before_commit=None):
        pinned_group_ids = frozenset(pinned_group_ids)
        if not pinned_group_ids.issubset(assignments or {}):
            raise ValueError("Pinned sessions must have assignments")
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            existing_calendar = self._read_calendar_contract(con)
            calendar = existing_calendar if calendar is None else ProjectCalendar.from_dict(calendar.to_dict())
            existing_resources = self._read_resource_contract(con)
            if con.execute("SELECT 1 FROM session WHERE id=1").fetchone():
                # Reject semantic corruption in the accepted version even if a
                # caller offers an explicit replacement extension.
                self.load_session()
            resources = existing_resources if resources is None else resources
            self._validate_resources(resources, courses, classrooms, restrictions, assignments, lab_overrides, calendar)
            con.execute("INSERT INTO project_calendar VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                        (json.dumps(calendar.to_dict(), ensure_ascii=False),))
            con.execute("INSERT INTO scheduling_resources VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                        (json.dumps(resources.to_data(), ensure_ascii=False),))
            # Session metadata
            con.execute("""
                INSERT INTO session (id, excel_path, seed, saved_at)
                VALUES (1, ?, ?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    excel_path = excluded.excel_path,
                    seed       = excluded.seed,
                    saved_at   = excluded.saved_at
            """, (excel_path, seed))

            # Classrooms
            con.execute("DELETE FROM classrooms")
            con.executemany("""
                INSERT INTO classrooms (name, capacity, room_type, description, campus)
                VALUES (?, ?, ?, ?, ?)
            """, [(c.name, c.capacity, c.room_type, c.description, c.campus)
                  for c in classrooms.values()])

            # Courses + per-group suggestions
            con.execute("DELETE FROM courses")
            con.execute("DELETE FROM course_group_suggestions")
            for course in courses:
                fs = None if course.force_split is None else (1 if course.force_split else 0)
                con.execute("""
                    INSERT INTO courses
                        (code, name, number_of_groups, duration_min, required_room_type, size,
                         suggested_classroom, preferred_day, preferred_start_min, force_split)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (course.code, course.name, course.number_of_groups,
                      course.duration_min, course.required_room_type, course.size,
                      course.suggested_classroom, course.preferred_day,
                      course.preferred_start_min, fs))
                for idx, sg in enumerate(course.group_suggestions):
                    con.execute("""
                        INSERT INTO course_group_suggestions
                            (course_code, group_index, aula, preferred_day, preferred_start_min)
                        VALUES (?, ?, ?, ?, ?)
                    """, (course.code, idx,
                          sg.get("aula"), sg.get("preferred_day"),
                          sg.get("preferred_start_min")))

            # Restrictions
            con.execute("DELETE FROM restrictions")
            for cls_name, codes in restrictions.items():
                con.executemany("""
                    INSERT INTO restrictions (classroom_name, course_code) VALUES (?, ?)
                """, [(cls_name, code) for code in codes])

            # Assignments
            con.execute("DELETE FROM assignments")
            if assignments:
                con.executemany("""
                    INSERT INTO assignments
                        (group_id, classroom_name, day, start_min, end_min, lab_override, pinned)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [(gid, cls, day, s, e, int(gid in lab_overrides), int(gid in pinned_group_ids))
                      for gid, (cls, day, s, e) in assignments.items()])

            # Application unit-of-work hook: no event pumping or nested writes.
            # An exception rolls back all SQL, including a late commit failure.
            if before_commit is not None:
                before_commit()

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_session(self) -> dict | None:
        """
        Returns a dict with keys:
            excel_path, seed, classrooms, courses, restrictions, assignments
        or None if no session exists.
        """
        with self._connect() as con:
            # All tables belong to one consistent snapshot, including in WAL mode.
            con.execute("BEGIN")
            resources = self._read_resource_contract(con)
            row = con.execute("SELECT * FROM session WHERE id = 1").fetchone()
            if not row:
                return None

            # Classrooms
            classrooms = {}
            for r in con.execute("SELECT * FROM classrooms"):
                c = Classroom(r["name"], r["capacity"], r["room_type"],
                              r["description"], r["campus"])
                classrooms[c.name] = c

            # Per-group suggestions grouped by course
            suggestions_by_code: dict[str, list] = {}
            for r in con.execute(
                "SELECT * FROM course_group_suggestions ORDER BY course_code, group_index"
            ):
                suggestions_by_code.setdefault(r["course_code"], []).append({
                    "aula":                r["aula"],
                    "preferred_day":       r["preferred_day"],
                    "preferred_start_min": r["preferred_start_min"],
                })

            # Courses
            courses = []
            for r in con.execute("SELECT * FROM courses"):
                fs_raw = r["force_split"]
                force_split = None if fs_raw is None else bool(fs_raw)
                courses.append(Course(
                    code=r["code"],
                    name=r["name"],
                    number_of_groups=r["number_of_groups"],
                    duration_min=r["duration_min"],
                    required_room_type=r["required_room_type"],
                    size=r["size"],
                    suggested_classroom=r["suggested_classroom"],
                    preferred_day=r["preferred_day"],
                    preferred_start_min=r["preferred_start_min"],
                    force_split=force_split,
                    group_suggestions=suggestions_by_code.get(r["code"], []),
                ))

            # Restrictions
            restrictions: dict[str, set[str]] = {}
            for r in con.execute("SELECT * FROM restrictions"):
                restrictions.setdefault(r["classroom_name"], set()).add(r["course_code"])

            # Assignments
            assignments = {}
            lab_overrides = set()
            pinned_group_ids = set()
            for r in con.execute("SELECT * FROM assignments"):
                if r["pinned"]:
                    pinned_group_ids.add(r["group_id"])
                if r["lab_override"]:
                    lab_overrides.add(r["group_id"])
                assignments[r["group_id"]] = (
                    r["classroom_name"], r["day"], r["start_min"], r["end_min"]
                )

            calendar = self._read_calendar_contract(con)
            self._validate_resources(resources, courses, classrooms, restrictions, assignments, lab_overrides, calendar)
            return {
                "calendar": calendar,
                "resources": resources,
                "excel_path":   row["excel_path"],
                "seed":         row["seed"],
                "classrooms":   classrooms,
                "courses":      courses,
                "restrictions": restrictions,
                "assignments":  assignments if assignments else None,
                "lab_overrides": lab_overrides,
                "pinned_group_ids": pinned_group_ids,
            }

    def has_session(self) -> bool:
        """Even a classroom-only or deliberately empty saved session is recoverable."""
        with self._connect() as con:
            self._read_resource_contract(con)
            if con.execute("SELECT id FROM session WHERE id = 1").fetchone() is not None:
                return True
            # An incomplete/corrupt logical session must not be mistaken for an
            # empty database and silently replaced on the next edit.
            for query in ("SELECT 1 FROM classrooms LIMIT 1", "SELECT 1 FROM courses LIMIT 1",
                          "SELECT 1 FROM course_group_suggestions LIMIT 1",
                          "SELECT 1 FROM restrictions LIMIT 1", "SELECT 1 FROM assignments LIMIT 1"):
                if con.execute(query).fetchone():
                    raise sqlite3.DatabaseError("Session data exists without session metadata. Preserve the database and recover a backup.")
            return False

    def get_course_completions(self) -> list[tuple[str, str]]:
        """Return list of (code, name) for all saved courses, for autocomplete."""
        with self._connect() as con:
            rows = con.execute("SELECT code, name FROM courses ORDER BY code").fetchall()
            return [(r["code"], r["name"] or "") for r in rows]

    def clear_session(self):
        with self._connect() as con:
            # executescript commits implicitly; individual statements retain the
            # transaction so a late failure cannot leave a partially erased session.
            for query in ("DELETE FROM project_calendar", "DELETE FROM scheduling_resources", "DELETE FROM assignments", "DELETE FROM restrictions",
                          "DELETE FROM course_group_suggestions", "DELETE FROM courses",
                          "DELETE FROM classrooms", "DELETE FROM session"):
                con.execute(query)

    @staticmethod
    def _validate_resources(resources, courses, classrooms, restrictions, assignments, lab_overrides, calendar):
        # Preserve the legacy loader's repair flow for old LAB placements when
        # no optional records exist. A resource-bearing snapshot is strictly
        # checked before any write, or before it can become the live session.
        from copy import deepcopy
        groups = [g for c in courses for g in c.generate_groups()]
        errors = resources.structure_issues({g.group_id for g in groups}, TimeModel.from_calendar(calendar))
        if calendar != ProjectCalendar() or any(c.resources or c.memberships for c in resources.catalogs):
            rooms = deepcopy(classrooms)
            for name, room in rooms.items():
                room.allowed_courses = restrictions.get(name)
            errors.extend(validate_schedule(assignments or {}, groups, rooms,
                          TimeModel.from_calendar(calendar), lab_overrides, resources))
        if errors:
            raise ValueError('; '.join(str(e) for e in errors))

    @staticmethod
    def _decode_resources(payload):
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate resource JSON field')
                result[key] = value
            return result
        return SchedulingResources.from_data(json.loads(payload, object_pairs_hook=unique_object))

    @staticmethod
    def _decode_calendar(payload):
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate calendar key')
                result[key] = value
            return result
        return ProjectCalendar.from_dict(json.loads(payload, object_pairs_hook=unique_object))
    @classmethod
    def _read_resource_contract(cls, con):
        saved = con.execute("SELECT 1 FROM session WHERE id=1").fetchone() is not None
        rows = con.execute("SELECT id, payload FROM scheduling_resources").fetchall()
        if not saved and not rows:
            return SchedulingResources()
        if not saved:
            raise sqlite3.DatabaseError('Resource data exists without session metadata; restore a backup')
        if len(rows) != 1 or rows[0]['id'] != 1:
            raise sqlite3.DatabaseError('Saved session resource contract is missing or inconsistent; restore a backup')
        return cls._decode_resources(rows[0]['payload'])

    @classmethod
    def _read_calendar_contract(cls, con):
        saved = con.execute("SELECT 1 FROM session WHERE id=1").fetchone() is not None
        rows = con.execute("SELECT id, payload FROM project_calendar").fetchall()
        if not saved and not rows:
            return ProjectCalendar()
        if not saved:
            raise sqlite3.DatabaseError('Calendar data exists without session metadata; restore a backup')
        if len(rows) != 1 or rows[0]['id'] != 1:
            raise sqlite3.DatabaseError('Saved project calendar is missing or inconsistent; restore a backup')
        return cls._decode_calendar(rows[0]['payload'])
