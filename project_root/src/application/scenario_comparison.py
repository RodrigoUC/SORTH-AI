"""Descriptive, unweighted comparison using the shared quality contract v1."""
import json
import hashlib
from ..scheduling.quality import QualitySnapshot, analyze_quality
from ..scheduling.time_model import TimeModel
from ..scheduling.project_calendar import ProjectCalendar
from ..scheduling.teaching_resources import SchedulingResources

ALGORITHM_VERSION = 'sorth-scheduler-v2'


def scenario_metadata(algorithm_version=None, calendar=None):
    time = TimeModel.from_calendar(calendar or ProjectCalendar())
    return dict(format_version=1, algorithm_version=algorithm_version,
                metrics_version=1, calendar=(dict(days=time.index_to_day,
                start=time.day_start, end=time.day_end, lunch=[time.LUNCH_START, time.LUNCH_END])
                if time.calendar == ProjectCalendar() else time.calendar.to_dict()))


def analyze_scenario(data):
    groups = [g for course in data['courses'] for g in course.generate_groups()]
    for group in groups:
        group.lab_override = group.group_id in data.get('lab_overrides', ())
    return analyze_quality(QualitySnapshot.capture(data['assignments'] or {}, groups,
                                                   TimeModel.from_calendar(data.get('calendar', ProjectCalendar())), data['classrooms']))


def _inputs(data):
    # Compare all persisted source values, including names, preferences and sizes.
    courses = sorted((vars(c) for c in data['courses']), key=lambda c: c['code'])
    rooms = sorted((dict(name=c.name, capacity=c.capacity, room_type=c.room_type,
                         description=c.description, campus=c.campus) for c in data['classrooms'].values()),
                   key=lambda c: c['name'])
    return courses, rooms


def compare_scenarios(left, right):
    a, am = left
    b, bm = right
    differences = []
    difference_values = {}
    ac, ar = _inputs(a)
    bc, br = _inputs(b)
    for key, x, y in (
        ('courses', ac, bc), ('classrooms', ar, br),
        ('restrictions', a['restrictions'], b['restrictions']),
        ('resources', a.get('resources', SchedulingResources()).to_data(), b.get('resources', SchedulingResources()).to_data()),
        ('pins', a.get('pinned_group_ids', set()), b.get('pinned_group_ids', set())),
        ('seed', a['seed'], b['seed']),
        ('calendar', am.get('calendar'), bm.get('calendar')),
        ('algorithm_version', am.get('algorithm_version'), bm.get('algorithm_version')),
        ('metrics_version', am.get('metrics_version'), bm.get('metrics_version')),
        ('format_version', am.get('format_version'), bm.get('format_version')),
    ):
        if x != y:
            differences.append(key)
            difference_values[key] = (x, y)
    unknown = not am.get('algorithm_version') or not bm.get('algorithm_version')
    supported = True
    for data, metadata in ((a, am), (b, bm)):
        try:
            validate_scenario_metadata(metadata, data.get('calendar', ProjectCalendar()))
        except ValueError:
            supported = False
    supported = supported and all(
        type(m.get('format_version')) is int and m.get('format_version') == 1
        and type(m.get('metrics_version')) is int and m.get('metrics_version') == 1 for m in (am, bm))
    return dict(left=analyze_scenario(a) if supported else None,
                right=analyze_scenario(b) if supported else None,
                differences=differences, difference_values=difference_values, unknown_algorithm=unknown,
                comparable=not differences and not unknown and supported,
                supported_calendar=supported)


def session_fingerprint(data):
    courses, rooms = _inputs(data)
    values = dict(courses=courses, rooms=rooms, restrictions=data['restrictions'],
                  seed=data['seed'], excel_path=data['excel_path'],
                  assignments=data['assignments'] or {}, lab_overrides=data.get('lab_overrides', ()),
                  pins=data.get('pinned_group_ids', ()),
                  calendar=data.get('calendar', ProjectCalendar()).to_dict(),
                  resources=data.get('resources', SchedulingResources()).to_data())
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False,
                                    default=lambda value: sorted(value)).encode()).hexdigest()


def validate_scenario_metadata(metadata, calendar=None):
    if not isinstance(metadata, dict):
        raise ValueError('Invalid scenario metadata')
    if (type(metadata.get('format_version')) is not int or metadata.get('format_version') != 1
            or type(metadata.get('metrics_version')) is not int or metadata.get('metrics_version') != 1):
        raise ValueError('Unsupported scenario format or metrics version')
    if metadata.get('algorithm_version') is not None and not isinstance(metadata['algorithm_version'], str):
        raise ValueError('Invalid algorithm version')
    value = metadata.get('calendar')
    legacy = scenario_metadata()['calendar']
    if json.dumps(value, sort_keys=True) == json.dumps(legacy, sort_keys=True):
        parsed = ProjectCalendar()
    else:
        parsed = ProjectCalendar.from_dict(value)
    if calendar is not None and parsed != calendar:
        raise ValueError('Scenario calendar does not match persisted project rules; original preserved')
