from random import Random
from typing import List
from .schedule_state import ScheduleState
from .group import Group
from .validation import unassigned_reason
from .cancellation import checkpoint


class Scheduler:

    def __init__(self, seed: int | None = 42, cancelled=None):
        self._cancelled = cancelled
        self._rng = Random(seed)
        self._all_groups: List[Group] = []

        # Incremental counters — updated on assign/unassign instead of
        # recomputing from scratch on every scoring call.
        self._day_load:       dict[int, int] = {}   # day_index -> # assignments
        self._time_load:      dict[int, int] = {}   # start_min -> # assignments
        self._classroom_uses: dict[str, int] = {}   # classroom_name -> # assignments
        # course_code -> list of (day, start_min, end_min, classroom_name)
        self._course_slots:   dict[str, list] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def schedule(self, state: ScheduleState, groups: List[Group]) -> bool:
        if state.resources is not None:
            errors = state.resources.structure_issues({g.group_id for g in groups}, state.time_model)
            if errors:
                raise ValueError('; '.join(map(str, errors)))
        checkpoint(self._cancelled)
        self._all_groups = groups
        self._reset_counters()
        self._seed_counters(state, groups)
        self._build_domains(state, groups, strict_preferences=True)

        ordered = sorted(groups, key=lambda g: len(g.domain))
        self._greedy_pass(state, ordered)

        MAX_RETRIES = 3
        for _ in range(MAX_RETRIES):
            checkpoint(self._cancelled)
            unassigned = [g for g in groups if not g.is_assigned()]
            if not unassigned:
                break
            # Relax preferences on retries so groups with no room on preferred
            # day/time can still be placed elsewhere
            self._build_domains(state, unassigned, strict_preferences=False)
            unassigned.sort(key=lambda g: len(g.domain))
            assigned_before = len(state.assignments)
            self._greedy_pass(state, unassigned)
            if len(state.assignments) == assigned_before:
                # A deterministic greedy pass cannot improve by repeating the
                # same relaxed domains against an unchanged schedule.
                break

        for group in groups:
            checkpoint(self._cancelled)
            group.unassigned_reason = "" if group.is_assigned() else unassigned_reason(
                group, state.classrooms, state.time_model)
        checkpoint(self._cancelled)
        return all(g.is_assigned() for g in groups)

    # ------------------------------------------------------------------
    # Greedy pass
    # ------------------------------------------------------------------

    def _greedy_pass(self, state: ScheduleState, groups: List[Group]):
        for group in groups:
            checkpoint(self._cancelled)
            if group.is_assigned():
                continue
            # Domains were built before earlier groups occupied their rooms.
            # Discard stale slots before scoring, then find the best candidate
            # in linear time instead of sorting every candidate. min() retains
            # the same first-in-domain tie breaking as the previous stable sort.
            candidates = (
                candidate for candidate in group.domain
                if self._candidate_available(candidate, group)
                and candidate[0].is_available(
                    candidate[1], candidate[2], candidate[2] + group.duration_min)
                and state.resources_allow(group, candidate[1], candidate[2])
                and (not group.parent_group_id or self._is_valid_subgroup(
                    group, candidate[1], candidate[2]))
            )
            best = min(candidates, key=lambda a: self._candidate_score(state, group, a),
                       default=None)
            if best is not None:
                classroom, day, start_min = best
                if state.assign(group, classroom.name, day, start_min):
                    self._track_assign(group, classroom.name, day, start_min)

    def _candidate_available(self, candidate, group):
        checkpoint(self._cancelled)
        return True

    # ------------------------------------------------------------------
    # Domain initialization
    # ------------------------------------------------------------------

    def _build_domains(self, state: ScheduleState, groups: List[Group],
                        strict_preferences: bool = True, domain_limit=None, additional_starts=()):
        # Build reverse map: course_code -> set of classrooms it is restricted to.
        # The reverse restriction applies only when this group's suggested
        # classroom belongs to the reserved set, never to unrelated groups.
        restricted_to: dict[str, set[str]] = {}
        for cls in state.classrooms.values():
            checkpoint(self._cancelled)
            if cls.allowed_courses is not None:
                for code in cls.allowed_courses:
                    checkpoint(self._cancelled)
                    restricted_to.setdefault(code, set()).add(cls.name)

        start_candidates: dict[tuple[int, int | None], list[int]] = {}
        for group in groups:
            checkpoint(self._cancelled)
            domain = []
            # Bidirectional restriction only applies if this specific group's
            # suggested_classroom is one of the restricted classrooms for this course.
            course_allowed_classrooms = restricted_to.get(group.course_code)
            if course_allowed_classrooms:
                if group.suggested_classroom not in course_allowed_classrooms:
                    # This group's suggestion is NOT a restricted classroom,
                    # so don't force it into the restricted set
                    course_allowed_classrooms = None
            pref_start = group.preferred_start_min if strict_preferences else None
            start_key = (group.duration_min, pref_start)
            if start_key not in start_candidates:
                start_candidates[start_key] = state.time_model.generate_start_candidates(
                    group.duration_min, pref_start)
                if additional_starts:
                    start_candidates[start_key] = sorted(set(start_candidates[start_key]) | {
                        start for start in additional_starts if type(start) is int
                        and state.time_model.is_valid_interval(1, start, start + group.duration_min)
                        and not state.time_model.overlaps_lunch(start, start + group.duration_min)})
            days = [day for day in range(1, state.time_model.days_count + 1)
                    if not (strict_preferences and group.preferred_day)
                    or state.time_model.to_day_name(day) == group.preferred_day]
            for classroom in state.classrooms.values():
                checkpoint(self._cancelled)
                if group.required_room_type == "LAB" and classroom.room_type != "LAB":
                    continue
                if classroom.capacity < group.size:
                    continue
                # Bidirectional restriction
                if not classroom.allows_course(group.course_code):
                    continue
                if course_allowed_classrooms and classroom.name not in course_allowed_classrooms:
                    continue
                # Strict pass: if group has a suggested classroom, only use that one
                if strict_preferences and group.suggested_classroom:
                    if classroom.name != group.suggested_classroom:
                        continue
                for day in days:
                    checkpoint(self._cancelled)
                    for start_min in start_candidates[start_key]:
                        checkpoint(self._cancelled)
                        if (classroom.is_available(day, start_min, start_min + group.duration_min)
                                and state.resources_allow(group, day, start_min)):
                            if domain_limit is not None and len(domain) >= domain_limit:
                                group.domain = domain
                                return True
                            domain.append((classroom, day, start_min))
            group.domain = domain
        return False

    # ------------------------------------------------------------------
    # Incremental counter management
    # ------------------------------------------------------------------

    def _reset_counters(self):
        self._day_load.clear()
        self._time_load.clear()
        self._classroom_uses.clear()
        self._course_slots.clear()

    def _seed_counters(self, state: ScheduleState, groups: List[Group]):
        """Include existing reservations when continuing an existing schedule."""
        known_groups = {group.group_id: group for group in groups}
        for group_id, (classroom, day, start, end) in state.assignments.items():
            checkpoint(self._cancelled)
            self._day_load[day] = self._day_load.get(day, 0) + 1
            self._time_load[start] = self._time_load.get(start, 0) + 1
            self._classroom_uses[classroom] = self._classroom_uses.get(classroom, 0) + 1
            group = known_groups.get(group_id)
            if group and group.course_code and group.parent_group_id is None:
                self._course_slots.setdefault(group.course_code, []).append(
                    (day, start, end, classroom))

    def _track_assign(self, group: Group, classroom_name: str, day: int, start_min: int):
        self._day_load[day] = self._day_load.get(day, 0) + 1
        self._time_load[start_min] = self._time_load.get(start_min, 0) + 1
        self._classroom_uses[classroom_name] = self._classroom_uses.get(classroom_name, 0) + 1
        if group.course_code and group.parent_group_id is None:
            end_min = start_min + group.duration_min
            self._course_slots.setdefault(group.course_code, []).append(
                (day, start_min, end_min, classroom_name)
            )

    # ------------------------------------------------------------------
    # Candidate sorting — all O(1) lookups via counters
    # ------------------------------------------------------------------

    def _sort_candidates(self, state: ScheduleState, group: Group, candidates: list) -> list:
        return sorted(candidates, key=lambda a: self._candidate_score(state, group, a))

    def _candidate_score(self, state: ScheduleState, group: Group, a: tuple) -> tuple:
        checkpoint(self._cancelled)
        return (
            self._type_score(state, group, a[0].name),
            self._suggested_classroom_score(group, a[0].name),
            self._same_course_score(group, a[1], a[2]),
            self._preference_score(state, group, a[1], a[2]),
            self._day_score(state, a[1]),
            self._time_score(a[2]),
            self._classroom_uses.get(a[0].name, 0),
        )

    def _suggested_classroom_score(self, group: Group, classroom_name: str) -> int:
        """0 = matches suggested classroom, 1 = does not."""
        if group.suggested_classroom and group.suggested_classroom == classroom_name:
            return 0
        return 1

    def _type_score(self, state: ScheduleState, group: Group, classroom_name: str) -> int:
        cls = state.classrooms.get(classroom_name)
        return 0 if (cls and cls.room_type == group.required_room_type) else 1

    def _same_course_score(self, group: Group, day: int, start_min: int) -> tuple:
        if group.parent_group_id is not None:
            return (3, 0)
        slots = self._course_slots.get(group.course_code, [])
        if not slots:
            return (3, 0)

        best_level, best_secondary = 3, 0
        for sib_day, sib_start, sib_end, _ in slots:
            checkpoint(self._cancelled)
            next_hour = ((sib_end + 59) // 60) * 60
            if day == sib_day and start_min == next_hour and start_min > sib_end:
                gap = start_min - sib_end
                if best_level > 0 or gap < best_secondary:
                    best_level, best_secondary = 0, gap
            elif day == sib_day and start_min == sib_start:
                if best_level > 1:
                    best_level, best_secondary = 1, 0
            elif day != sib_day and start_min == sib_start:
                if best_level > 2:
                    best_level, best_secondary = 2, 0
        return (best_level, best_secondary)

    def _preference_score(self, state: ScheduleState, group: Group,
                          day: int, start_min: int) -> int:
        if not group.preferred_day and group.preferred_start_min is None:
            return 3
        day_match = (state.time_model.to_day_name(day) == group.preferred_day
                     if group.preferred_day else True)
        hour_match = (start_min == group.preferred_start_min
                      if group.preferred_start_min is not None else True)
        if day_match and hour_match:
            return 0
        if day_match:
            return 1
        if hour_match:
            return 2
        return 3

    def _day_score(self, state: ScheduleState, day: int) -> int:
        load = self._day_load.get(day, 0)
        day_name = state.time_model.to_day_name(day)
        weekdays = {"Lunes", "Martes", "Miércoles", "Jueves", "Viernes"}
        if day_name in weekdays:
            return load if load <= 2 else 500 + load
        return 50 + load

    def _time_score(self, start_min: int) -> int:
        load = self._time_load.get(start_min, 0)
        if start_min <= 16 * 60:
            return load
        return 100 + (start_min - 16 * 60) // 60

    # ------------------------------------------------------------------
    # Subgroup constraint
    # ------------------------------------------------------------------

    def _is_valid_subgroup(self, subgroup: Group, day: int, start_min: int) -> bool:
        parent_id = subgroup.parent_group_id
        for other in self._all_groups:
            checkpoint(self._cancelled)
            if other.parent_group_id != parent_id or other is subgroup:
                continue
            if not other.is_assigned():
                continue
            _, other_day, other_start, _ = other.assignment
            if other_day == day or other_start != start_min:
                return False
        return True
