from collections import defaultdict
from pathlib import Path

import pandas as pd

from src.application.scheduling_service import SchedulingService
from src.infrastructure.excel_reader import ExcelReader
from src.scheduling.time_model import TimeModel


def assert_valid_assignments(assignments, groups, classrooms):
    """Every assigned group has a valid, non-overlapping classroom interval."""
    group_by_id = {group.group_id: group for group in groups}
    assert len(group_by_id) == len(groups)
    assert set(assignments) <= set(group_by_id)
    time_model = TimeModel.default()
    room_slots = defaultdict(list)
    for group_id, (room_name, day, start, end) in assignments.items():
        group = group_by_id[group_id]
        assert room_name in classrooms
        assert classrooms[room_name].capacity >= group.size
        assert time_model.is_valid_interval(day, start, end)
        assert not time_model.overlaps_lunch(start, end)
        assert end - start == group.duration_min
        room_slots[(room_name, day)].append((start, end))
    for slots in room_slots.values():
        slots.sort()
        assert all(previous[1] <= following[0] for previous, following in zip(slots, slots[1:]))


def test_shipped_demo_workbook_produces_valid_schedule():
    base_dir = Path(__file__).resolve().parents[1]
    excel_path = base_dir / "data" / "input" / "Cursos_Ejemplo.xlsx"
    reader = ExcelReader(str(excel_path))
    classrooms = reader.load_classrooms()
    courses = reader.load_courses()
    assignments, groups = SchedulingService(str(excel_path), seed=42).run()
    assert classrooms
    assert courses
    assert len(assignments) == len(groups) == 42
    assert len(groups) == sum(len(course.generate_groups()) for course in courses)
    # Every synthetic demo session must be scheduled and satisfy hard constraints.
    assert_valid_assignments(assignments, groups, classrooms)


def test_self_contained_workbook_schedules_every_group(tmp_path):
    excel_path = tmp_path / "courses.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        # Reverse sheet order to verify names define the input contract.
        pd.DataFrame({
            "Curso": ["BIO101", "BIO101", "BIO101L"],
            "Nombre de Curso": ["Biología", "Biología", "Laboratorio"],
            "Horas": ["0800-1000", "0800-1000", "1400-1600"],
            "Aula": ["601", "601", "LBIO"], "Días": ["L", "I", "M"],
        }).to_excel(writer, sheet_name="Cursos", index=False)
        pd.DataFrame({
            "# DE AULA": ["601", "LBIO"], "CAPACIDAD": [60, 25],
        }).to_excel(writer, sheet_name="Aulas", index=False)
    assignments, groups = SchedulingService(str(excel_path), seed=7).run()
    assert assignments is not None
    assert set(assignments) == {"BIO101-G1", "BIO101-G2", "BIO101L-G1"}
    assert_valid_assignments(assignments, groups, ExcelReader(str(excel_path)).load_classrooms())
