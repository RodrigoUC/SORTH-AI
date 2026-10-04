"""Synthetic deterministic scheduler measurements; no source mutation or user data."""
import argparse
import cProfile
import hashlib
import gc
import io
import json
import platform
import pstats
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2],
                        help='Trusted source checkout to benchmark (default: this checkout)')
    parser.add_argument('--out', type=Path, default=Path('build/reports/scheduler-matrix.json'))
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--cases', nargs='*', choices=('small', 'medium', 'large',
        'course_constraints', 'resources', 'pins_calendar', 'split_groups', 'saturated'))
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--memory', action='store_true')
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error('--repeats must be at least 1')
    return args


# Direct execution can compare a trusted baseline checkout without copying code.
# Imports use this checkout when the fixture module is imported by tests.
args = parse_args() if __name__ == '__main__' else parse_args([])
sys.path.insert(0, str(Path(args.root) / 'project_root'))
from src.scheduling.classroom import Classroom
from src.scheduling.course import Course
from src.scheduling.schedule_state import ScheduleState
from src.scheduling.scheduler import Scheduler
from src.scheduling.time_model import TimeModel
from src.scheduling.project_calendar import ProjectCalendar
from src.scheduling.teaching_resources import Resource, ResourceCatalog, SchedulingResources
from src.scheduling.validation import validate_schedule
from src.scheduling.quality import QualitySnapshot, analyze_quality
from tools.benchmark_scheduler import validate_schedule as validate_state


def fixture(name):
    sizes = {'small': (12, 2, 4), 'medium': (60, 2, 12), 'large': (180, 2, 24),
             'course_constraints': (60, 2, 12), 'resources': (60, 2, 12),
             'pins_calendar': (40, 2, 10), 'split_groups': (40, 1, 12),
             'saturated': (90, 2, 2)}
    count, groups_per_course, room_count = sizes[name]
    rooms = [Classroom(f'R{i:02}', 45 + (i % 3) * 15,
                       'LAB' if i % 4 == 0 else 'REGULAR') for i in range(room_count)]
    courses = [Course(f'C{i:03}', groups_per_course,
                      360 if name == 'split_groups' else (60, 90, 120)[i % 3],
                      'LAB' if i % 5 == 0 else 'REGULAR', size=20 + (i % 3) * 10,
                      suggested_classroom=(f'R{i % room_count:02}' if name == 'course_constraints' and i % 4 == 1 else None),
                      preferred_start_min=(480 + (i % 6) * 60 if i % 9 == 1 else None),
                      preferred_day=('Lunes' if i % 13 == 3 else None)) for i in range(count)]
    tm = TimeModel.default()
    if name == 'pins_calendar':
        tm = TimeModel.from_calendar(ProjectCalendar(('Lunes','Martes','Miércoles','Jueves','Viernes'),
            457, 1177, ((697, 752), (952, 967))))
        courses[0] = Course('C000', 1, 360, 'LAB', size=20)
        courses[1] = Course('C001', 2, 60, 'REGULAR', size=20)
    if name == 'course_constraints':
        for room in rooms[:4]:
            room.set_allowed_courses({course.code for i, course in enumerate(courses) if i % 4 == 1})
    groups = [group for course in courses for group in course.generate_groups()]
    resources = None
    if name == 'resources':
        catalogs = []
        for kind, n, membership_count in [('teacher', 30, 1), ('student_group', 24, 1), ('student', 80, 3)]:
            entries = tuple(Resource(f'{kind}{i}', f'{kind} {i}',
                          tuple((d, 420, 720) for d in range(1, 7)) + tuple((d, 780, 1200) for d in range(1, 7))
                          if i % 4 == 0 else None) for i in range(n))
            memberships = tuple((g.group_id, tuple(f'{kind}{(i * membership_count + j) % n}'
                                for j in range(membership_count))) for i,g in enumerate(groups))
            catalogs.append(ResourceCatalog(kind, True, entries, memberships))
        resources = SchedulingResources(tuple(catalogs))
    state = ScheduleState(tm, rooms, resources)
    pins = {}
    if name == 'pins_calendar':
        by_id = {g.group_id:g for g in groups}
        for gid, room, day, start in [('C000-G1-P1', 'R00', 2, 467), ('C001-G1', 'R01', 1, 467)]:
            group = by_id[gid]
            if not state.assign(group, room, day, start): raise AssertionError('Invalid benchmark pin')
            group.pinned = True
            pins[gid] = group.assignment
    return state, groups, pins


