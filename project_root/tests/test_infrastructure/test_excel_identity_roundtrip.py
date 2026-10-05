"""Synthetic workbook identities, split groups and their durable references."""
from collections import Counter

from openpyxl import Workbook

from src.infrastructure.excel_reader import ExcelReader
from src.infrastructure.session_repository import SessionRepository
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from src.scheduling.validation import validate_schedule
from src.scheduling.time_model import TimeModel


def test_excel_identifiers_and_split_relationships_survive_reopen(tmp_path):
    path = tmp_path / 'roundtrip-corpus.xlsx'
    book = Workbook()
    rooms = book.active
    rooms.title = 'Aulas'
    rooms.append([' # DE AULA ', ' CAPACIDAD ', 'DESCRIPCIÓN', 'CAMPUS'])
    room_ids = ['R', 'r', 'LΩ', '楼A', 'é', 'e\u0301', '001', '601', 'nan', 'NaN']
    for room in room_ids:
        rooms.append([f'\u00a0{room}\u00a0', 30, f'Description {room}', 'SYNTHETIC'])
    sheet = book.create_sheet('Cursos')
    sheet.append([' CURSO ', 'Nombre de Curso', ' Horas sugeridas ', 'AULA SUGERIDA', ' DIÁS '])
    rows = [
        (' BIO ', 'R', '0800-1300', 'L'), ('BIO', 'r', '0900-1400', 'I'),
        ('bio', 'LΩ', '0800-0900', 'm'), ('BIÓ', '楼A', '0900-1000', 'J'),
        ('BIO\u0301', 'é', '0800-0900', 'V'), ('ＢＩＯ', 'e\u0301', '0800-0900', 'S'),
        ('001', '001', '0800-0900', 'L'), (601, 601, '0800-0900', 'I'),
        ('nan', 'nan', '0800-0900', 'M'), ('NaN', 'NaN', '0800-0900', 'J'),
    ]
    for code, room, hours, day in rows:
        sheet.append([code, f'Synthetic {code}', hours, room, day])
    book.save(path)

    imported = ExcelReader(str(path)).load_validated()
    assert not imported.warnings
    # Headers are normalized; identifiers retain exact case and Unicode after
    # exterior whitespace is removed. Duplicate course rows remain two groups.
    expected_codes = [str(code).strip() for code, *_ in rows]
    assert Counter({c.code: c.number_of_groups for c in imported.courses}) == Counter(expected_codes)
    assert set(imported.classrooms) == set(room_ids)
    expected_map = {str(room): [str(code).strip()] for code, room, *_ in rows}
    assert imported.classroom_course_map == expected_map
    groups = [group for course in imported.courses for group in course.generate_groups()]
    assert len(groups) == 14 and len({group.group_id for group in groups}) == 14
    for course in imported.courses:
        for index in range(1, course.number_of_groups + 1):
            group_id = f'{course.code}-G{index}'
            parts = [group for group in course.generate_groups()
                     if group.group_id == group_id or group.parent_group_id == group_id]
            assert sum(group.duration_min for group in parts) == course.duration_min
    bio = next(course for course in imported.courses if course.code == 'BIO')
    assert [group.duration_min for group in bio.generate_groups()] == [120, 120, 60, 120, 120, 60]
    assert [group.suggested_classroom for group in bio.generate_groups()] == ['R'] * 3 + ['r'] * 3

    assignments = {'BIO-G1-P1': ('R', 1, 480, 600), 'bio-G1': ('LΩ', 3, 480, 540)}
    pins = set(assignments)
    kinds = ('teacher', 'student_group', 'student')
    resources = SchedulingResources(tuple(
        ResourceCatalog(kind, True, (Resource(f'{kind}-local', f'Synthetic {kind}'),), (
            ('BIO-G1-P1', (f'{kind}-local',)), ('bio-G1', (f'{kind}-local',)),
        )) for kind in kinds))
    restrictions = {room: set(codes) for room, codes in imported.classroom_course_map.items()}
    for room in imported.classrooms.values():
        room.allowed_courses = restrictions.get(room.name)
    assert not validate_schedule(assignments, groups, imported.classrooms, TimeModel.default(), resources=resources)
    db = tmp_path / 'roundtrip-corpus.db'
    repository = SessionRepository(str(db))
    repository.save_session(str(path), 17, imported.classrooms, imported.courses, restrictions,
                            assignments, pinned_group_ids=pins, resources=resources)

    reopened = SessionRepository(str(db)).load_session()
    assert [vars(course) for course in reopened['courses']] == [vars(course) for course in imported.courses]
    assert reopened['pinned_group_ids'] == pins and reopened['assignments'] == assignments
    assert reopened['restrictions'] == restrictions
    for kind in kinds:
        assert reopened['resources'].catalog(kind) == resources.catalog(kind)
    assert [vars(group) for course in reopened['courses'] for group in course.generate_groups()] == [
        vars(group) for group in groups]
    repeat = ExcelReader(str(path)).load_validated()
    assert [vars(course) for course in repeat.courses] == [vars(course) for course in imported.courses]
