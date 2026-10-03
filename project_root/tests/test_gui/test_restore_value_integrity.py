"""Malformed saved values cannot be silently normalized by Qt and autosave."""
import sqlite3

import pytest
from PyQt6.QtCore import QSettings

from src.gui.main_window import MainWindow
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


@pytest.fixture
def window(tmp_path):
    repo = SessionRepository(str(tmp_path / 'session.db'))
    settings = QSettings(str(tmp_path / 'settings.ini'), QSettings.Format.IniFormat)
    win = MainWindow(repo, restore_session=False, feature_settings=settings)
    yield win
    win._unsaved = False
    win.close()


@pytest.mark.parametrize('seed', [-1, 1000000, 2**40, 1.5, 'not a seed'])
def test_out_of_range_seed_restore_blocks_autosave_without_clamping(window, tmp_path, seed):
    repo = window._repo
    repo.save_session(None, seed, {}, [Course('BIO', 1, 60, 'REGULAR')], {}, None)
    before = (tmp_path / 'session.db').read_bytes()

    window._restore_session_if_exists(confirm=False, show_status=False)

    assert window._restore_failed
    assert not window._save_session()
    assert (tmp_path / 'session.db').read_bytes() == before
    assert repo.load_session()['seed'] == seed


@pytest.mark.parametrize('pinned', [False, True])
def test_assignments_without_courses_cannot_be_discarded_by_restore(window, tmp_path, pinned):
    repo = window._repo
    repo.save_session(None, 42, {'R': Classroom('R', 30, 'REGULAR')},
                      [Course('BIO', 1, 60, 'REGULAR')], {},
                      {'BIO-G1': ('R', 1, 480, 540)},
                      pinned_group_ids={'BIO-G1'} if pinned else set())
    with sqlite3.connect(repo._db_path) as con:
        con.execute('DELETE FROM courses')
    before = (tmp_path / 'session.db').read_bytes()

    window._restore_session_if_exists(confirm=False, show_status=False)

    assert window._restore_failed
    assert not window._save_session()
    assert (tmp_path / 'session.db').read_bytes() == before
    assert repo.load_session()['assignments'] == {'BIO-G1': ('R', 1, 480, 540)}


@pytest.mark.parametrize('seed', [None, 0, 999999])
def test_valid_empty_session_restores_and_roundtrips_seed(window, seed):
    window._repo.save_session(None, seed, {}, [], {}, None)

    window._restore_session_if_exists(confirm=False, show_status=False)

    assert not window._restore_failed
    assert window._save_session()
    assert window._repo.load_session()['seed'] == seed