def check(state, groups, pins):
    # Independent final validator plus occupancy/family and exact pin checks.
    validate_state(state, groups)
    errors = validate_schedule(state.assignments, groups, state.classrooms, state.time_model,
                               {g.group_id for g in groups if g.lab_override}, state.resources)
    if errors: raise AssertionError(str(errors))
    if any(state.assignments.get(gid) != p for gid,p in pins.items()): raise AssertionError('Moved pin')
    if state.resources:
        # Also call the baseline unindexed admission rule over a clean prefix;
        # this remains a correctness oracle if an indexed admission is proposed.
        seen = {}
        for gid, placement in state.assignments.items():
            _, day, start, end = placement
            errors = state.resources.placement_issues(gid, day, start, end, seen)
            if errors: raise AssertionError(str(errors))
            seen[gid] = placement
    return hashlib.sha256(json.dumps(state.assignments, sort_keys=True).encode()).hexdigest()


def run(name, profile=False, memory=False, scheduler_type=Scheduler):
    setup = time.perf_counter(); state, groups, pins = fixture(name); setup = time.perf_counter()-setup
    scheduler = scheduler_type(seed=42)
    # Start each sample at the same collection boundary, outside the timer.
    gc.collect()
    profiler = cProfile.Profile() if profile else None
    if memory: tracemalloc.start()
    if profiler: profiler.enable()
    started = time.perf_counter(); complete = scheduler.schedule(state, groups); elapsed = time.perf_counter()-started
    if profiler: profiler.disable()
    peak = tracemalloc.get_traced_memory()[1] if memory else None
    if memory: tracemalloc.stop()
    checked = time.perf_counter(); digest = check(state,groups,pins); validation = time.perf_counter()-checked
    if complete != all(g.is_assigned() for g in groups): raise AssertionError('Success disagrees with assignments')
    if profiler:
        stream=io.StringIO(); pstats.Stats(profiler,stream=stream).sort_stats('cumulative').print_stats(35)
        Path(args.out).with_name(f'{Path(args.out).stem}-{name}-profile.txt').write_text(stream.getvalue())
        profiler.dump_stats(str(Path(args.out).with_name(f'{Path(args.out).stem}-{name}.prof')))
    return dict(case=name, groups=len(groups), rooms=len(state.classrooms), assigned=len(state.assignments),
                complete=complete, schedule_seconds=elapsed, setup_seconds=setup,
                validation_seconds=validation, assignment_sha256=digest,
                assignment_order_sha256=hashlib.sha256(json.dumps(list(state.assignments.items())).encode()).hexdigest(),
                peak_traced_bytes=peak,
                domain_entries=sum(len(g.domain) for g in groups), pins=len(pins),
                hard_constraints_verified=True, quality=analyze_quality(QualitySnapshot.capture(
                    state.assignments,groups,state.time_model,state.classrooms)))


if __name__ == "__main__":
    args.out.parent.mkdir(parents=True, exist_ok=True)
    cases = args.cases or ['small','medium','large','course_constraints','resources','pins_calendar','split_groups','saturated']
    report = dict(python=sys.version, platform=platform.platform(), source_root=str(args.root.resolve()), seed=42,
                  note='Only Scheduler.schedule timed; GUI responsiveness is not measured.', results=[])
    for name in cases:
        samples = [run(name) for _ in range(args.repeats)]
        if len({s['assignment_sha256'] for s in samples}) != 1: raise AssertionError(f'Nondeterministic {name}')
        result = dict(samples[-1], samples_seconds=[s['schedule_seconds'] for s in samples],
                      median_seconds=statistics.median(s['schedule_seconds'] for s in samples), deterministic=True)
        if args.profile: run(name, profile=True)
        if args.memory: result['peak_traced_bytes']=run(name,memory=True)['peak_traced_bytes']
        report['results'].append(result)
        Path(args.out).write_text(json.dumps(report, indent=2))
        print(json.dumps({k:result[k] for k in ['case','groups','rooms','assigned','median_seconds','assignment_sha256','domain_entries','peak_traced_bytes']}), flush=True)
