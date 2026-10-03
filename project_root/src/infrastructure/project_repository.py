"""Local named projects and immutable scenarios, independent of the working DB.

IDs, never display names, identify records. SQLite transactions commit the project,
metadata and full SQLite snapshot together. A failed insert cannot replace a
scenario. SessionRepository remains the only owner of session migrations.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
import tempfile
import unicodedata
import uuid

from .session_repository import SessionRepository


class ProjectRepository:
    SCHEMA_VERSION = 1

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            version = con.execute('PRAGMA user_version').fetchone()[0]
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version > self.SCHEMA_VERSION or (tables and version != self.SCHEMA_VERSION):
                raise sqlite3.DatabaseError('Unsupported project catalog; original preserved')
            if con.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise sqlite3.DatabaseError('Project catalog integrity check failed')
            con.executescript('''BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, name_key TEXT UNIQUE NOT NULL);
                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    name TEXT NOT NULL, name_key TEXT NOT NULL, snapshot BLOB NOT NULL,
                    metadata TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(project_id, name_key));
                CREATE TABLE IF NOT EXISTS imports (source TEXT PRIMARY KEY, scenario_id TEXT NOT NULL);
                PRAGMA user_version = 1; COMMIT;''')

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        try:
            with con:
                yield con
        finally:
            con.close()

    @staticmethod
    def _name(name):
        name = unicodedata.normalize('NFC', name.strip())
        if not name or len(name) > 120 or any(unicodedata.category(c).startswith('C') for c in name):
            raise ValueError('Names require 1–120 visible characters')
        return name, name.casefold()

    @staticmethod
    def _capture(repo):
        # The backup API includes WAL and future fields (such as pin flags).
        source = Path(repo._db_path)
        with tempfile.TemporaryDirectory(prefix='sorth-scenario-') as directory:
            path = SessionRepository._snapshot(source, Path(directory), 'snapshot-')
            snapshot_repo = SessionRepository(str(path))
            data = snapshot_repo.load_session()
            if data is None:
                raise ValueError('No saved working session')
            return path.read_bytes()

    def _insert(self, con, project_id, name, blob, metadata):
        name, key = self._name(name)
        scenario_id = uuid.uuid4().hex
        con.execute('INSERT INTO scenarios(id,project_id,name,name_key,snapshot,metadata) VALUES (?,?,?,?,?,?)',
                    (scenario_id, project_id, name, key, blob, json.dumps(metadata, ensure_ascii=False, sort_keys=True)))
        return scenario_id

    def create_project(self, name, scenario_name, repo, metadata):
        name, key = self._name(name)
        blob = self._capture(repo)
        project_id = uuid.uuid4().hex
        with self._connect() as con:
            con.execute('INSERT INTO projects VALUES (?,?,?)', (project_id, name, key))
            scenario_id = self._insert(con, project_id, scenario_name, blob, metadata)
        return project_id, scenario_id

    def save_as(self, project_id, name, repo, metadata):
        blob = self._capture(repo)
        with self._connect() as con:
            return self._insert(con, project_id, name, blob, metadata)

    def duplicate(self, scenario_id, name):
        with self._connect() as con:
            row = con.execute('SELECT * FROM scenarios WHERE id=?', (scenario_id,)).fetchone()
            if row is None:
                raise KeyError(scenario_id)
            return self._insert(con, row['project_id'], name, row['snapshot'], json.loads(row['metadata']))

    def rename(self, scenario_id, name):
        name, key = self._name(name)
        with self._connect() as con:
            cursor = con.execute('UPDATE scenarios SET name=?,name_key=? WHERE id=?', (name, key, scenario_id))
            if cursor.rowcount != 1:
                raise KeyError(scenario_id)

    def list_scenarios(self):
        with self._connect() as con:
            return [dict(row) for row in con.execute('''SELECT s.id,s.project_id,p.name AS project_name,
                s.name,s.created_at FROM scenarios s JOIN projects p ON p.id=s.project_id
                ORDER BY p.name_key,s.created_at,s.rowid''')]

    def read(self, scenario_id):
        with self._connect() as con:
            row = con.execute('SELECT snapshot,metadata FROM scenarios WHERE id=?', (scenario_id,)).fetchone()
            if row is None:
                raise KeyError(scenario_id)
        # Opening/migration happens only on an expendable copy. The catalog blob
        # is immutable even if a newer session schema cannot be loaded.
        with tempfile.TemporaryDirectory(prefix='sorth-scenario-') as directory:
            path = Path(directory) / 'session.db'
            path.write_bytes(row['snapshot'])
            data = SessionRepository(str(path)).load_session()
            if data is None:
                raise ValueError('Empty scenario snapshot')
        return data, json.loads(row['metadata'])

    def preserve_legacy(self, repo, metadata):
        """Idempotently retain the original single session before any scenario use."""
        source = str(Path(repo._db_path).resolve())
        with self._connect() as con:
            con.execute('BEGIN IMMEDIATE')
            old = con.execute('SELECT scenario_id FROM imports WHERE source=?', (source,)).fetchone()
            if old:
                return old[0]
            if not repo.has_session():
                return None
            blob = self._capture(repo)
            project_id = uuid.uuid4().hex
            # A deterministic display prefix and unique ID avoid stealing names.
            name = 'Recovered ' + project_id[:12]
            con.execute('INSERT INTO projects VALUES (?,?,?)', (project_id, name, name.casefold()))
            scenario_id = self._insert(con, project_id, 'Original', blob, metadata)
            con.execute('INSERT INTO imports VALUES (?,?)', (source, scenario_id))
            return scenario_id
