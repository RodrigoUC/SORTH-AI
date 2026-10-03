"""Read-only, unweighted schedule indicators. See QUALITY_METRICS.md.

Capture on the owning thread after generation/restoration/editing. Analysis uses
only immutable value objects, never Group.assignment or Classroom.occupancy.
This is descriptive analysis, not a hard-constraint validator or optimizer.
"""
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class SessionSnapshot:
    group_id: str
    original_group_id: str
    total_parts: int
    preferred_day: str | None
    preferred_start_min: int | None
    suggested_classroom: str | None
    required_room_type: str
    lab_override: bool


@dataclass(frozen=True)
class QualitySnapshot:
    sessions: tuple[SessionSnapshot, ...]
    assignments: tuple[tuple[str, str, int, int, int], ...]
    days: tuple[tuple[int, str], ...]
    day_start: int
    day_end: int
    rooms: tuple[tuple[str, str], ...] | None
    # room=None means the exclusion applies to every room on this day.
    exclusions: tuple[tuple[str | None, int, int, int], ...]

    @classmethod
    def capture(cls, assignments, groups, time_model, classrooms=None,
                *, room_exclusions: Mapping | None = None):
        """Copy authoritative assignments and metadata into a detached snapshot.

        room_exclusions maps (room_name, day_index) to half-open minute intervals.
        It is additional to the TimeModel lunch exclusion. No exclusions are
        inferred from room occupancy or course eligibility restrictions.
        None classrooms means unknown inventory; {} means a known empty one.
        """
        sessions = tuple(sorted((SessionSnapshot(
            g.group_id, g.parent_group_id or g.group_id, g.total_subgroups,
            g.preferred_day, g.preferred_start_min, g.suggested_classroom,
            g.required_room_type, bool(g.lab_override),
        ) for g in groups), key=lambda g: g.group_id))
        if len({g.group_id for g in sessions}) != len(sessions):
            raise ValueError("Duplicate session IDs cannot be analyzed")
        days = tuple(sorted(time_model.index_to_day.items()))
        exclusions = [(None, day, start, end)
                      for day, _ in days for start, end in time_model.breaks]
        for (room, day), intervals in (room_exclusions or {}).items():
            if classrooms is None or room not in classrooms or day not in dict(days):
                raise ValueError("Room exclusion references unknown room or day")
            for start, end in intervals:
                if type(start) is not int or type(end) is not int or start >= end:
                    raise ValueError("Room exclusions require increasing integer minutes")
                exclusions.append((room, day, start, end))
        slots = tuple((gid, *tuple(slot)) for gid, slot in sorted(assignments.items()))
        for slot in slots:
            if (len(slot) != 5 or not isinstance(slot[1], str)
                    or any(type(value) is not int for value in slot[2:])):
                raise ValueError("Assignments require room, day and integer start/end minutes")
        return cls(sessions, slots, days, time_model.day_start, time_model.day_end,
                   None if classrooms is None else tuple(sorted(
                       (name, room.room_type) for name, room in classrooms.items())),
                   tuple(sorted(exclusions, key=lambda row: (row[0] or '', *row[1:]))))


def _ratio(numerator, denominator):
    return numerator / denominator if denominator > 0 else None


def _union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _available(snapshot, room, day):
    if snapshot.day_end <= snapshot.day_start:
        return []
    pieces = [(snapshot.day_start, snapshot.day_end)]
    for start, end in _union((start, end) for name, index, start, end in snapshot.exclusions
                            if index == day and name in (None, room)):
        pieces = [(a, b) for left, right in pieces for a, b in
                  ((left, min(right, start)), (max(left, end), right)) if a < b]
    return pieces


