"""Developer commands have one canonical implementation and work outside the repo."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_canonical_benchmark_command_works_outside_project(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / 'tools/benchmark_scheduler.py'), '--repeats', '1', '--json'],
        cwd=tmp_path, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['hard_constraints_verified'] and report['deterministic']
    assert report['assigned'] == report['groups'] == 42


def test_retired_entrypoints_and_duplicate_inputs_are_absent():
    for relative in ('benchmark.py', 'convert_png_to_ico.py', 'generate_courses_json.py',
                     'requeriments.txt', 'MANUAL_USUARIO.md', 'WINDOWS_DISTRIBUTION.md',
                     'src/ui/app.py', 'src/infrastructure/course_config_reader.py',
                     'src/scheduling/assignment.py', 'data/input/courses_config.json', 'schedule-board.png',
                     'SORTH.spec', 'src/infrastructure/excel_writer.py',
                     'tools/convert_png_to_ico.py', 'tools/verify_cross_version_recovery.py'):
        assert not (ROOT / relative).exists(), relative
