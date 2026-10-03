"""Snapshot identity must use consistent APIs and keep every mutation guard."""
import builtins
from types import SimpleNamespace
import pandas as pd
import pytest
from src.infrastructure import import_candidate
from src.infrastructure.excel_reader import ExcelImportError, ImportCancelled

@pytest.fixture
def workbook(tmp_path):
    path = tmp_path / 'stable.xlsx'
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'# DE AULA': ['R'], 'CAPACIDAD': [30]}).to_excel(writer, sheet_name='Aulas', index=False)
        pd.DataFrame({'Curso': ['BIO'], 'Aula': ['R']}).to_excel(writer, sheet_name='Cursos', index=False)
    return path

def metadata(result, **changes):
    values = {name: getattr(result, name) for name in
              ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')}
    return SimpleNamespace(**{**values, **changes})

def test_windows_path_creation_time_differs_from_handle_change_time(workbook, monkeypatch):
    """CPython 3.12 Windows stat(path) ctime is birthtime; fstat is change time."""
    original_stat = import_candidate.os.stat
    original_fstat = import_candidate.os.fstat
    calls = []
    def path_stat(path, *args, **kwargs):
        result = original_stat(path, *args, **kwargs)
        if str(path) == str(workbook):
            return metadata(result, st_ctime_ns=result.st_ctime_ns - 1_000_000)
        return result
    def handle_stat(fd):
        calls.append(fd)
        return original_fstat(fd)
    monkeypatch.setattr(import_candidate.os, 'stat', path_stat)
    monkeypatch.setattr(import_candidate.os, 'fstat', handle_stat)
    candidate = import_candidate.read_candidate(str(workbook), lambda: False)
    assert candidate.imported.courses[0].code == 'BIO'
    assert len(calls) == 3
    assert calls[0] == calls[1] and calls[2] != calls[0]

@pytest.mark.parametrize('call', [2, 3], ids=['original-handle-mutated', 'path-replaced-or-mutated'])
@pytest.mark.parametrize('field', ['st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns'])
def test_all_identity_and_change_fields_remain_checked(workbook, monkeypatch, call, field):
    original = import_candidate.os.fstat
    calls = []
    def changed(fd):
        result = original(fd)
        calls.append(fd)
        if len(calls) == call:
            return metadata(result, **{field: getattr(result, field) + 1})
        return result
    monkeypatch.setattr(import_candidate.os, 'fstat', changed)
    with pytest.raises(ExcelImportError, match='cambió mientras'):
        import_candidate.read_candidate(str(workbook), lambda: False)

@pytest.mark.parametrize('error', [PermissionError, FileNotFoundError])
def test_reopened_path_failure_preserves_friendly_error_and_closes_handle(workbook, monkeypatch, error):
    original = builtins.open
    handles = []
    def open_path(path, *args, **kwargs):
        if str(path) == str(workbook):
            if handles:
                raise error('synthetic reopen error')
            handle = original(path, *args, **kwargs)
            handles.append(handle)
            return handle
        return original(path, *args, **kwargs)
    monkeypatch.setattr(import_candidate, 'open', open_path, raising=False)
    with pytest.raises(ExcelImportError):
        import_candidate.read_candidate(str(workbook), lambda: False)
    assert handles and handles[0].closed

def test_snapshot_cancellation_still_stops_before_reopening(workbook, monkeypatch):
    original = builtins.open
    handles = []
    def open_path(*args, **kwargs):
        handle = original(*args, **kwargs)
        handles.append(handle)
        return handle
    monkeypatch.setattr(import_candidate, 'open', open_path, raising=False)
    calls = []
    def cancelled():
        calls.append(True)
        return len(calls) == 3
    with pytest.raises(ImportCancelled):
        import_candidate.read_candidate(str(workbook), cancelled)
    assert len(handles) == 1 and handles[0].closed
