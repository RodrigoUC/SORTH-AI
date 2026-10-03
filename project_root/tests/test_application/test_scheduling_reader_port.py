"""Input adapters are replaceable without changing the scheduling use case."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src.application.scheduling_service import SchedulingService
from src.bootstrap.scheduling import create_excel_reader
from src.scheduling.cancellation import SchedulingCancelled
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course


class FakeReader:
    def __init__(self):
        self.courses = [Course('BIO', 1, 60, 'REGULAR', size=20)]
        self.classrooms = {'A1': Classroom('A1', 30, 'REGULAR')}
        self.classrooms['A1'].occupy(1, 420, 480)
        self.classrooms['A1'].set_allowed_courses({'OLD'})
        self.calls = []

    def load_validated(self):
        self.calls.append('validated')
        return SimpleNamespace(courses=self.courses, classrooms=self.classrooms)

    def load_classrooms(self):
        self.calls.append('classrooms')
        return self.classrooms

    def load_courses(self):
        self.calls.append('courses')
        return self.courses


@pytest.mark.parametrize('supplied,expected', [
    ({}, ['validated']),
    ({'courses': True}, ['classrooms']),
    ({'classrooms': True}, ['courses']),
    ({'courses': True, 'classrooms': True}, []),
])
def test_reader_loads_only_missing_data_and_preserves_inputs(supplied, expected):
    reader = FakeReader()
    factory_calls = []

    def factory(path):
        factory_calls.append(path)
        return reader

    kwargs = {name: getattr(reader, name) for name in supplied}
    original_course = deepcopy(vars(reader.courses[0]))
    assignments, groups = SchedulingService(
        'opaque-source', reader_factory=factory,
    ).run(**kwargs)

    assert len(assignments) == len(groups) == 1
    assert reader.calls == expected
    assert factory_calls == (['opaque-source'] if expected else [])
    assert reader.classrooms['A1'].occupancy == {1: [(420, 480)]}
    assert reader.classrooms['A1'].allowed_courses == {'OLD'}
    assert vars(reader.courses[0]) == original_course


def test_complete_data_never_uses_legacy_composition(monkeypatch):
    import src.bootstrap.scheduling as composition
    reader = FakeReader()

    def forbidden(path):
        raise AssertionError('Fully supplied generation must not access a reader')

    monkeypatch.setattr(composition, 'create_excel_reader', forbidden)
    assignments, _ = SchedulingService('unused.xlsx').run(
        courses=reader.courses, classrooms=reader.classrooms,
    )
    assert assignments


def test_injected_failure_does_not_change_supplied_classrooms():
    reader = FakeReader()
    original = deepcopy(vars(reader.classrooms['A1']))

    def fail():
        raise ValueError('Invalid input from adapter')

    reader.load_courses = fail
    with pytest.raises(ValueError, match='Invalid input from adapter'):
        SchedulingService(None, reader_factory=lambda path: reader).run(
            classrooms=reader.classrooms,
        )
    assert vars(reader.classrooms['A1']) == original


def test_cancel_before_loading_never_constructs_reader():
    def forbidden(path):
        raise AssertionError('Cancelled generation must not access a reader')

    with pytest.raises(SchedulingCancelled):
        SchedulingService(None, reader_factory=forbidden).run(cancelled=lambda: True)


def test_explicit_empty_data_does_not_trigger_file_fallback():
    def forbidden(path):
        raise AssertionError('Empty inputs are supplied inputs, not missing ones')

    assert SchedulingService(None, reader_factory=forbidden).run(
        courses=[], classrooms={},
    ) == ({}, [])


def test_legacy_path_api_uses_named_composition_bridge(monkeypatch):
    import src.bootstrap.scheduling as composition
    reader = FakeReader()
    paths = []

    def factory(path):
        paths.append(path)
        return reader

    monkeypatch.setattr(composition, 'create_excel_reader', factory)
    assignments, _ = SchedulingService('legacy.xlsx', 42).run()
    assert assignments
    assert paths == ['legacy.xlsx']
    assert reader.calls == ['validated']


def test_explicit_excel_composition_matches_legacy_result():
    path = str(Path(__file__).resolve().parents[2] / 'data/input/Cursos_Ejemplo.xlsx')
    legacy_assignments, legacy_groups = SchedulingService(path, 42).run()
    explicit_assignments, explicit_groups = SchedulingService(
        path, 42, reader_factory=create_excel_reader,
    ).run()
    assert legacy_assignments == explicit_assignments
    def signature(group):
        return dict(vars(group), domain=[(room.name, day, start)
                                        for room, day, start in group.domain])
    assert list(map(signature, legacy_groups)) == list(map(signature, explicit_groups))


def test_injected_reader_and_composition_import_run_without_site_packages(tmp_path):
    root = str(Path(__file__).resolve().parents[2])
    script = f'''
import sys
from types import SimpleNamespace
sys.path.insert(0, {root!r})
from src.application.scheduling_service import SchedulingService
from src.bootstrap.scheduling import create_excel_reader
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
class Reader:
    def load_validated(self):
        return SimpleNamespace(
            courses=[Course('BIO', 1, 60, 'REGULAR', size=20)],
            classrooms={{'A1': Classroom('A1', 30, 'REGULAR')}},
        )
result, groups = SchedulingService(None, reader_factory=lambda path: Reader()).run()
assert len(result) == len(groups) == 1
assert not any(name.startswith(('PyQt', 'mcp', 'pandas', 'openpyxl', 'sqlite3',
                                'src.infrastructure')) for name in sys.modules)
'''
    result = subprocess.run(
        [sys.executable, '-B', '-S', '-c', script], cwd=tmp_path,
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []
