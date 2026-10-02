"""Deterministic scheduler benchmark using the shipped Excel data.

Run from any directory:
    python project_root/benchmark.py --repeats 5
    python project_root/benchmark.py --input courses.xlsx --json

Input loading, group creation, and invariant checks are outside the timed region.
The result measures scheduler time, not full GUI or import/export performance.
"""

import argparse
import copy
import json
from pathlib import Path
import statistics
import time

from src.infrastructure.excel_reader import ExcelReader
from src.scheduling.schedule_state import ScheduleState
from src.scheduling.scheduler import Scheduler
from src.scheduling.time_model import TimeModel


DEFAULT_INPUT = Path(__file__).resolve().parent / "data" / "input" / "Cursos_Ejemplo.xlsx"


def validate_schedule(state, groups):
    """Fail loudly if a benchmark run violates any scheduling hard constraint."""
    assert len(state.assignments) == sum(group.is_assigned() for group in groups)
    families = {}
    for group in groups:
        if not group.is_assigned():
            assert group.group_id not in state.assignments
            continue
        room_name, day, start, end = group.assignment
        room = state.classrooms[room_name]
        assert state.assignments[group.group_id] == group.assignment
        assert room.capacity >= group.size
        assert group.required_room_type != "LAB" or room.room_type == "LAB" or group.lab_override
        assert room.allows_course(group.course_code)
        assert state.time_model.is_valid_interval(day, start, end)
        assert not state.time_model.overlaps_lunch(start, end)
        assert end - start == group.duration_min
        assert (start, end) in room.occupancy[day]
        if group.parent_group_id:
            families.setdefault(group.parent_group_id, []).append(group.assignment)
    for room in state.classrooms.values():
        for intervals in room.occupancy.values():
            ordered = sorted(intervals)
            assert all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:]))
    for slots in families.values():
        assert len({slot[1] for slot in slots}) == len(slots)
        assert len({slot[2] for slot in slots}) == 1


def run_once(classrooms, courses, seed=42, *, scheduler_type=Scheduler,
             state_type=ScheduleState, time_model_type=TimeModel):
    """Use clean objects for each run and return timing plus the validated result."""
    rooms = copy.deepcopy(list(classrooms.values()))
    groups = [group for course in courses for group in course.generate_groups()]
    state = state_type(time_model_type.default(), rooms)
    scheduler = scheduler_type(seed=seed)
    started = time.perf_counter()
    success = scheduler.schedule(state, groups)
    elapsed = time.perf_counter() - started
    validate_schedule(state, groups)
    assert success == all(group.is_assigned() for group in groups)
    return elapsed, state, groups


def benchmark_excel(input_path=DEFAULT_INPUT, repeats=5, seed=42):
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    started = time.perf_counter()
    reader = ExcelReader(str(input_path))
    classrooms = reader.load_classrooms()
    courses = reader.load_courses(known_classrooms=set(classrooms))
    load_seconds = time.perf_counter() - started
    samples = []
    first_assignments = None
    deterministic = True
    for _ in range(repeats):
        elapsed, state, groups = run_once(classrooms, courses, seed)
        samples.append(elapsed)
        if first_assignments is None:
            first_assignments = dict(state.assignments)
        else:
            deterministic = deterministic and state.assignments == first_assignments
    return {
        "input": str(Path(input_path).resolve()),
        "seed": seed,
        "repeats": repeats,
        "classrooms": len(classrooms),
        "courses": len(courses),
        "groups": len(groups),
        "assigned": len(state.assignments),
        "unassigned": len(groups) - len(state.assignments),
        "median_seconds": statistics.median(samples),
        "min_seconds": min(samples),
        "max_seconds": max(samples),
        "samples_seconds": samples,
        "input_load_seconds": load_seconds,
        "deterministic": deterministic,
        "hard_constraints_verified": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Excel input path")
    parser.add_argument("--repeats", type=int, default=5, help="Number of timed runs (default: 5)")
    parser.add_argument("--seed", type=int, default=42, help="Scheduler seed (default: 42)")
    parser.add_argument("--json", action="store_true", help="Print machine-readable results")
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    if not args.input.is_file():
        parser.error(f"Input file not found: {args.input}")
    result = benchmark_excel(args.input, args.repeats, args.seed)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Input: {result['input']}")
        print(f"Courses: {result['courses']} | Classrooms: {result['classrooms']}")
        print(f"Assigned: {result['assigned']}/{result['groups']} | Unassigned: {result['unassigned']}")
        print(f"Scheduler median: {result['median_seconds']:.4f} s "
              f"(min {result['min_seconds']:.4f}, max {result['max_seconds']:.4f}, "
              f"{args.repeats} runs)")
        print(f"Input load: {result['input_load_seconds']:.4f} s (excluded from scheduler timing)")
        print(f"Deterministic: {result['deterministic']} | Hard constraints verified: True")


if __name__ == "__main__":
    main()
