"""Compatibility entrypoints continue to work after organizing developer tools."""
import json
from pathlib import Path
import subprocess
import sys

import benchmark
from tools import benchmark_scheduler

ROOT = Path(__file__).resolve().parents[2]


def test_benchmark_imports_forward_to_one_implementation():
    for name in benchmark.__all__:
        assert getattr(benchmark, name) is getattr(benchmark_scheduler, name)
    assert benchmark.DEFAULT_INPUT == ROOT / "data/input/Cursos_Ejemplo.xlsx"


def test_benchmark_old_and_new_commands_work_outside_project(tmp_path):
    reports = []
    for script in (ROOT / "benchmark.py", ROOT / "tools/benchmark_scheduler.py"):
        result = subprocess.run(
            [sys.executable, str(script), "--repeats", "1", "--json"],
            cwd=tmp_path, capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["hard_constraints_verified"] and report["deterministic"]
        assert report["assigned"] == report["groups"] > 0
        reports.append(report)
    for name in ("input", "seed", "classrooms", "courses", "groups", "assigned", "quality"):
        assert reports[0][name] == reports[1][name]


def test_icon_entrypoint_forwards_without_writing_resources():
    import convert_png_to_ico as compatibility
    from tools import convert_png_to_ico as implementation
    assert compatibility.convert_png_to_ico is implementation.convert_png_to_ico
    assert compatibility.main is implementation.main
    assert implementation.ROOT == ROOT
