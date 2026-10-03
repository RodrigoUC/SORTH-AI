"""Independent minute-set oracle for indexed room/day occupancy."""
import random
import pytest
from src.scheduling.classroom import Classroom
from src.scheduling.group import Group
from src.scheduling.quality import QualitySnapshot, analyze_quality
from src.scheduling.time_model import TimeModel


@pytest.mark.parametrize('seed', range(20))
def test_room_day_buckets_match_independent_minute_occupancy(seed):
    rng = random.Random(seed)
    tm = TimeModel(['Lunes', 'Martes'], 420, 900, breaks=((600, 630), (720, 780)))
    rooms = {name: Classroom(name, 30, 'REGULAR') for name in ('A', 'B', 'C')}
    exclusions = {('A', 1): [(450, 500), (490, 530)], ('B', 2): [(800, 1000)]}
    assignments = {}
    groups = []
    for i in range(80):
        gid = f'G{i}'
        start = rng.randrange(390, 940)
        # Include reversed/empty intervals, unknown rooms and unknown days.
        end = start + rng.randrange(-20, 150)
        assignments[gid] = (rng.choice(['A', 'B', 'C', 'missing']), rng.randrange(1, 4), start, end)
        groups.append(Group(gid, max(1, end - start), 'REGULAR'))
    snapshot = QualitySnapshot.capture(assignments, groups, tm, rooms, room_exclusions=exclusions)
    result = analyze_quality(snapshot)
    for room in result['occupancy']['rooms']:
        for daily in room['days']:
            name, day = room['room'], daily['day']
            available = set(range(tm.day_start, tm.day_end))
            for start, end in list(tm.breaks) + exclusions.get((name, day), []):
                available.difference_update(range(start, end))
            occupied = set()
            for assigned_room, assigned_day, start, end in assignments.values():
                if assigned_room == name and assigned_day == day:
                    occupied.update(range(start, end))
            assert daily['occupied_minutes'] == len(occupied & available)
            assert daily['available_minutes'] == len(available)
    # Buckets must not survive a later analysis with a different assignment set.
    empty = analyze_quality(QualitySnapshot.capture({}, groups, tm, rooms, room_exclusions=exclusions))
    assert empty['occupancy']['occupied_minutes'] == 0
    assert analyze_quality(snapshot) == result
