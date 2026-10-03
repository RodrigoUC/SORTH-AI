"""Pure bounded suggestions; never moves existing sessions or relaxes a rule."""
from copy import deepcopy
from dataclasses import dataclass, asdict, is_dataclass
import hashlib
import json

from ..scheduling.cancellation import checkpoint
from ..scheduling.scheduler import Scheduler
from ..scheduling.schedule_state import ScheduleState
from ..scheduling.validation import validate_schedule, unassigned_reason


@dataclass(frozen=True)
class PlacementOptions:
    group_id: str
    revision: str
    placements: tuple
    examined: int
    truncated: bool
    notices: tuple = ()


def revision(assignments, groups, classrooms, time_model, lab_overrides=(), pinned=(), resources=None):
    """Fingerprint all validity inputs, including disabled-but-retained resources."""
    data = dict(assignments=assignments,
        groups=[{k: v for k, v in vars(g).items() if k != 'domain'} for g in groups],
        rooms={name: {k: v for k, v in vars(room).items() if k != 'occupancy'}
               for name, room in classrooms.items()},
        time=vars(time_model), lab_overrides=sorted(lab_overrides), pinned=sorted(pinned),
        resources=asdict(resources) if is_dataclass(resources) else resources)
    def encode(value):
        if isinstance(value, (set, frozenset)):
            return sorted(value)
        raise TypeError(f'Unsupported scheduling input: {type(value).__name__}')
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=encode,
                                    ensure_ascii=False).encode()).hexdigest()


def enumerate_placements(group_id, assignments, groups, classrooms, time_model,
                         lab_overrides=(), pinned=(), resources=None, *,
                         max_options=100, max_candidates=2000, cancelled=None):
    if type(max_options) is not int or type(max_candidates) is not int or not 1 <= max_options <= 500 or not 1 <= max_candidates <= 10000:
        raise ValueError('Invalid suggestion limits')
    checkpoint(cancelled)
    stamp = revision(assignments, groups, classrooms, time_model, lab_overrides, pinned, resources)
    known = {g.group_id: g for g in groups}
    if group_id not in known or group_id in assignments or group_id in pinned:
        raise ValueError('Only an unpinned pending session may be suggested')
    errors = validate_schedule(assignments, groups, classrooms, time_model, lab_overrides, resources)
    if errors:
        return PlacementOptions(group_id, stamp, (), 0, False, tuple(errors))
    copied_groups, rooms = deepcopy(groups), deepcopy(classrooms)
    group = next(g for g in copied_groups if g.group_id == group_id)
    for room in rooms.values():
        room.occupancy.clear()
    for room, day, start, end in assignments.values():
        rooms[room].occupy(day, start, end)
    state = ScheduleState(time_model, list(rooms.values()), resources=resources)
    state.assignments = dict(assignments)
    scheduler = Scheduler(cancelled=cancelled)
    exact_starts = {group.preferred_start_min} if group.preferred_start_min is not None else set()
    if group.parent_group_id:
        exact_starts.update(assignments[g.group_id][2] for g in copied_groups
                            if g.parent_group_id == group.parent_group_id and g.group_id in assignments)
    domain_limited = scheduler._build_domains(state, [group], strict_preferences=False,
        domain_limit=max_candidates + 1, additional_starts=exact_starts)
    placements, notices = [], []
    examined = 0
    truncated = domain_limited
    for room, day, start in group.domain:
        checkpoint(cancelled)
        if examined >= max_candidates or len(placements) >= max_options:
            truncated = True
            break
        examined += 1
        placement = (room.name, day, start, start + group.duration_min)
        candidate = dict(assignments, **{group_id: placement})
        errors = validate_schedule(candidate, copied_groups, rooms, time_model,
                                   set(lab_overrides) - {group_id}, resources)
        if not errors:
            placements.append(placement)
        elif len(notices) < 4:
            notices.extend(errors[:4 - len(notices)])
    if not placements and not notices:
        notices.append(unassigned_reason(group, rooms, time_model))
    checkpoint(cancelled)
    return PlacementOptions(group_id, stamp, tuple(placements), examined, truncated, tuple(notices))


def validate_choice(options, placement, assignments, groups, classrooms, time_model,
                    lab_overrides=(), pinned=(), resources=None):
    """Reject stale reviews; callers must recompute instead of silently applying."""
    if options.revision != revision(assignments, groups, classrooms, time_model,
                                    lab_overrides, pinned, resources):
        return ('stale',)
    if placement not in options.placements or options.group_id in assignments or options.group_id in pinned:
        return ('invalid_choice',)
    return tuple(validate_schedule(dict(assignments, **{options.group_id: placement}),
        groups, classrooms, time_model, set(lab_overrides) - {options.group_id}, resources))
