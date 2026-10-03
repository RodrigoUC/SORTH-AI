"""Bounded synthetic editor benchmark; reports timings, never asserts time limits.

Use the identical script on a baseline and candidate checkout. The unoptimized
visible course table can be very slow, so UI sizes above 100 require an explicit
--ui-max-size. Core operations have no database or file persistence side effects.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application.edit_history import EditHistory, fingerprint
from src.application.scenario_comparison import ALGORITHM_VERSION, compare_scenarios, scenario_metadata
from src.application.scheduling_service import SchedulingService
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.project_calendar import ProjectCalendar
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from src.scheduling.time_model import TimeModel


def fixture(size):
    time_model = TimeModel.default()
    rooms = {f'R{i}': Classroom(f'R{i}', 40, 'REGULAR') for i in range(math.ceil(size / 60))}
    courses = [Course(f'C{i:05}', 1, 60, 'REGULAR', 20, name=f'Course {i}',
                      suggested_classroom=f'R{i // 60}',
                      preferred_day=time_model.index_to_day[1 + i % 6],
                      preferred_start_min=420 + 60 * (i % 60 // 6) + (60 if i % 60 // 6 >= 5 else 0))
               for i in range(size)]
    groups = [group for course in courses for group in course.generate_groups()]
    assignments = {group.group_id: (course.suggested_classroom, 1 + i % 6,
                                    course.preferred_start_min, course.preferred_start_min + 60)
                   for i, (group, course) in enumerate(zip(groups, courses))}
    resources = SchedulingResources((ResourceCatalog('teacher', True,
        tuple(Resource(f'T{i}', f'Teacher {i}') for i in range(size)),
        tuple((group.group_id, (f'T{i}',)) for i, group in enumerate(groups))),))
    state = dict(courses=courses, classrooms=rooms, assignments=assignments, restrictions={},
                 resources=SchedulingResources(), calendar=ProjectCalendar(), seed=42, excel_path=None,
                 lab_overrides=set(), pinned_group_ids=set(), schedule_present=True,
                 group_feedback={}, classroom_course_map={})
    return state, groups, resources


def measure(operation, repeats):
    operation()  # warm-up, excluded from timing
    wall, cpu = [], []
    for _ in range(repeats):
        wall_start, cpu_start = time.perf_counter(), time.process_time()
        operation()
        wall.append((time.perf_counter() - wall_start) * 1000)
        cpu.append((time.process_time() - cpu_start) * 1000)
    return dict(wall_ms=wall, cpu_ms=cpu, median_wall_ms=statistics.median(wall),
                median_cpu_ms=statistics.median(cpu))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', nargs='+', type=int, default=[100, 1000, 5000])
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--ui-max-size', type=int, default=100)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if any(size < 1 or size > 5000 for size in args.sizes) or not 1 <= args.repeats <= 20:
        parser.error('Use sizes 1..5000 and repeats 1..20 for a bounded run')
    from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
    from PyQt6.QtWidgets import QApplication
    from src.gui.course_manager_widget import CourseManagerWidget
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    report = dict(environment=dict(python=platform.python_version(), platform=platform.platform(),
        qt=QT_VERSION_STR, pyqt=PYQT_VERSION_STR, qpa=os.environ['QT_QPA_PLATFORM'],
        style=app.style().objectName()), repeats=args.repeats, results=[])
    for size in args.sizes:
        state, groups, resources = fixture(size)
        after = deepcopy(state)
        after['courses'][0].name = 'Edited course'
        metadata = scenario_metadata(ALGORITHM_VERSION)
        comparison = lambda: compare_scenarios((state, metadata), (after, metadata))
        generation = lambda: SchedulingService(None, 42).run(courses=state['courses'], classrooms=state['classrooms'])
        resource_validation = lambda: resources.validate(state['assignments'], groups, TimeModel.default())
        execute = lambda: EditHistory().execute(state, after, lambda _: None, 'edit')
        result = dict(size=size, rooms=len(state['classrooms']), measurements={})
        for name, operation in (
            ('resource_validation', resource_validation), ('snapshot', lambda: deepcopy(state)),
            ('fingerprint', lambda: fingerprint(state)), ('history_execute', execute),
            ('history_noop', lambda: EditHistory().execute(state, state, lambda _: None, 'noop')),
            ('scenario_compare', comparison), ('generation_preferences', generation),
        ):
            result['measurements'][name] = measure(operation, args.repeats)
        generated, _ = generation()
        result['correctness'] = dict(resource_notices=[str(i) for i in resource_validation()],
            accepted_fingerprint=fingerprint(execute()), comparison_digest=digest(comparison()),
            generated_count=len(generated), generated_digest=digest(generated))
        if size <= args.ui_max_size:
            widget = CourseManagerWidget()
            widget.courses = state['courses']
            widget.resize(1000, 700)
            widget.show()
            app.processEvents()
            result['measurements']['course_table_refresh'] = measure(
                lambda: (widget._refresh_table(), app.processEvents()), args.repeats)
            result['correctness']['table_codes'] = sorted(widget.table.item(row, 0).text()
                for row in range(widget.table.rowCount()))
            widget.close()
            widget.deleteLater()
            app.processEvents()
        report['results'].append(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(dict(size=size, medians={name: value['median_wall_ms']
            for name, value in result['measurements'].items()})), flush=True)


if __name__ == '__main__':
    main()
