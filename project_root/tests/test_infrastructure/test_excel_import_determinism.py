"""A workbook must materialize identically before the scheduler seed is used."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


@pytest.mark.parametrize('hash_seed', ['1', '2', '3', '4'])
def test_tied_defaults_follow_first_row_in_fresh_processes(tmp_path, hash_seed):
    path = tmp_path / 'tied.xlsx'
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'# DE AULA': ['LAB', 'R'], 'CAPACIDAD': [30, 30]}).to_excel(
            writer, sheet_name='Aulas', index=False)
        pd.DataFrame({
            'Curso': ['BIO', 'BIO', 'BIO'], 'Aula': ['LAB', 'R', ''],
            'Días': ['L', 'I', ''], 'Horas': ['1000-1300', '0800-0900', ''],
        }).to_excel(writer, sheet_name='Cursos', index=False)
    script = '''
import json, sys
from src.infrastructure.excel_reader import ExcelReader
course, = ExcelReader(sys.argv[1]).load_validated().courses
group = course.generate_groups()[-1]
print(json.dumps({
    'course': [course.suggested_classroom, course.required_room_type,
               course.preferred_day, course.duration_min, course.preferred_start_min],
    'fallback_group': [group.suggested_classroom, group.required_room_type,
                       group.preferred_day, group.duration_min, group.preferred_start_min],
}))
'''
    result = subprocess.run(
        [sys.executable, '-c', script, str(path)],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, 'PYTHONHASHSEED': hash_seed},
        capture_output=True, text=True, timeout=30, check=True)
    expected = ['LAB', 'LAB', 'Lunes', 180, 600]
    assert json.loads(result.stdout) == {'course': expected, 'fallback_group': expected}