def analyze_quality(snapshot: QualitySnapshot) -> dict:
    """Return deterministic JSON-ready values with explicit denominators.

    Preference ratios use assigned, evaluable preferences only; pending, absent
    and unknown preferences remain separate. Start-time satisfaction means exact
    equality, not the scheduler's ±30-minute candidate search window.
    """
    groups = {g.group_id: g for g in snapshot.sessions}
    assignments = {gid: (room, day, start, end)
                   for gid, room, day, start, end in snapshot.assignments}
    days = dict(snapshot.days)
    rooms = None if snapshot.rooms is None else dict(snapshot.rooms)
    assigned_ids = groups.keys() & assignments.keys()
    unknown_ids = sorted(assignments.keys() - groups.keys())
    issues = []
    if unknown_ids:
        issues.append("unknown_assignment_sessions")
    if rooms is None:
        issues.append("unknown_room_inventory")
    if snapshot.day_end <= snapshot.day_start:
        issues.append("invalid_operating_window")

    families = {}
    for group in snapshot.sessions:
        families.setdefault(group.original_group_id, []).append(group)
    original_counts = dict(total=len(families), fully_assigned=0, partially_assigned=0,
                           unassigned=0, unknown=0)
    for members in families.values():
        expected = {g.total_parts for g in members}
        if len(expected) != 1 or next(iter(expected)) != len(members):
            original_counts["unknown"] += 1
            continue
        count = sum(g.group_id in assignments for g in members)
        key = "fully_assigned" if count == len(members) else "partially_assigned" if count else "unassigned"
        original_counts[key] += 1
    if original_counts["unknown"]:
        issues.append("incomplete_original_group_metadata")

    preferences = {}
    for kind, attribute in (("day", "preferred_day"), ("time", "preferred_start_min"),
                            ("room", "suggested_classroom")):
        counts = dict(requested=0, absent=0, pending=0, unknown=0, evaluated=0, satisfied=0)
        for group in snapshot.sessions:
            preference = getattr(group, attribute)
            if preference is None or preference == "":
                counts["absent"] += 1
                continue
            counts["requested"] += 1
            slot = assignments.get(group.group_id)
            if slot is None:
                counts["pending"] += 1
                continue
            room, day, start, _ = slot
            if kind == "day":
                known = preference in days.values() and day in days
                matched = days.get(day) == preference
            elif kind == "time":
                known = (type(preference) is int and snapshot.day_start <= preference < snapshot.day_end
                         and snapshot.day_start <= start < snapshot.day_end)
                matched = start == preference
            else:
                known = rooms is not None and preference in rooms and room in rooms
                matched = room == preference
            if not known:
                counts["unknown"] += 1
                continue
            counts["evaluated"] += 1
            counts["satisfied"] += int(matched)
        counts["unsatisfied"] = counts["evaluated"] - counts["satisfied"]
        counts["ratio"] = _ratio(counts["satisfied"], counts["evaluated"])
        preferences[kind] = counts

    day_load = []
    for day, name in snapshot.days:
        slots = [slot for slot in assignments.values() if slot[1] == day and slot[2] < slot[3]]
        day_load.append(dict(day=day, name=name, assigned_sessions=len(slots),
                             teaching_minutes=sum(end - start for _, _, start, end in slots)))
    if any(day not in days or start >= end for _, day, start, end in assignments.values()):
        issues.append("unmeasurable_assignment_intervals")
    all_minutes = sum(row["teaching_minutes"] for row in day_load)
    for row in day_load:
        row["teaching_minutes_ratio"] = _ratio(row["teaching_minutes"], all_minutes)

    room_usage = []
    unknown_rooms = sorted({slot[0] for slot in assignments.values()
                            if rooms is None or slot[0] not in rooms})
    for room in sorted(rooms or {}):
        daily = []
        for day, _ in snapshot.days:
            available = _available(snapshot, room, day)
            scheduled = _union((start, end) for name, index, start, end in assignments.values()
                               if name == room and index == day)
            occupied = _union((max(a, start), min(b, end)) for a, b in available
                              for start, end in scheduled if max(a, start) < min(b, end))
            available_min = sum(end - start for start, end in available)
            occupied_min = sum(end - start for start, end in occupied)
            daily.append(dict(day=day, occupied_minutes=occupied_min, available_minutes=available_min,
                              ratio=_ratio(occupied_min, available_min)))
        occupied_min = sum(row["occupied_minutes"] for row in daily)
        available_min = sum(row["available_minutes"] for row in daily)
        room_usage.append(dict(room=room, occupied_minutes=occupied_min, available_minutes=available_min,
                               ratio=_ratio(occupied_min, available_min), days=daily))
    occupied_min = sum(row["occupied_minutes"] for row in room_usage)
    available_min = sum(row["available_minutes"] for row in room_usage)
    if unknown_rooms and rooms is not None:
        issues.append("unknown_assignment_rooms")

    recorded, active, unconfirmed, inactive, unknown_exceptions = [], [], [], [], []
    for group in snapshot.sessions:
        if group.lab_override:
            recorded.append(group.group_id)
        slot = assignments.get(group.group_id)
        if slot is None:
            if group.lab_override:
                inactive.append(group.group_id)
            continue
        if rooms is None or slot[0] not in rooms:
            if group.required_room_type == "LAB" or group.lab_override:
                unknown_exceptions.append(group.group_id)
            continue
        needs_exception = group.required_room_type == "LAB" and rooms[slot[0]] != "LAB"
        if needs_exception:
            (active if group.lab_override else unconfirmed).append(group.group_id)
        elif group.lab_override:
            inactive.append(group.group_id)

    return dict(
        schema_version=1, scope="global", unit="session", validity="not_evaluated",
        coverage=dict(sessions=len(groups), assigned_sessions=len(assigned_ids),
                      pending_sessions=len(groups) - len(assigned_ids),
                      assigned_ratio=_ratio(len(assigned_ids), len(groups)),
                      original_groups=original_counts, unknown_assignment_ids=unknown_ids),
        preferences=preferences, day_load=day_load,
        occupancy=dict(occupied_minutes=occupied_min, available_minutes=available_min,
                       ratio=_ratio(occupied_min, available_min), rooms=room_usage,
                       unknown_assignment_rooms=unknown_rooms, inventory_known=rooms is not None),
        manual_exceptions=dict(kind="lab_in_non_lab_room", recorded_ids=recorded,
                               active_ids=active, inactive_ids=inactive, unconfirmed_ids=unconfirmed,
                               unknown_ids=unknown_exceptions, assigned_sessions=len(assigned_ids),
                               active_ratio=_ratio(len(active), len(assigned_ids))),
        data_issues=issues,
    )
